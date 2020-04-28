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
import logging
import argparse
from copy import deepcopy
from os.path import dirname, realpath
from time import gmtime, strftime, time, sleep
from taskmaster.config import Config, ConfigError
from subprocess import PIPE, Popen, TimeoutExpired


LOG = logging.getLogger(__name__)

RUNNING = 'RUNNING'
STOPPED = 'STOPPED'
UNKNOWN = 'UNKNOWN'
KILLED = 'EXITED'


class Taskmasterd:

    def __init__(self, conf):
        self.conf = conf
        self.conf_backup = conf
        self.programs = deepcopy(conf['programs'])
        self.umask = 0o22
        self.directory = "/"
        self.exit = False
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_address = ('localhost', conf['server']['port'])
        self.client_address = None
        self.connection = None
        self.buf = 1028
        self.conn_timeout = 3 # prefer shorter timeouts
        self.data_timeout = 10 # set to high, 30 etc.

    def listen_signals(self):
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGQUIT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, signum, frame):
        if signum == signal.SIGINT or signum == signal.SIGQUIT or signum == signal.SIGTERM:
            self.cleanup()

    def cleanup(self):
        try:
            self.stop_programs(['all'])
            self.connection.sendall('shut down successfully'.encode())
            self.connection.close()
        except Exception as e:
            LOG.warn(f'shut down: {e}')
        finally:
            self.sock.close()
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

    def run(self):
        self.listen_signals()
        self.init_programs()
        self.serve_forever()
        self.cleanup()

    def serve_forever(self):

        LOG.debug('starting server')
        try:
            self.sock.bind(self.server_address)
            self.sock.listen(1)
            self.sock.settimeout(self.conn_timeout)
        except OSError:
            LOG.error(f'port {self.conf["server"]["port"]} is in use, exiting')
            return

        while 1:
            LOG.debug('waiting for a connection')
            try:
                self.connection, self.client_address = self.sock.accept()
                self.connection_established()
                if self.exit is True:
                    return
            except socket.timeout as e:
                if e.args[0] == 'timed out':
                    sleep(0.5)
                    LOG.debug(f'no connection after {self.conn_timeout} seconds, checking programs')
                    self.manager()
            except socket.error as e:
                LOG.error(e)
                return  

    def connection_established(self):
        try:
            LOG.info(f'connection from {self.client_address}')
            self.connection.settimeout(self.data_timeout)
            while True:
                try:
                    data = self.connection.recv(self.buf)
                    LOG.debug(f'received "{data}"')
                    if data:
                        data = data.decode()
                        if data == 'shutdown':
                            self.exit = True
                            return
                        response = self.action(data)
                        LOG.debug(f'sending response [{response}] back to the client')
                        if response:
                            self.connection.sendall(response.encode())
                        else:
                            self.connection.sendall(f'response: None'.encode())
                    else:
                        break
                except socket.timeout as e:
                    if e.args[0] == 'timed out':
                        sleep(0.5)
                        LOG.debug(f'no data from {self.client_address} after {self.data_timeout} seconds, checking programs')
                        self.manager()
                        continue
                except socket.error as e:
                    LOG.error(e)
                    self.exit = True
                    return                
        except Exception as e:
            LOG.error(e)
        finally:
            LOG.debug(f'All data received from {self.client_address}')

    def manager(self):
        try:
            for k, v in self.programs.items():
                autorestart = self.programs[k]['autorestart'] 
                p = self.programs[k]['p']
                if p is not None:
                    exit_code = p.poll()
                    if exit_code is not None and self.programs[k]['state'] == RUNNING:
                        self.programs[k]['state'] = KILLED
                        self.programs[k]['start_ts'] = None
                        self.programs[k]['pid'] = None
                        LOG.info(f'{k} exited with {exit_code}')
                        if autorestart == 'always' or (autorestart == 'unexpected' and exit_code not in self.programs[k]['expected_exit']):
                            self.restart_programs([k])
        except Exception as e:
            LOG.error(f'manager: {e}')
        finally:
            return

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
            elif command[0] == 'tail':
                return self.tail(command[1], command[2])
            elif command[0] == 'reread':
                return self.reread()
            elif command[0] == 'update':
                return self.update()
        except Exception as e:
            LOG.error(f'action: {e}')
            return f'{e} not found'

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
        if self.check_if_running(name):
            return f'{name} is already running|'
        cwd = os.getcwd()
        work_dir = self.programs[name]['dir']
        restarts = self.programs[name]['restarts']
        startup_wait = self.programs[name]['startup_wait']
        log_stdout = self.programs[name]['stdout_logfile']
        log_stderr = self.programs[name]['stderr_logfile']

        if isinstance(log_stdout, str):
            log_stdout = open(log_stdout, 'w+')
        if isinstance(log_stderr, str):
            log_stderr = open(log_stderr, 'w+')

        if work_dir is not None:
            try:
                os.chdir(work_dir)
                LOG.debug(f'cd to working dir {work_dir}')
            except IOError as e:
                LOG.error(e)
                return f"Can't use working dir {dir} for {name}"
        os.umask(self.programs[name]['umask'])
        while 1:
            p = Popen(
                self.programs[name]['command'],
                stdout=log_stdout,
                stderr=log_stderr,
                env=self.programs[name]['environment']
            )
            sleep(startup_wait)
            if p.poll() is None:
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
        if work_dir is not None:
            try:
                LOG.debug(f'cd to cwd {cwd}')
                os.chdir(cwd)
            except IOError as e:
                LOG.error(e)
                return f'{e}'
        if isinstance(log_stdout, io.IOBase):
            log_stdout.close()
        if isinstance(log_stderr, io.IOBase):
            log_stderr.close()         
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
        p = self.programs[name]['p']
        if p is not None:
            kill_signal = self.programs[name]['stop_signal']
            kill_timeout = self.programs[name]['kill_timeout']
            if self.programs[name]['stdout_logfile'] == PIPE:
                p.stdout.close()
            if self.programs[name]['stderr_logfile'] == PIPE:
                p.stderr.close()
            LOG.info(f'Stopping process {self.programs[name]["pid"]}')
            p.send_signal(kill_signal)
            try:
                p.wait(timeout=kill_timeout)
                LOG.info(f'stopped pid {self.programs[name]["pid"]} successfully')
                response = f'stopped {name} successfully|'
                self.programs[name]['state'] = STOPPED
            except TimeoutExpired:
                p.kill()
                LOG.warn(f'Killed pid {self.programs[name]["pid"]} after timeout ({kill_timeout} seconds)')
                response = f'Killed {name} after timeout ({kill_timeout} seconds)|'
                self.programs[name]['state'] = KILLED
            finally:
                self.programs[name]['p'] = None
                self.programs[name]['start_ts'] = None
                self.programs[name]['pid'] = None
        else:
            response = f'{name} is already stopped|'
        return response

    def restart_programs(self, command):
        response = ''
        if command[0] == 'all':
            for k, _ in self.programs.items():
                command.append(k)
            command.pop(0)
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
            if 'state' in v:
                status += '{:{width}}'.format(v['state'], width=10)
            else:
                status += '{:{width}}'.format(UNKNOWN, width=10)
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
                    self.programs[k]['p'] = None
                    self.programs[k]['pid'] = None
                    self.programs[k]['state'] = STOPPED
                    self.programs[k]['start_ts'] = None
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
    
    def tail(self, name, fd):
        stream = f'{fd}_logfile'
        logs = self.programs[name][stream]
        if logs == '/dev/null':
            return f'{name}: output is directed to /dev/null'
        elif isinstance(logs, str):
            p = Popen(
                ['tail', logs],
                stdout=PIPE,
                stderr=PIPE
            )
            try:
                out, err = p.communicate(timeout=3)
            except TimeoutExpired:
                return 'Error calling tail (timeout after 3 seconds)'
            if len(out):
                return out.decode()
            elif len(err):
                return err.decode()
        else:
            p = self.programs[name]['p']
            r = ''
            i = 0
            while i < 10:
                if fd == 'stdout':
                    line = p.stdout.readline()
                elif fd == 'stderr':
                    line = p.stderr.readline()
                else:
                    return None
                if line:
                    r += f'{line}|'
                i += 1
            return r


    def check_if_running(self, name):
        if 'p' in self.programs[name]:
            if self.programs[name]['p'] is not None:
                if self.programs[name]['p'].poll() is None:
                    return True
        return False

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



def logger_options(nodaemon):
    if nodaemon:
        logging.basicConfig(
            level=logging.INFO,
            format='%(levelname)s:%(asctime)s ⁠— %(message)s',
            datefmt='%d/%m/%Y %H:%M:%S'
        )
    else:
        work_dir = dirname(realpath(__file__))
        logging.basicConfig(
            filename=f'{work_dir}/resources/logs/taskmasterd.log',
            level=logging.INFO,
            format='%(levelname)s:%(asctime)s ⁠— %(message)s',
            datefmt='%d/%m/%Y %H:%M:%S'
        )
    return


def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--configuration", help="The path to a taskmasterd configuration file")
    parser.add_argument("-n", "--nodaemon", help="Run taskmasterd in the foreground", action="store_true")
    return parser.parse_args()


def main():
    args = arg_parser()
    logger_options(args.nodaemon)
    try:
        config = Config(args.configuration)
    except ConfigError as e:
        sys.exit(f'ConfigError: {e}')
    d = Taskmasterd(config.conf)
    print('Server starting...')
    if not args.nodaemon:
        d.daemonize()
    d.run()


if __name__ == '__main__':
    main()
