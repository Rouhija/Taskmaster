#!/usr/bin/python3

"""taskmasterd -- run a set of applications as daemons.

Usage: %s [options]

Options:
-h/--help -- display options
-c/--configuration <file> -- configuration file path
-n/--nodaemon -- run taskmasterd in the foreground
"""

import os
import sys
import signal
import socket
import asyncio
import logging
import argparse
from taskmaster.manager import Manager
from taskmaster.utils import arg_parserd, loggerd_options
from taskmaster.config import Config, ConfigError

LOG = logging.getLogger(__name__)

class Taskmasterd:

    def __init__(self, conf):
        self.conf = conf
        self.umask = 0o22
        self.directory = "/"
        self.buffer = 1028
        self.test = 'None'
        self.manager_wait = 3
        self.m = Manager(conf)

    def listen_signals(self):
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGQUIT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, signum, frame):
        if signum == signal.SIGINT or signum == signal.SIGQUIT or signum == signal.SIGTERM:
            self.cleanup()

    def cleanup(self):
        self.loop.stop()

    def blocking(self):
        while self.block:
            pass
        return

    def start(self):
        self.listen_signals()
        self.loop = asyncio.get_event_loop()
        self.loop.create_task(asyncio.start_server(self.handle_client, 'localhost', self.conf['server']['port']))
        self.loop.create_task(self.manage_programs())
        self.loop.run_forever()
        self.cleanup()

    async def handle_client(self, reader, writer):
        request = None
        try:
            while True:
                self.block = True
                request = (await reader.read(self.buffer)).decode('utf8')
                self.block = False
                response = await self.process_request(request)
                writer.write(response.encode('utf8'))
                await writer.drain()
            writer.close()
        except ConnectionResetError:
            LOG.info('client closed connection')

    async def process_request(self, request):
        LOG.info(request)
        response = str(request) + ' response'
        return response

    async def manage_programs(self):
        try:
            await self.m.init_programs()
            while(1):
                LOG.info('manager doing stuff...')
                await asyncio.sleep(self.manager_wait)
        finally:
            await self.m.stop_programs(['all'])

    def daemonize(self):
        """
        This function daemonizes the program like Supervisor
            1. We need to fork the parent process to ensure it's not the process leader
            2. Change working directory to /
            3. Close stdin, stdout, stderr
            4. setsid() makes the process a process leader in the new group
            5. set default umask
        """
        pid = os.fork()
        if pid != 0:
            LOG.debug("taskmasterd forked; parent exiting")
            os._exit(0)
        LOG.info("daemonizing the taskmasterd process")
        try:
            os.chdir(self.directory)
        except OSError as err:
            LOG.critical("can't chdir into %r: %s" % (self.directory, err))
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
    args = arg_parserd()
    loggerd_options(args.nodaemon)
    try:
        config = Config(args.configuration)
    except ConfigError as e:
        sys.exit(f'ConfigError: {e}')
    d = Taskmasterd(config.conf)
    print('Server starting...')
    if not args.nodaemon:
        d.daemonize()
    d.start()


if __name__ == '__main__':
    main()
