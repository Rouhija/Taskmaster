import io
import os
import asyncio
import logging
from copy import deepcopy
from subprocess import PIPE, Popen, TimeoutExpired
from time import gmtime, strftime, time, sleep

LOG = logging.getLogger(__name__)

RUNNING = 'RUNNING'
STOPPED = 'STOPPED'
UNKNOWN = 'UNKNOWN'
KILLED = 'EXITED'

class Manager():

    def __init__(self, conf):
        self.conf = conf
        self.conf_backup = conf
        self.programs = deepcopy(conf['programs'])

    async def init_programs(self):
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
            await self.start_programs(startup)

    async def start_programs(self, command):
        response = ''
        if command[0] == 'all':
            command = []
            for k, _ in self.programs.items():
                command.append(k)
        for name in command:
            response += await self.start(name)
        return response

    async def start(self, name):
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

    async def stop_programs(self, command):
        response = ''
        if command[0] == 'all':
            command = []
            for k, _ in self.programs.items():
                command.append(k)
        for name in command:
            response += await self.stop(name)
        return response

    async def stop(self, name):
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

    def check_if_running(self, name):
        if 'p' in self.programs[name]:
            if self.programs[name]['p'] is not None:
                if self.programs[name]['p'].poll() is None:
                    return True
        return False