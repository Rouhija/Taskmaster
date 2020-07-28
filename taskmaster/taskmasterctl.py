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
from subprocess import Popen, PIPE
from taskmaster.editor import Editor
from taskmaster.config import Config
from os.path import dirname, realpath
from taskmaster.utils import parse, syntax, arg_parserctl, clear_screen

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

    def __init__(self, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_address = ('localhost', port)
        self.buf = 8192


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
            command = e.user_input()
            command = parse(command)
            if command is None or command == 'quit' or command == 'exit':
                break
            elif command == '':
                pass
            elif syntax(command) == True:
                response = self.send_to_daemon(command)
                if response is None:
                    print(f'No response. Make sure taskmasterd is running.')
                    LOG.warn(f'No response from {self.server_address}')
                elif 'attach' in command and response is not None:
                    self.attach(response)
                else:
                    self.echo_resp(response)
        self.cleanup()


    def echo_resp(self, response):
        resp = response.split('|')
        for r in resp:
            if r:
                print(r)


    def attach(self, response):
        try:
            resp = response.split('|')
            pid = int(resp[0])
            fd = int(resp[1])
        except:
            print('error in attaching process to console')


    def send_to_daemon(self, command):

        response = ''

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
            r = self.sock.recv(self.buf)
            if r:
                response += r.decode()
            LOG.info('Received from taskmasterd "%s"' % response)

        finally:
            if len(response):
                return response
            else:
                return None

    def cleanup(self):
        try:
            LOG.debug('closing socket')
            self.sock.close()
        finally:
            sys.exit('')


def logger_options(debug: int):
    if debug:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(levelname)s:%(asctime)s ⁠— %(message)s',
            datefmt='%d/%m/%Y %H:%M:%S'
        )
    else:
        work_dir = dirname(realpath(__file__))
        logging.basicConfig(
            filename=f'{work_dir}/resources/logs/taskmasterctl.log',
            level=logging.DEBUG,
            format='%(levelname)s:%(asctime)s ⁠— %(message)s',
            datefmt='%d/%m/%Y %H:%M:%S'
        )


def main():
    print(SNEK)
    args = arg_parserctl()
    logger_options(args.debug)
    conf = Config(ctl=True)
    c = Console(conf.port)
    c.run_forever()


if __name__ == "__main__":
    main()
