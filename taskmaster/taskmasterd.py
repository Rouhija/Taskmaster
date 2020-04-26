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
from copy import deepcopy
from os.path import dirname, realpath
from subprocess import Popen, TimeoutExpired
from time import gmtime, strftime, time, sleep
from taskmaster.config import Config, ConfigError


LOG = logging.getLogger(__name__)

RUNNING = 'RUNNING'
STOPPED = 'STOPPED'


class Taskmasterd:

    def __init__(self, conf):
        self.conf = conf
        self.conf_backup = conf
        self.programs = deepcopy(conf['programs'])
        self.buf = 256
        self.umask = 0o22
        self.directory = "/"
        self.server_address = ('localhost', 10000)
        self.client_address = None
        self.connection = None


    def set_signals(self):
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)


    def signal_handler(self, signum, frame):
        if signum == signal.SIGINT or signum == signal.SIGTERM or signal.SIGABRT:
            self.cleanup()


    def cleanup(self):
        try:
            self.stop_programs(['all'])
            self.connection.sendall('taskmasterd shut down successfully'.encode())
            self.connection.close()
        finally:
            LOG.debug('taskmasterd shut down')
            sys.exit()


    def init_programs(self):
        startup = []
        for name, v in self.conf['programs'].items():
            if v['autostart']:
                startup.append(name)
            else:
               self.programs[name]['p'] = None
               self.programs[name]['pid'] = None
               self.programs[name]['state'] = STOPPED
               self.programs[name]['start_ts'] = None
        if len(startup):
            self.start_programs(startup)


    def listen_sockets(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(self.server_address)
        self.sock.listen(1)


    def start_server(self):
        self.listen_sockets()
        self.set_signals()
        self.init_programs()
        self.serve_forever()


    def serve_forever(self):
        while 1:
            LOG.debug('waiting for a connection')
            self.connection, self.client_address = self.sock.accept()
            try:
                LOG.debug(f'connection from {self.client_address}')
                # Receive data from control program
                while True:
                    data = self.connection.recv(self.buf)
                    LOG.debug(f'received "{data}"')
                    if data:
                        data = data.decode()
                        if data == 'shutdown':
                            self.cleanup()
                        response = self.action(data)
                        LOG.debug(f'sending response [{response}] back to the client')
                        if response:
                            self.connection.sendall(response.encode())
                        else:
                            self.connection.sendall(f'no actions for `{data}`'.encode())
                    else:
                        break
            except OSError as e:
                LOG.error(e)
            finally:
                LOG.debug(f'All data received from {self.client_address}')


    def action(self, command):
        command = command.split(' ')
        try:
            if command[0] == 'status':
                return self.get_status()
            elif command[0] == 'start':
                return self.start_programs(command[1:])
            elif command[0] == 'stop':
                return self.stop_programs(command[1:])
            elif command[0] == 'restart':
                return self.restart_programs(command[1:])
            elif command[0] == 'reread':
                return self.reread()
            elif command[0] == 'update':
                return self.update()
        except Exception as e:
            LOG.error(e)
            return None


    def start_programs(self, command):
        response = ''
        if command[0] == 'all':
            command = []
            for k, _ in self.programs.items():
                command.append(k)
        for name in command:
            response += self.start(name)
        return response


    def start(self, name):
        try:
            if self.programs[name]['p'].poll() == None:
                response = f'{name} is already running|'
        except:
            restarts = self.programs[name]['restarts']
            startup_wait = self.programs[name]['startup_wait']
            log_stdout = self.programs[name]['stdout_logfile']
            log_stderr = self.programs[name]['stderr_logfile']

            if isinstance(log_stdout, str):
                stdout = open(log_stdout, 'w+')
            if isinstance(log_stderr, str):
                stderr = open(log_stderr, 'w+')

            while 1:
                p = Popen(
                    self.programs[name]['command'],
                    stdout=stdout,
                    stderr=stderr
                )
                sleep(startup_wait)
                if p.poll() == None:
                    self.programs[name]['p'] = p
                    self.programs[name]['state'] = RUNNING
                    self.programs[name]['start_ts'] = time()
                    self.programs[name]['pid'] = p.pid
                    LOG.info(f'{name} started successfully with pid {p.pid}')
                    response = f'{name} started successfully|'
                    break
                elif restarts:
                    sleep(0.1)
                    restarts -= 1
                else:
                    LOG.warn(f'starting {name} was unsuccessful after {self.programs[name]["restarts"]} retries')
                    response = f'starting {name} was unsuccessful after {self.programs[name]["restarts"]} retries'
                    self.programs[name]['p'] = None
                    self.programs[name]['pid'] = None
                    self.programs[name]['state'] = STOPPED
                    self.programs[name]['start_ts'] = None
                    break
        return response


    def stop_programs(self, command):
        response = ''
        if command[0] == 'all':
            command = []
            for k, _ in self.programs.items():
                command.append(k)
        for name in command:
            response += self.stop(name)
        return response


    def stop(self, name):
        if self.programs[name]['p'] is not None:
            kill_signal = self.programs[name]['stop_signal']
            kill_timeout = self.programs[name]['kill_timeout']

            LOG.info(f'Stopping process {self.programs[name]["pid"]}')
            self.programs[name]['p'].send_signal(kill_signal)
            try:
                self.programs[name]['p'].wait(timeout=kill_timeout)
                LOG.info(f'stopped pid {self.programs[name]["pid"]} successfully')
                response = f'stopped {name} successfully|'
            except TimeoutExpired:
                self.programs[name]['p'].kill()
                LOG.warn(f'Killed pid {self.programs[name]["pid"]} after timeout ({kill_timeout} seconds)')
                response = f'Killed {name} after timeout ({kill_timeout} seconds)|'
            finally:
                self.programs[name]['p'] = None
                self.programs[name]['state'] = STOPPED
                self.programs[name]['start_ts'] = None
                self.programs[name]['pid'] = None
        else:
            response = f'{name} is already stopped|'
        return response


    def restart_programs(self, command):
        response = ''
        LOG.info(f'Restarting programs {command}')
        for name in command:
            self.stop(name)
            response += self.start(name)
            response = response.replace('started', 'restarted')
        return response


    def get_status(self):
        status = ''
        for k, v in self.programs.items():
            status += '{:{width}}'.format(k, width=25)
            status += '{:{width}}'.format(v['state'], width=10)
            if v['pid']:
                pid = 'pid {}, '.format(v['pid'])
            else:
                pid = 'pid {}, '.format('None')
            status += '{:{width}}'.format(pid, width=11)    
            if v['start_ts']:
                status += 'uptime {:{width}} |'.format(strftime('%H:%M:%S', gmtime(time() - v['start_ts'])), width=10)
            else:
                status += 'uptime {:{width}} |'.format('--:--:--', width=10)
        return status


    def reread(self):
        response = None
        try:
            config = Config()
            self.conf = config.conf
            response = 'Configuration file reread successfully - run `update` to apply changes'
        except ConfigError as e:
            self.conf = self.conf_backup
            response = f"Couldn't read configuration:|-->\t{e}"
        finally:
            return response


    def update(self):
        try:
            for k, v in self.conf['programs'].items():
                if not k in self.conf_backup['programs'] and v['autostart']:
                    LOG.info(f'New program in configuration [{k}]: starting')
                    self.programs[k] = deepcopy(v)
                    self.start(k)
                elif not k in self.conf_backup['programs'] and not v['autostart']:
                    LOG.info(f'New program in configuration [{k}]: no autostart')
                    self.programs[k] = deepcopy(v)
                    self.programs[k]['p'] = None
                    self.programs[k]['pid'] = None
                    self.programs[k]['state'] = STOPPED
                    self.programs[k]['start_ts'] = None
                elif self.conf['programs'][k] != self.conf_backup['programs'][k] and v['autostart']:
                    LOG.info(f'Configuration for [{k}] changed: restarting')
                    self.stop(k)
                    self.programs[k] = deepcopy(v)
                    self.start(k)
                elif self.conf['programs'][k] != self.conf_backup['programs'][k] and not v['autostart']:
                    LOG.info(f'Configuration for [{k}] changed: no autostart')
                    self.stop(k)
                    self.programs[k] = deepcopy(v)
            for k, _ in self.conf_backup['programs'].items():
                if not k in self.conf['programs']:
                    LOG.info(f'[{k}] removed: stopping')
                    self.stop(k)
                    del self.programs[k]
        except Exception as e:
            LOG.error(e)
            return f'Error in update: {e}'
        self.conf_backup = self.conf
        return 'Update ran successfully'


    def daemonize(self):
        """
        This function daemonizes the program like Supervisor
            1. We need to fork the parent process to ensure it's not the process leader
            2. Change working directory to /
            3. Close stdin, stdout, stderr
            4. setsid() makes the process a process leader in the new group
            5. set default umask to 022
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
    return


def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--configuration", help="The path to a taskmasterd configuration file", action="store_true")
    parser.add_argument("-n", "--nodaemon", help="Run taskmasterd in the foreground", action="store_true")
    return parser.parse_args()


def main():
    args = arg_parser()
    logger_options(args.nodaemon)
    try:
        config = Config()
    except ConfigError as e:
        sys.exit(f'ConfigError: {e}')
    d = Taskmasterd(config.conf)
    if not args.nodaemon:
        d.daemonize()
    d.start_server()


if __name__ == '__main__':
    main()