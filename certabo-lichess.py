#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 by Harald Klein <hari@vt100.at> - All rights reserved
# 

from __future__ import print_function
from __future__ import division
import importlib
import re
import sys
import time
import logging
import logging.handlers
import traceback
import os
import argparse
import subprocess
import time as tt
import threading
import queue
import serial
import fcntl

import serial.tools.list_ports

import berserk

from socket import *
from select import *

import chess.pgn
import chess

from random import shuffle

import codes

from utils import port2number, port2udp, find_port, get_engine_list, get_book_list, coords_in
from constants import CERTABO_SAVE_PATH, CERTABO_DATA_PATH, MAX_DEPTH_DEFAULT

DEBUG = True

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(module)s %(message)s')

filehandler = logging.handlers.TimedRotatingFileHandler(
    os.path.join(CERTABO_DATA_PATH, "certabo-lichess.log"), backupCount=12
)
filehandler.setFormatter(formatter)
logger.addHandler(filehandler)

# log unhandled exceptions to the log file
def my_excepthook(excType, excValue, traceback, logger=logger):
    logger.error("Uncaught exception",
                 exc_info=(excType, excValue, traceback))
sys.excepthook = my_excepthook

logging.info("certabi-lichess.py startup")

for d in (CERTABO_SAVE_PATH, CERTABO_DATA_PATH):
    try:
        os.makedirs(d)
    except OSError:
        pass

parser = argparse.ArgumentParser()
parser.add_argument("--port")
# ignore additional parameters
# parser.add_argument('bar', nargs='?')
args = parser.parse_args()

portname = 'auto'
if args.port is not None:
    portname = args.port
port = port2number(portname)


