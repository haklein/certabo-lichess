#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 by Harald Klein <hari@vt100.at> - All rights reserved
# 

import sys
import time
import logging
import logging.handlers
import traceback
import os
import argparse
import threading
import importlib

import chess.pgn
import chess

import berserk
import certabo
from certabo.certabo import CERTABO_DATA_PATH as CERTABO_DATA_PATH

parser = argparse.ArgumentParser()
parser.add_argument("--port")
parser.add_argument("--calibrate", action="store_true")
parser.add_argument("--devmode", action="store_true")
parser.add_argument("--quiet", action="store_true")
parser.add_argument("--debug", action="store_true")
args = parser.parse_args()

portname = 'auto'
if args.port is not None:
    portname = args.port

calibrate = False
if args.calibrate:
    calibrate = True

DEBUG=False
if args.debug:
    DEBUG = True

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(module)s %(message)s')

filehandler = logging.handlers.TimedRotatingFileHandler(
    os.path.join(CERTABO_DATA_PATH, "certabo-lichess.log"), backupCount=12
)
filehandler.setFormatter(formatter)
logger.addHandler(filehandler)

if not args.quiet:
    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(formatter)
    logger.addHandler(consoleHandler)

# log unhandled exceptions to the log file
def my_excepthook(excType, excValue, traceback, logger=logger):
    logger.error("Uncaught exception",
                 exc_info=(excType, excValue, traceback))
sys.excepthook = my_excepthook

logging.info("certabo-lichess.py startup")

class Game(threading.Thread):
    def __init__(self, client, mycertabo, game_id, **kwargs):
        super().__init__(**kwargs)
        self.game_id = game_id
        self.certabo = mycertabo
        self.client = client
        self.stream = client.board.stream_game_state(game_id)
        self.current_state = next(self.stream)

    def run(self):
        for event in self.stream:
            if event['type'] == 'gameState':
                self.handle_state_change(event)
            elif event['type'] == 'chatLine':
                self.handle_chat_line(event)

    def handle_state_change(self, game_state):
        # {'type': 'gameState', 'moves': 'd2d3 e7e6 b1c3', 'wtime': datetime.datetime(1970, 1, 25, 20, 31, 23, 647000, tzinfo=datetime.timezone.utc), 'btime': datetime.datetime(1970, 1, 25, 20, 31, 23, 647000, tzinfo=datetime.timezone.utc), 'winc': datetime.datetime(1970, 1, 1, 0, 0, tzinfo=datetime.timezone.utc), 'binc': datetime.datetime(1970, 1, 1, 0, 0, tzinfo=datetime.timezone.utc), 'bdraw': False, 'wdraw': False}

        print(game_state)
        tmp_chessboard = chess.Board()
        moves = game_state['moves'].split(' ')
        for move in moves:
            tmp_chessboard.push_uci(move)
            # print(move)
            self.certabo.set_board_from_fen(tmp_chessboard.fen())
        if tmp_chessboard.turn == self.certabo.get_color():
            logging.info('it is our turn')
            moves = self.certabo.get_user_move()
            logging.info(f'our move: {moves}') 
            try:
                self.client.board.make_move(self.certabo.get_reference(), moves[0])
            except:
                e = sys.exc_info()[0]
                logging.info(f'exception on make_move: {e}')

    def handle_chat_line(self, chat_line):
        print(chat_line)
        pass


def main():
    simplejson_spec = importlib.util.find_spec("simplejson")
    if simplejson_spec is not None:
        print(f'ERROR: simplejson is installed. The berserk lichess client will not work with simplejson. Please remove the module. Aborting.')
        sys.exit(-1)

    mycertabo = certabo.certabo.Certabo(port=portname, calibrate=calibrate)

    try:
        with open('./lichess.token') as f:
            token = f.read().strip()
    except FileNotFoundError:
        print(f'ERROR: cannot find token file')
        sys.exit(-1)
    except PermissionError:
        print(f'ERROR: permission denied on token file')
        sys.exit(-1)

    try:
        session = berserk.TokenSession(token)
    except:
        e = sys.exc_info()[0]
        print(f"cannot create session: {e}")
        logging.info(f'cannot create session {e}')
        sys.exit(-1)

    try:
        if args.devmode:
            client = berserk.Client(session, base_url="https://lichess.dev")
        else:
            client = berserk.Client(session)
    except:
        e = sys.exc_info()[0]
        logging.info(f'cannot create lichess client: {e}')
        print(f"cannot create lichess client: {e}")
        sys.exit(-1)

    def setup_new_gameid(gameId):
        for game in client.games.get_ongoing():
            if game['gameId'] == gameId:
                mycertabo.new_game()
                mycertabo.set_reference(game['gameId'])
                logging.info(f'setup_new_gameid() found gameId: {mycertabo.get_reference()}')
                tmp_chessboard = chess.Board()
                # unfortunately this is not a complete FEN. So we can only determine position and who's turn it is for an already ongoing game, but have no idea about castling 
                # rights and en passant. But that's the best we can do for now, and on the next state update we'll get all moves and can replay them to get a complete board state
                tmp_chessboard.set_board_fen(game['fen']) 
                if game['isMyTurn'] and game['color']=='black':
                    tmp_chessboard.turn = chess.BLACK
                else:
                    tmp_chessboard.turn = chess.WHITE
                mycertabo.set_board_from_fen(tmp_chessboard.fen())
                logging.info(f'final FEN: {tmp_chessboard.fen()}')
                if game['color'] == 'black':
                    mycertabo.set_color(chess.BLACK)
                else:
                    mycertabo.set_color(chess.WHITE)
                if game['isMyTurn']:
                    mycertabo.set_state('myturn')

    while True:
        try:
            logging.debug(f'board event loop')
            for event in client.board.stream_incoming_events():
                if event['type'] == 'challenge':
                    print("Challenge received")
                    print(event)
                elif event['type'] == 'gameStart':
                    # {'type': 'gameStart', 'game': {'id': 'pCHwBReX'}}
                    game_data = event['game']
                    logging.info(f"game start received: {game_data['id']}")

                    try:
                        game = Game(client, mycertabo, game_data['id'])
                        game.daemon = True
                        game.start()
                    except berserk.exceptions.ResponseError as e:
                        if 'This game cannot be played with the Board API' in str(e):
                            print('cannot play this game via board api')
                        logging.info(f'ERROR: {e}')
                        continue

                    setup_new_gameid(game_data['id'])
                    if mycertabo.get_state() == 'myturn':
                        logging.info(f'starting new game, checking for user move')
                        mycertabo.set_state('init')
                        moves = mycertabo.get_user_move()
                        client.board.make_move(mycertabo.get_reference(), moves[0])

        except berserk.exceptions.ResponseError as e:
            print(f'ERROR: Invalid server response: {e}')
            logging.info('Invalid server response: {e}')
            if 'Too Many Requests for url' in str(e):
                time.sleep(10)

if __name__ == '__main__':
    main()

