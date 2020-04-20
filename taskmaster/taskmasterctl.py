#!/usr/bin/python3

"""taskmasterctl -- control applications run by taskmasterd from the cmd line.
Usage: %s [options] [action [arguments]]
Options:
-
-
-
"""

import sys
import socket
import signal
import logging
from taskmaster.config import Config

logging.basicConfig(
    # filename='/var/log/taskmaster/taskmasterctl.log',
    level=logging.DEBUG,
    format='%(levelname)s:%(asctime)s ⁠— %(message)s',
    datefmt='%d/%m/%Y %H:%M:%S'
)

LOG = logging.getLogger(__name__)

snake = """\
    --..,_                     _,.--.
       `'.'.                .'`__ o  `;__.
          '.'.            .'.'`  '---'`  `
            '.`'--....--'`.'
              `'--....--'`
    \x1B[3mTaskmaster ©srouhe\x1B[23m
"""

DEFAULT_CMDS = [
    'add',
    'avail',
    'clear',
    'exit',
    'fg',
    'maintail',
    'open',
    'pid',
    'quit',
    'reload'
    'remove',
    'reread',
    'restart',
    'shutdown',
    'signal',
    'start',
    'status',
    'stop',
    'tail',
    'update',
    'version'
]


class Console:

    def __init__(self, stdin=None, stdout=None):
        self.sock = sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_address = ('localhost', 10000)
        self.prompt = '> '

    def set_signals(self):
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, signum, frame):
        if signum == signal.SIGINT or signum == signal.SIGTERM:
            print('closing socket')
            self.sock.close()
            sys.exit("exiting...")

    def run_forever(self):
        while 1:
            command = input(self.prompt)
            self.send_stuff(command)

    def send_stuff(self, command):

        # Create a TCP/IP socket
        try:
            print('connecting to %s port %s' % self.server_address)
            self.sock.connect(self.server_address)
        except OSError as e:
            print('already connected')

        try:
            
            # Send data
            message = command.encode()
            print('sending "%s"' % message)
            self.sock.sendall(message)

            # Look for the response
            amount_received = 0
            amount_expected = len(message)
            
            while amount_received < amount_expected:
                data = self.sock.recv(16)
                amount_received += len(data)
                print('received "%s"' % data)

        finally:
            print('done')


def main():
    print(snake)
    c = Console()
    c.set_signals()
    c.run_forever()


if __name__ == "__main__":
    main()