class serialreader(threading.Thread):
    def __init__ (self, handler, device='auto'):
        threading.Thread.__init__(self)
        self.device = device
        self.connected = False
        self.handler = handler
        self.serial_out = queue.Queue()

    def send_led(self, message):
        self.serial_out.put(message)

    def run(self):
        while True:
            if not self.connected:
                try:
                    if self.device == 'auto':
                        logging.info(f'Auto-detecting serial port')
                        serialport = find_port()
                    else:
                        serialport = self.device
                    if serialport is None:
                        logging.info(f'No port found, retrying')
                        time.sleep(1)
                        continue
                    logging.info(f'Opening serial port {serialport}')
                    uart = serial.Serial(serialport, 38400, timeout=2.5)  # 0-COM1, 1-COM2 / speed /
                    if os.name == 'posix':
                        logging.debug(f'Attempting to lock {serialport}')
                        fcntl.flock(uart.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    logging.debug(f'Flushing input on {serialport}')
                    uart.flushInput()
                    uart.write(b'U\xaaU\xaaU\xaaU\xaa')
                    time.sleep(1)
                    uart.write(b'\xaaU\xaaU\xaaU\xaaU')
                    time.sleep(1)
                    uart.write(b'\x00\x00\x00\x00\x00\x00\x00\x00')
                    self.connected = True
                except Exception as e:
                    logging.info(f'ERROR: Cannot open serial port {serialport}: {str(e)}')
                    self.connected = False
                    time.sleep(0.1)
            else:
                try:
                    while uart.inWaiting():
                        # logging.debug(f'serial data pending')
                        message = uart.readline().decode("ascii")
                        message = message[1: -3]
                        #if DEBUG:
                        #    print(len(message.split(" ")), "numbers")
                        if len(message.split(" ")) == 320:  # 64*5
                            self.handler(message)
                        message = ""
                    time.sleep(0.001)
                    if not self.serial_out.empty():
                        data = self.serial_out.get()
                        self.serial_out.task_done()
                        # logging.debug(f'Sending to serial: {data}')
                        uart.write(data)
                except Exception as e:
                    logging.info(f'Exception during serial communication: {str(e)}')
                    self.connected = False


class Certabo():
    def __init__(self, port='auto', **kwargs):
        super().__init__(**kwargs)
        self.portname = port
        self.calibration = False
        self.new_setup = False
        self.rotate180 = False
        self.color = chess.WHITE
        self.starting_position = chess.STARTING_FEN
        self.chessboard = chess.Board(chess.STARTING_FEN)
        self.board_state_usb = ""
        self.mystate = "init"
        self.reference = ""

        # internal values for CERTABO board
        self.calibration_samples_counter = 0
        self.calibration_samples = []
        self.usb_data_history_depth = 3
        self.usb_data_history = list(range(self.usb_data_history_depth))
        self.usb_data_history_filled = False
        self.usb_data_history_i = 0
        self.move_detect_tries = 0
        self.move_detect_max_tries = 3

        # try to load calibration data (mapping of RFID chip IDs to pieces)
        codes.load_calibration(None)

        # spawn a serial thread and pass our data handler
        self.serialthread = serialreader(self.handle_usb_data, self.portname)
        self.serialthread.daemon = True
        self.serialthread.start()

    def has_user_move(self):
        try:
            moves = codes.get_moves(self.chessboard, self.board_state_usb)
            return moves
        except:
            return []

    def get_reference(self):
        return self.reference

    def set_reference(self, reference):
        self.reference = reference

    def get_color(self):
        return self.color

    def set_color(self, color):
        self.color = color

    def set_state(self, state):
        self.mystate = state

    def get_state(self):
        return self.mystate

    def new_game(self):
        self.chessboard = chess.Board()
        self.mystate = "init"

    def set_board_from_fen(self, fen):
        self.chessboard = chess.Board(fen)

    def send_leds(self, message=b'\x00\x00\x00\x00\x00\x00\x00\x00'):
        self.serialthread.send_led(message)

    def diff_leds(self):
        s1 = self.chessboard.board_fen()
        s2 = self.board_state_usb.split(" ")[0]
        if (s1 != s2):
            diffmap = codes.diff2squareset(s1, s2)
            # logging.debug(f'Difference on Squares:\n{diffmap}')
            self.send_leds(codes.squareset2ledbytes(diffmap))
        else:
            self.send_leds()

    def handle_usb_data(self, data):
        usb_data = list(map(int, data.split(" ")))
        if self.calibration == True:
            self.calibrate_from_usb_data(usb_data)
        else:
            if self.usb_data_history_i >= self.usb_data_history_depth:
                self.usb_data_history_filled = True
                self.usb_data_history_i = 0

            self.usb_data_history[self.usb_data_history_i] = list(usb_data)[:]
            self.usb_data_history_i += 1
            if self.usb_data_history_filled:
                self.usb_data_processed = codes.statistic_processing(self.usb_data_history, False)
                if self.usb_data_processed != []:
                    test_state = codes.usb_data_to_FEN(self.usb_data_processed, self.rotate180)
                    if test_state != "":
                        self.board_state_usb = test_state
                        # logging.info(f'info string FEN {test_state}')
                        self.diff_leds()

    def calibrate_from_usb_data(self, usb_data):
        self.calibration_samples.append(usb_data)
        logging.info("    adding new calibration sample")
        self.calibration_samples_counter += 1
        if self.calibration_samples_counter >= 15:
            logging.info( "------- we have collected enough samples for averaging ----")
            usb_data = codes.statistic_processing_for_calibration( self.calibration_samples, False)
            codes.calibration(usb_data, self.new_setup, None)
            self.calibration = False
            logging.info('calibration ok') 
            self.send_leds()
        elif self.calibration_samples_counter %2:
            self.send_leds(b'\xff\xff\x00\x00\x00\x00\xff\xff')
        else:
            self.send_leds()

class Game(threading.Thread):
    def __init__(self, client, certabo, game_id, **kwargs):
        super().__init__(**kwargs)
        self.game_id = game_id
        self.certabo = certabo
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
            while self.certabo.has_user_move() == []:
                time.sleep(0.1)
            ucimove = self.certabo.has_user_move()[0]
            logging.info(f'our move: {ucimove}') 
            self.client.board.make_move(self.certabo.get_reference(), ucimove)

    def handle_chat_line(self, chat_line):
        print(chat_line)
        pass


def main():
    certabo = Certabo(portname)

    with open('./lichess.token') as f:
        token = f.read().strip()

    session = berserk.TokenSession(token)
    client = berserk.Client(session)

    def setup_new_gameid(gameId):
        for game in client.games.get_ongoing():
            if game['gameId'] == gameId:
                certabo.new_game()
                certabo.set_reference(game['gameId'])
                logging.info(f'setup_new_gameid() found gameId: {certabo.get_reference()}')
                tmp_chessboard = chess.Board()
                # unfortunately this is not a complete FEN. So we can only determine position and who's turn it is for an already ongoing game, but have no idea about castling 
                # rights and en passant. But that's the best we can do for now, and on the next state update we'll get all moves and can replay them to get a complete board state
                tmp_chessboard.set_board_fen(game['fen']) 
                if game['isMyTurn'] and game['color']=='black':
                    tmp_chessboard.turn = chess.BLACK
                else:
                    tmp_chessboard.turn = chess.WHITE
                certabo.set_board_from_fen(tmp_chessboard.fen())
                logging.info(f'final FEN: {tmp_chessboard.fen()}')
                if game['color'] == 'black':
                    certabo.set_color(chess.BLACK)
                else:
                    certabo.set_color(chess.WHITE)
                if game['isMyTurn']:
                    certabo.set_state('myturn')

    for event in client.board.stream_incoming_events():
        if event['type'] == 'challenge':
            print("Challenge received")
            print(event)
        elif event['type'] == 'gameStart':
            print("game start received")

            # {'type': 'gameStart', 'game': {'id': 'pCHwBReX'}}
            # print(event)
            game_data = event['game']
            # print(game_data)
             
            game = Game(client, certabo, game_data['id'])
            game.daemon = True
            game.start()

            setup_new_gameid(game_data['id'])
            if certabo.get_state() == 'myturn':
                certabo.set_state('init')
                while certabo.has_user_move() == []:
                    time.sleep(0.1)
                client.board.make_move(certabo.get_reference(), certabo.has_user_move()[0])


                

if __name__ == '__main__':
    main()

