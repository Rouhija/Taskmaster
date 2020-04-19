#!/usr/bin/python3

"""taskmasterd -- run a set of applications as daemons.

Usage: %s [options]

Options:
-c/--configuration <file> -- configuration file path (searches if not given)
"""

import os
import sys
import signal
from time import sleep
from subprocess import Popen
from taskmaster.config import Config


class Taskmasterd:

    def __init__(self, conf):
        self.conf = conf
        self.directory = "/"
        self.programs = conf['programs']
        self.umask = 22
        self.active = []

    def set_signals(self):
        signal.signal(signal.SIGINT, self.signal_handler)

    def signal_handler(self):
        for pid in self.active:
            pid.kill()

    def run(self):
        for k, v in self.programs.items():
            self.init_program(k)
        while 1:

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
        self.active.append(p)

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
            print("supervisord forked; parent exiting")
            os._exit(0)
        print("daemonizing the supervisord process")
        try:
            os.chdir(self.directory)
        except OSError as err:
            print("can't chdir into %r: %s" % (self.directory, err))
        else:
            print("set current directory: %r" % self.directory)
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
    d.set_signals()
    d.daemonize()
    while (1):
        d.run()
    
if __name__ == '__main__':
    main()