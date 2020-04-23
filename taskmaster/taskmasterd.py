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
from subprocess import Popen
from time import gmtime, strftime, time
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
        self.client_address = None
        self.connection = None

    def set_signals(self):
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, signum, frame):
        if signum == signal.SIGINT or signum == signal.SIGTERM:
            try:
                for p_info in self.processes:
                    LOG.debug(f'killing {p_info["pid"]}')
                    p_info['p'].kill()
                self.connection.close()
            finally:
                LOG.debug('taskmasterd shut down')
                sys.exit()

    def listen_sockets(self):
        # Create a TCP/IP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(self.server_address)
        self.sock.listen(1)

    def start(self):
        self.listen_sockets()
        self.set_signals()
        for k, _ in self.programs.items():
            self.init_program(k)
        self.program_status()
        self.serve_forever()

    def serve_forever(self):
        while 1:
            LOG.debug('waiting for a connection')
            self.connection, self.client_address = self.sock.accept()
            try:
                LOG.debug(f'connection from {self.client_address}')
                # Receive the data in small chunks and retransmit it
                while True:
                    data = self.connection.recv(16)
                    LOG.debug(f'received "{data}"')
                    if data:
                        LOG.debug('sending data back to the client')
                        self.connection.sendall(data)
                    else:
                        break
            finally:
                LOG.debug(f'all data from received from {self.client_address}')

    def init_program(self, prog):
        p_info = {}
        conf = self.programs[prog]
        log_stdout = open(conf['stdout_logfile'], 'w+')
        log_stderr = open(conf['stderr_logfile'], 'w+')
        p = Popen(
            [conf['command']],
            stdout=log_stdout,
            stderr=log_stderr
        )
        p_info['p'] = p
        p_info['pid'] = p.pid
        p_info['start'] = time()
        self.processes.append(p_info)

    def program_status(self):
        for p_info in self.processes:
            print(p_info['p'].poll())
            print(p_info['pid'])
            print(strftime('%H:%M:%S', gmtime(time() - p_info['start'])))

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