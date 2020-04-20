#!/usr/bin/python3

"""taskmasterd -- run a set of applications as daemons.

Usage: %s [options]

Options:
-c/--configuration <file> -- configuration file path (searches if not given)
"""

import os
import sys
import signal
import socket
import logging
from time import sleep
from subprocess import Popen
from taskmaster.config import Config
from os.path import dirname, realpath


parent_dir = dirname(dirname(realpath(__file__)))

logging.basicConfig(
    filename=f'{parent_dir}/logs/taskmasterd.log',
    level=logging.DEBUG,
    format='%(levelname)s:%(asctime)s ⁠— %(message)s',
    datefmt='%d/%m/%Y %H:%M:%S'
    )

LOG = logging.getLogger(__name__)

class Taskmasterd:

    def __init__(self, conf):
        self.conf = conf
        self.directory = "/"
        self.programs = conf['programs']
        self.umask = 22
        self.processes = []
        self.server_address = ('localhost', 10000)

    def set_signals(self):
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, signum, frame):
        if signum == signal.SIGINT or signum == signal.SIGTERM:
            for pid in self.processes:
                LOG.debug(f'killing {pid}')
                pid.kill()
            sys.exit("taskmasterd received terminating signal... quitting")

    def listen_sockets(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Create a TCP/IP socket
        self.sock.bind(self.server_address)
        self.sock.listen(1)

    def start(self):
        self.listen_sockets()
        self.set_signals()
        for k, _ in self.programs.items():
            self.init_program(k)
        self.serve_forever()

    def serve_forever(self):
        while 1:
            LOG.debug('waiting for a connection')
            connection, client_address = self.sock.accept()
            try:
                LOG.debug(f'connection from {client_address}')
                # Receive the data in small chunks and retransmit it
                while True:
                    data = connection.recv(16)
                    LOG.debug(f'received "{data}"')
                    if data:
                        LOG.debug('sending data back to the client')
                        connection.sendall(data)
                    else:
                        LOG.debug(f'no more data from {client_address}')
                        break
                    
            finally:
                connection.close()
            sleep(1)

    def init_program(self, prog):
        conf = self.programs[prog]
        log_stdout = open(conf['stdout_logfile'], 'w+')
        log_stderr = open(conf['stderr_logfile'], 'w+')
        p = Popen(
            [conf['command']],
            stdout=log_stdout,
            stderr=log_stderr
        )
        self.processes.append(p)

    def daemonize(self):
        """
        This function daemonizes the program.
            1. We need to fork the parent process and close it to disassociate the tty.
            2. Change directory to /
            3. Close fd's 1, 2, 3 and direct to /dev/null
            4. setsid() makes the process a process leader
            5. umask??
        """
        pid = os.fork()
        if pid != 0:
            LOG.debug("supervisord forked; parent exiting")
            os._exit(0)
        LOG.debug("daemonizing the supervisord process")
        try:
            os.chdir(self.directory)
        except OSError as err:
            LOG.error("can't chdir into %r: %s" % (self.directory, err))
        else:
            LOG.debug("set current directory: %r" % self.directory)
        os.close(0)
        self.stdin = sys.stdin = sys.__stdin__ = open("/dev/null")
        os.close(1)
        self.stdout = sys.stdout = sys.__stdout__ = open("/dev/null", "w")
        os.close(2)
        self.stderr = sys.stderr = sys.__stderr__ = open("/dev/null", "w")
        os.setsid()
        os.umask(self.umask)

def main():
    config = Config()
    d = Taskmasterd(config.conf)
    d.daemonize()
    d.start()
    
if __name__ == '__main__':
    main()