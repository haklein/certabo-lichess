import sys
import logging
import os
import serial
import string
import platform
import stat
from constants import BASE_PORT, ENGINE_PATH, BOOK_PATH


if os.name == 'nt':  # sys.platform == 'win32':
    from serial.tools.list_ports_windows import comports
elif os.name == 'posix':
    from serial.tools.list_ports_posix import comports


def port2number(port):
    if isinstance(port, str):
        try:
            n = int(port)
        except ValueError:
            if isinstance(port, str):
                if port.upper().startswith('COM'):
                    return int(port[3:]) - 1  # Convert to zero based enumeration
                if port.lower().startswith('/dev/'):
                    digits = []
                    for c in reversed(port):
                        if c not in string.digits:
                            break
                        digits.append(c)
                    if not digits:
                        return None
                    return int(''.join(digits))

        else:
            return n


def port2udp(port_number):
    if port_number is None:
        return BASE_PORT, BASE_PORT + 1
    board_listen_port = BASE_PORT + (port_number + 1) * 2
    gui_listen_port = board_listen_port + 1
    return board_listen_port, gui_listen_port


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


if platform.system() == 'Windows':
    def get_engine_list():
        result_exe = []
        result_rom = []
        for filename in os.listdir(ENGINE_PATH):
            if filename == 'MessChess':
                roms = os.path.join(ENGINE_PATH, filename, 'roms')
                for rom in os.listdir(roms):
                    result_rom.append('rom-' + os.path.splitext(rom)[0])

            if filename.endswith('.exe'):
                result_exe.append(os.path.splitext(filename)[0])
        result_exe.sort()
        result_rom.sort()
        return result_exe + result_rom
else:
    def get_engine_list():
        result = []
        for filename in os.listdir(ENGINE_PATH):
            st = os.stat(os.path.join(ENGINE_PATH, filename))
            if st.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
                result.append(filename)
        result.sort()
        return result

def get_book_list():
    result = []
    for filename in os.listdir(BOOK_PATH):
        result.append(filename)
    result.sort()
    return result

def coords_in(x, y, area):
    if not area:
        return False
    lx, ty, rx, by = area
    return lx < x < rx and ty < y < by
