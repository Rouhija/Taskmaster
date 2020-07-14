#!/usr/bin/python3

"""taskmasterd -- run a set of applications as daemons.

Usage: %s [options]

Options:
-h/--help -- display options
-c/--configuration <file> -- configuration file path
-n/--nodaemon -- run taskmasterd in the foreground
"""

import io
import os
import sys
import signal
import socket
import asyncio
import logging
import argparse
from copy import deepcopy
from taskmaster.utils import arg_parserd, loggerd_options
from time import gmtime, strftime, time, sleep
from taskmaster.config import Config, ConfigError
from subprocess import PIPE, Popen, TimeoutExpired

LOG = logging.getLogger(__name__)

class Taskmasterd:

    def __init__(self, conf):
        self.conf = conf
        self.conf_backup = conf
        self.programs = deepcopy(conf['programs'])
        self.umask = 0o22
        self.directory = "/"
        self.buffer = 1028
        self.test = 'None'

    def listen_signals(self):
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGQUIT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, signum, frame):
        if signum == signal.SIGINT or signum == signal.SIGQUIT or signum == signal.SIGTERM:
            self.cleanup()

    def cleanup(self):
        self.loop.stop()

    def start(self):
        self.listen_signals()
        # self.queue = asyncio.Queue()
        self.loop = asyncio.get_event_loop()
        self.loop.create_task(asyncio.start_server(self.handle_client, 'localhost', self.conf['server']['port']))
        self.loop.create_task(self.manager())
        self.loop.run_forever()

    async def handle_client(self, reader, writer):
        request = None
        try:
            while request != 'shutdown\n':
                request = (await reader.read(self.buffer)).decode('utf8')
                # self.queue.put_nowait(request)
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

    async def manager(self):
        while(1):
            LOG.info('manager doing stuff...')
            await asyncio.sleep(2)


def main():
    args = arg_parserd()
    loggerd_options(args.nodaemon)
    try:
        config = Config(args.configuration)
    except ConfigError as e:
        sys.exit(f'ConfigError: {e}')
    d = Taskmasterd(config.conf)
    print('Server starting...')
    # if not args.nodaemon:
    #     d.daemonize()
    d.start()


if __name__ == '__main__':
    main()
