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
            self.cleanup()


    def cleanup(self):
        try:
            for p_info in self.processes:
                LOG.debug(f'killing pid {p_info["pid"]}')
                p_info['p'].kill()
            self.connection.sendall('taskmasterd shut down successfully'.encode())
            self.connection.close()
        finally:
            LOG.debug('taskmasterd shut down')
            sys.exit()


    def listen_sockets(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(self.server_address)
        self.sock.listen(1)


    def start_server(self):
        self.listen_sockets()
        self.set_signals()
        for k, _ in self.programs.items():
            self.init_program(k)
        self.serve_forever()


    def init_program(self, prog):
        p_info = {}
        conf = self.programs[prog]
        log_stdout = open(conf['stdout_logfile'], 'w+')
        log_stderr = open(conf['stderr_logfile'], 'w+')
        if conf['autostart'] == 'true':
            p = Popen(
                [conf['command']],
                stdout=log_stdout,
                stderr=log_stderr
            )
            p_info['p'] = p
            p_info['state'] = 'RUNNING'
            p_info['start'] = time()
        else:
            p_info['p'] = None
            p_info['state'] = 'STOPPED'
            p_info['start'] = None
        p_info['name'] = prog
        p_info['pid'] = p.pid
        self.processes.append(p_info)


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
                        if data.decode() == 'shutdown':
                            self.cleanup()
                        response = self.action(data.decode())
                        LOG.debug(f'sending response [{response}] back to the client')
                        if response:
                            self.connection.sendall(response.encode())
                        else:
                            self.connection.sendall(f'no actions for `{data.decode()}`'.encode())
                    else:
                        break
            except OSError as e:
                LOG.error(e)
            finally:
                LOG.debug(f'All data received from {self.client_address}')


    def action(self, command):
        command = command.split(' ')
        try:
            return self.fmap[command[0]](self, command)
        except:
            return None


    def prog_status(self, command):
        status = ''
        for p_info in self.processes:
            status += '{:{width}}'.format(p_info['name'], width=25)
            if p_info['p'].poll() is None:
                status += '{:{width}}'.format(p_info['state'], width=10)
            else:
                status += '{:{width}}'.format('STOPPED', width=10)
            status += 'pid {}, '.format(p_info['pid'], width=10)
            status += 'uptime {:{width}} |'.format(strftime('%H:%M:%S', gmtime(time() - p_info['start'])), width=10)
        return status


    def prog_start(self, command):
        resp = ''
        command.pop(0)
        for name in command:
            for i, proc in enumerate(self.processes):
                if proc['name'] == name or name == 'all':
                    if proc['state'] == 'STOPPED':
                        LOG.info(f'Starting process {proc["pid"]}')
                        proc['p'].send_signal(signal.SIGCONT)
                        resp += f'{proc["name"]} started|'
                        self.processes[i]['state'] = 'RUNNING'
                    else:
                        resp += f'{proc["name"]} is already running|'
        return resp        

    
    def prog_stop(self, command):
        resp = ''
        command.pop(0)
        for name in command:
            for i, proc in enumerate(self.processes):
                if proc['name'] == name or name == 'all':
                    if proc['state'] == 'RUNNING':
                        LOG.info(f'Stopping process {proc["pid"]}')
                        proc['p'].send_signal(signal.SIGSTOP)
                        resp += f'{proc["name"]} stopped|'
                        self.processes[i]['state'] = 'STOPPED'
                    else:
                        resp += f'{proc["name"]} is already stopped|'
        return resp


    def prog_restart(self, command):
        # LOG.info(f'Restarting programs {command[1:]}')
        # resp = self.prog_stop(command)
        # resp = self.prog_start(command)
        # resp = resp.replace('stopped', 'restarted')
        return 'error'


    def reread_conf(self, command):
        config = Config()
        self.conf = config.conf
        return 'Configuration file reread successfully - run update to apply changes'


    def reload(self, command):
        # os.execv(__file__, sys.argv)
        return 'error'


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

    fmap = {
        'status': prog_status,
        'start': prog_start,
        'stop': prog_stop,
        'reread': reread_conf,
        'restart': prog_restart
    }


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
    d.start_server()


if __name__ == '__main__':
    main()