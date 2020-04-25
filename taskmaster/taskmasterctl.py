#!/usr/bin/python3

"""taskmasterctl -- control applications run by taskmasterd from the cmd line.
Usage: %s [options] [action [arguments]]
Options:
  -h, --help   show this help message and exit
  -d, --debug  log to console
"""

import sys
import socket
import signal
import logging
import argparse
from taskmaster.editor import Editor
from taskmaster.config import Config
from os.path import dirname, realpath
from taskmaster.utils import parse, syntax

LOG = logging.getLogger(__name__)

SNEK = """\
    --..,_                     _,.--.
       `'.'.                .'`__ o  `;__.
          '.'.            .'.'`  '---'`  `
            '.`'--....--'`.'
              `'--....--'`
    \x1B[3mTaskmaster\x1B[23m
"""


class Console:

    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_address = ('localhost', 10000)
        self.buf = 256


    def set_signals(self):
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)


    def signal_handler(self, signum, frame):
        if signum == signal.SIGINT or signum == signal.SIGTERM:
            self.cleanup()


    def run_forever(self):
        self.set_signals()
        e = Editor()
        while 1:
            command = e.read_in()
            command = parse(command)
            if command == None or command == 'quit' or command == 'exit':
                break
            elif command == '':
                pass
            elif syntax(command) == True:
                response = self.send_to_daemon(command)
                if response is None or response == 'error':
                    print(f'No response. Make sure taskmasterd is running.')
                    LOG.warn(f'No response from {self.server_address}')
                else:
                    self.echo_resp(response)
        self.cleanup()


    def echo_resp(self, response):
        resp = response.split('|')
        for r in resp:
            if r:
                print(r)


    def send_to_daemon(self, command):

        response = None

        # Connect to daemon
        try:
            LOG.info('connecting to %s port %s' % self.server_address)
            self.sock.connect(self.server_address)
        except OSError as e:
            LOG.debug(e)

        try:
            # Send to daemon
            b_command = command.encode()
            LOG.info('Sending to taskmasterd %s' % b_command)
            try:
                self.sock.sendall(b_command)
            except BrokenPipeError as e:
                LOG.error(f'Daemon is not responding: {e}')

            # Get response       
            response = self.sock.recv(self.buf).decode()
            LOG.info('Received from taskmasterd "%s"' % response)

        finally:
            return response

    def cleanup(self):
        try:
            LOG.debug('closing socket')
            self.sock.close()
        finally:
            sys.exit()


def logger_options(debug: int):
    if debug:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(levelname)s:%(asctime)s ⁠— %(message)s',
            datefmt='%d/%m/%Y %H:%M:%S'
        )
    else:
        parent_dir = dirname(dirname(realpath(__file__)))
        logging.basicConfig(
            filename=f'{parent_dir}/logs/taskmasterctl.log',
            level=logging.DEBUG,
            format='%(levelname)s:%(asctime)s ⁠— %(message)s',
            datefmt='%d/%m/%Y %H:%M:%S'
        )


def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--debug", help="log to console", action="store_true")
    return parser.parse_args()


def main():
    print(SNEK)
    args = arg_parser()
    logger_options(args.debug)
    c = Console()
    c.run_forever()


if __name__ == "__main__":
    main()
