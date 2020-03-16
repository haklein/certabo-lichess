#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 by Harald Klein <hari@vt100.at> - All rights reserved
# 

import time
import os
import sys
import argparse
import subprocess
import threading
import queue
import serial
import fcntl
import logging

import serial.tools.list_ports

if os.name == 'nt':  # sys.platform == 'win32':
    from serial.tools.list_ports_windows import comports
elif os.name == 'posix':
    from serial.tools.list_ports_posix import comports

def find_port():
    logging.debug('Searching for port...')
    for port in comports():
        device = port[0]
        if 'bluetooth' in device.lower():
            continue
        if port.pid != 0xea60 and port.vid != 0x10c4:
            logging.debug(f'skipping: {port.hwid}')
            continue
        try:
            logging.debug('Trying %s', device)
            s = serial.Serial(device)
        except serial.SerialException:
            logging.debug('Port is busy, continuing...')
            continue
        else:
            s.close()
            logging.debug('Port is found! - %s', device)
            if (sys.version_info.major == 2):
                if isinstance(device, unicode):
                    device = device.encode('utf-8')
            return device
    else:
        logging.debug('Port not found')
        return

class serialreader(threading.Thread):
    def __init__ (self, handler, device='auto'):
        threading.Thread.__init__(self)
        self.device = device
        self.connected = False
        self.handler = handler
        self.uart = None

    def send_led(self, message: bytes):
        # logging.debug(f'Sending to serial: {message}')
        if self.connected:
            return self.uart.write(message)
        return None

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
                    self.uart = serial.Serial(serialport, 38400)  # 0-COM1, 1-COM2 / speed /
                    # self.uart = serial.Serial(serialport, 38400, timeout=2.5)  # 0-COM1, 1-COM2 / speed /
                    if os.name == 'posix':
                        logging.debug(f'Attempting to lock {serialport}')
                        fcntl.flock(self.uart.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    logging.debug(f'Flushing input on {serialport}')
                    self.uart.flushInput()
                    self.uart.write(b'U\xaaU\xaaU\xaaU\xaa')
                    time.sleep(1)
                    self.uart.write(b'\xaaU\xaaU\xaaU\xaaU')
                    time.sleep(1)
                    self.uart.write(b'\x00\x00\x00\x00\x00\x00\x00\x00')
                    self.connected = True
                except Exception as e:
                    logging.info(f'ERROR: Cannot open serial port {serialport}: {str(e)}')
                    self.connected = False
                    time.sleep(0.1)
            else:
                try:
                    while True:
                        # logging.debug(f'serial data pending')
                        raw_message = self.uart.readline()
                        try:
                            message = raw_message.decode("ascii")[1: -3]
                            #if DEBUG:
                            #    print(len(message.split(" ")), "numbers")
                            if len(message.split(" ")) == 320:  # 64*5
                                self.handler(message)
                            message = ""
                        except Exception as e:
                            logging.info(f'Exception during message decode: {str(e)}')
                except Exception as e:
                    logging.info(f'Exception during serial communication: {str(e)}')
                    self.connected = False

