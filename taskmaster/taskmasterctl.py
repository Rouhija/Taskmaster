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
from taskmaster.editor import Editor
from taskmaster.config import Config
from taskmaster.utils import parser
from os.path import dirname, realpath

parent_dir = dirname(dirname(realpath(__file__)))

logging.basicConfig(
    filename=f'{parent_dir}/logs/taskmasterctl.log',
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
    \x1B[3mTaskmaster\x1B[23m
"""


class Console:

    def __init__(self, stdin=None, stdout=None):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_address = ('localhost', 10000)
        self.prompt = '> '
        self.buf = 256

    def set_signals(self):
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, signum, frame):
        if signum == signal.SIGINT or signum == signal.SIGTERM:
            self.cleanup()

    def run_forever(self):
        e = Editor()
        while 1:
            command = e.read_in()
            if command == None : break
            elif command == '' : pass
            elif parser(command):
                response = self.send_to_daemon(command)
                self.status(response)
        self.cleanup()


    def status(self, response):
        res = response.split('|')
        for proc in res:
            if proc:
                proc = proc.split(' ')
                name = proc[0].upper()
                try:
                    status = self.p_status[proc[1]]
                except KeyError:
                    status = 'UNKNOWN'
                pid = proc[2]
                uptime = proc[3]
                print('{:{width}}'.format(name, width=25), end ='')
                print('{:{width}}'.format(status, width=10), end ='')
                print('pid {}, '.format(pid, width=10), end ='')
                print('uptime {:{width}}'.format(uptime, width=10))

# '{:{width}.{prec}f}'.format(2.7182, width=5, prec=2)

    def send_to_daemon(self, command):

        # Create a TCP/IP socket
        try:
            LOG.debug('connecting to %s port %s' % self.server_address)
            self.sock.connect(self.server_address)
        except OSError as e:
            LOG.debug('already connected')

        try:
            # Send to daemon
            b_command = command.encode()
            LOG.info('to taskmasterd %s' % b_command)
            self.sock.sendall(b_command)

            # Get response       
            data = self.sock.recv(self.buf).decode()

        finally:
            LOG.info('from taskmasterd "%s"' % data)
            return data

    def cleanup(self):
        try:
            LOG.debug('closing socket')
            self.sock.close()
        finally:
            sys.exit()

    p_status = {
        'None': 'RUNNING'
    }


def main():
    print(snake)
    c = Console()
    c.set_signals()
    c.run_forever()


if __name__ == "__main__":
    main()
