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
            if command == None or command == 'quit' or command == 'exit' : break
            elif command == '' : pass
            elif parser(command):
                response = self.send_to_daemon(command)
                if response is None or response == 'error':
                    LOG.warn('No response from daemon')
                else:
                    self.fmap[command.split(' ')[0]](self, response)
        self.cleanup()


    def resp_general(self, response):
        resp = response.split('|')
        for r in resp:
            if r:
                print(r)


    def resp_status(self, response):
        res = response.split('|')
        for proc in res:
            if proc:
                proc = proc.split(' ')
                name = proc[0].upper()
                status = proc[1]
                pid = proc[2]
                uptime = proc[3]
                print('{:{width}}'.format(name, width=25), end ='')
                print('{:{width}}'.format(status, width=10), end ='')
                print('pid {}, '.format(pid, width=10), end ='')
                print('uptime {:{width}}'.format(uptime, width=10))

    def send_to_daemon(self, command):

        response = None

        # Connect to daemon
        try:
            LOG.debug('connecting to %s port %s' % self.server_address)
            self.sock.connect(self.server_address)
        except OSError as e:
            LOG.debug('already connected')

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

    fmap = {
        'status': resp_status,
        'stop': resp_general,
        'start': resp_general
    }


def main():
    print(snake)
    c = Console()
    c.set_signals()
    c.run_forever()


if __name__ == "__main__":
    main()
