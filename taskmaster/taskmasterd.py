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
# import fcntl
import signal
import socket
import logging
import argparse
from copy import deepcopy
from multiprocessing import Process, Queue
from os.path import dirname, realpath
from time import gmtime, strftime, time, sleep
from taskmaster.config import Config, ConfigError
from subprocess import DEVNULL, PIPE, Popen, TimeoutExpired


LOG = logging.getLogger(__name__)

RUNNING = 'RUNNING'
STOPPED = 'STOPPED'
UNKNOWN = 'UNKNOWN'
SYSEXIT = 'SYSEXIT'


class Server:

    def __init__(self):
        self.server_address = ('localhost', 10000)
        self.client_address = None
        self.connection = None
        self.buf = 4096

    def listen_signals(self):
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, signum, frame):
        if signum == signal.SIGINT or signum == signal.SIGTERM:
            try:
                self.connection.close()
            finally:
                LOG.debug(f'server received signal {signum}: exiting')
                os._exit(signum)

    def serve_forever(self, queue):

        LOG.debug('starting server')
        self.listen_signals()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(self.server_address)
        self.sock.listen(1)
        self.sock.settimeout(2)

        while 1:
            LOG.debug('waiting for a connection')
            try:
                self.connection, self.client_address = self.sock.accept()
            except socket.timeout as e:
                err = e.args[0]
                if err == 'timed out':
                    sleep(1)
                    print('no connection, check programs')
                    continue
            try:
                LOG.info(f'connection from {self.client_address}')
                # fcntl.fcntl(self.sock, fcntl.F_SETFL, os.O_NONBLOCK)
                self.connection.settimeout(2)
                while True:
                    try:
                        data = self.connection.recv(self.buf)
                        LOG.debug(f'received "{data}"')
                        if data:
                            data = data.decode()
                            queue.put(data)
                            if data == 'shutdown':
                                self.stop_server()
                                return
                            response = queue.get()
                            LOG.debug(f'sending response [{response}] back to the client')
                            if response:
                                self.connection.sendall(response.encode())
                            else:
                                self.connection.sendall(f'response: None'.encode())
                        else:
                            break
                    except socket.timeout as e:
                        err = e.args[0]
                        # this next if/else is a bit redundant, but illustrates how the
                        # timeout exception is setup
                        if err == 'timed out':
                            sleep(1)
                            print('recv timed out, retry later')
                            continue
                    except socket.error as e:
                        # Something else happened, handle error, exit, etc.
                        print(e)
                        sys.exit(1)                   
            except Exception as e:
                LOG.error(e)
            finally:
                LOG.debug(f'All data received from {self.client_address}')

    def stop_server(self):
        try:
            self.connection.sendall('shut down successfully'.encode())
            self.connection.close()
        finally:
            LOG.debug('server stopped')    


class Taskmasterd:

    def __init__(self, conf):
        self.conf = conf
        self.conf_backup = conf
        self.programs = deepcopy(conf['programs'])
        self.umask = 0o22
        self.directory = "/"


    def set_signals(self):
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)


    def signal_handler(self, signum, frame):
        if signum == signal.SIGINT or signum == signal.SIGTERM:
            self.cleanup()


    def cleanup(self):
        try:
            self.stop_programs(['all'])
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


    def run(self):

        # Initialize
        self.q = Queue()
        self.server = Server()
        self.set_signals()
        # self.server = Process(target=self.s.serve_forever, args=(self.q, ))
        # self.manager = Process(target=self.manager, args=())

        # Start server and manager
        self.server.serve_forever(self.q)
        # self.manager()

        # On exit
        # self.server.join()
        # self.manager.join()
        self.cleanup()


    def manager(self):
        LOG.debug('starting manager')
        self.init_programs()
        while 1:
            try:
                msg = self.queue.get(timeout=3)
                if msg == 'shutdown':
                    break
                LOG.error('AAAAAAAAAAAAAAAAAAAAAAAA')
                response = self.action(msg)
                self.queue.put(response)
            except:
                # LOG.debug('manager: queue empty, checking program status')
                for k, v in self.programs.items():
                    autorestart = self.programs[k]['autorestart'] 
                    p = self.programs[k]['p']
                    if p is not None:
                        exit_code = p.poll()
                        if exit_code is not None and self.programs[k]['state'] == RUNNING:
                            self.programs[k]['state'] = SYSEXIT
                            self.programs[k]['start_ts'] = None
                            self.programs[k]['pid'] = None
                            LOG.info(f'{k} exited with {exit_code}')
                            if autorestart == 'unexpected':
                                self.restart_programs([k])
        self.stop_programs(['all'])


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
            if self.programs[name]['p'].poll() is None:
                return f'{name} is already running|'
        except:
            cwd = os.getcwd()
            work_dir = self.programs[name]['dir']
            restarts = self.programs[name]['restarts']
            startup_wait = self.programs[name]['startup_wait']
            log_stdout = self.programs[name]['stdout_logfile']
            log_stderr = self.programs[name]['stderr_logfile']

            if isinstance(log_stdout, str):
                stdout = open(log_stdout, 'w+')
            else:
                stdout = DEVNULL
            if isinstance(log_stderr, str):
                stderr = open(log_stderr, 'w+')
            else:
                stderr = DEVNULL

            if work_dir is not None:
                try:
                    os.chdir(work_dir)
                    LOG.debug(f'cd to working dir {work_dir}')
                except IOError as e:
                    LOG.error(e)
                    return f"Can't use working dir {dir} for {name}"

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
            if work_dir is not None:
                try:
                    LOG.debug(f'cd to cwd {cwd}')
                    os.chdir(cwd)
                except IOError as e:
                    LOG.error(e)
                    return f'{e}'           
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
        if isinstance(logs, str):
            p = Popen(
                ['tail', logs],
                stdout=PIPE,
                stderr=PIPE
            )
            try:
                out, err = p.communicate(timeout=5)
            except TimeoutExpired:
                return 'Error calling tail (timeout after 5 seconds)'
            if len(out):
                return out.decode()
            elif len(err):
                return err.decode()
        else:
            return f'No {fd} logfile specified for {name}: output is directed to /dev/null'


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
    print('Server started')
    if not args.nodaemon:
        d.daemonize()
    d.run()


if __name__ == '__main__':
    main()