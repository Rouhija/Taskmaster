#!/usr/bin/python3

"""taskmasterd -- run a set of applications as daemons.

Usage: %s [options]

Options:
-h/--help -- display options
-c/--configuration <file> -- configuration file path (searches if not given)
-n/--nodaemon -- run taskmasterd in the foreground
"""

import os
import sys
import signal
import socket
import logging
import argparse
from subprocess import Popen
from time import gmtime, strftime, time
from taskmaster.config import Config
from os.path import dirname, realpath


LOG = logging.getLogger(__name__)


class Taskmasterd:

    def __init__(self, conf):
        self.conf = conf
        self.directory = "/"
        self.programs = conf['programs']
        self.buf = 256
        self.umask = 0o22
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
                    LOG.debug(f'killing pid {p_info["pid"]}')
                    p_info['p'].kill()
                self.connection.close()
            finally:
                LOG.debug('taskmasterd shut down')
                sys.exit()


    def listen_sockets(self):
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
                # Receive data from control program
                while True:
                    data = self.connection.recv(16)
                    LOG.debug(f'received "{data}"')
                    if data:
                        response = self.action(data.decode())
                        LOG.debug(f'sending response [{response}] back to the client')
                        self.connection.sendall(response.encode())
                    else:
                        break
            finally:
                LOG.debug(f'Connection closed by client {self.client_address}')


    def action(self, command):
        command = command.split(' ')
        if command[0] == 'reload':
            # os.execv(__file__, sys.argv)
            return 'not implemented'
        elif command[0] == 'status':
            return self.program_status()
        return '1'


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
        p_info['name'] = prog
        p_info['p'] = p
        p_info['pid'] = p.pid
        p_info['start'] = time()
        self.processes.append(p_info)


    def program_status(self):
        status = ''
        for p_info in self.processes:
            status += p_info['name'] + ' '
            status += str(p_info['p'].poll()) + ' '
            status += str(p_info['pid']) + ' '
            status += str(strftime('%H:%M:%S', gmtime(time() - p_info['start']))) + '|'
        return status


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
            LOG.debug("taskmasterd forked; parent exiting")
            os._exit(0)
        LOG.debug("daemonizing the taskmasterd process")
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


def logger_options(nodaemon):
    if nodaemon:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(levelname)s:%(asctime)s ⁠— %(message)s',
            datefmt='%d/%m/%Y %H:%M:%S'
        )
    else:
        parent_dir = dirname(dirname(realpath(__file__)))
        logging.basicConfig(
            filename=f'{parent_dir}/logs/taskmasterd.log',
            level=logging.DEBUG,
            format='%(levelname)s:%(asctime)s ⁠— %(message)s',
            datefmt='%d/%m/%Y %H:%M:%S'
        )  


def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--configuration", help="The path to a taskmasterd configuration file.", action="store_true")
    parser.add_argument("-n", "--nodaemon", help="Run taskmasterd in the foreground", action="store_true")
    parser.add_argument("-m", "--umask", help="Octal number (e.g. 022) representing the umask that should be used by taskmasterd after it starts.", default='022')
    return parser.parse_args()


def main():
    args = arg_parser()
    logger_options(args.nodaemon)
    config = Config()
    d = Taskmasterd(config.conf)
    if not args.nodaemon:
        d.daemonize()
    d.start()


if __name__ == '__main__':
    main()