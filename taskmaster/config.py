import os
import sys
import yaml
import signal
from copy import deepcopy
from subprocess import PIPE
from os.path import dirname, realpath


OPTIONS = [
    'command',
    'autostart',
    'autorestart',
    'stdout_logfile',
    'stderr_logfile',
    'instances',
    'stop_signal',
    'kill_timeout',
    'startup_wait',
    'restarts',
    'expected_exit',
    'environment',
    'dir',
    'umask'
]


class Error(Exception):
    """Base class for exceptions in this module."""
    pass

class ConfigError(Error):

    def __init__(self, message):
        self.message = message

class Config(object):

    """
    Read in .yml config file. Add default values to each process if they are not specified.
    Check that the applied values are coherent
    """

    def __init__(self, path=None, ctl=None):
        try:
            if path is not None:
                with open(path, 'r') as cfg_stream: 
                    self.conf = yaml.load(cfg_stream, Loader=yaml.BaseLoader)
            else:
                self.search()
            if ctl is True:
                self.port = int(self.conf['server']['port'])
            else:
                self.process()
        except (ConfigError, FileNotFoundError, PermissionError, TypeError) as e:
            raise ConfigError(e)

    def search(self):
        search = ['config.yml', 'config.yaml', 'configuration.yml', 'taskmaster/resources/config.yml']
        parent_dir = dirname(dirname(realpath(__file__)))
        for s in search:
            try:
                with open(f'{parent_dir}/{s}', 'r') as cfg_stream: 
                    self.conf = yaml.load(cfg_stream, Loader=yaml.BaseLoader)
                    return
            except:
                pass
        raise ConfigError("Couldn't find configuration file")


    def process(self):
        """
        add default values if not defined, validate options and duplicate instances if specified
        """
        for proc_name, _ in self.conf['programs'].items():

            self.opt_command(proc_name)
            self.opt_bool(proc_name, 'autostart', True, ['true', 'false'])
            self.opt_autorestart(proc_name, 'autorestart', 'always', ['always', 'never', 'unexpected'])
            self.opt_int(proc_name, 'restarts', 3, int)
            self.opt_int(proc_name, 'kill_timeout', 3, int)
            self.opt_int(proc_name, 'startup_wait', 0.1, int)
            self.opt_int(proc_name, 'instances', 1, int)
            self.opt_int(proc_name, 'umask', 0o22, int, base=8)
            self.opt_logfile(proc_name, 'stdout_logfile', PIPE, ['full path to logfile'])
            self.opt_logfile(proc_name, 'stderr_logfile', PIPE, ['full path to logfile'])
            self.opt_signal(proc_name, 'stop_signal', signal.SIGTERM, 'one of [2, 3, 9, 15]')
            self.opt_list(proc_name, 'expected_exit', [0], 'list[int, int, ...]')
            self.opt_dir(proc_name, 'dir', None, ['valid path'])
            self.opt_environment(proc_name, 'environment', None, 'list[key:val, key:val, ...]')

            for k, _ in self.conf['programs'][proc_name].items():
                if k not in OPTIONS:
                    self.invalid_option(proc_name, k)

        self.server()
        self.instances()
        return

    def server(self):
        try:
            self.conf['server']['port'] = int(self.conf['server']['port'])
        except:
            self.invalid_value('server', 'port', int)
            

    def instances(self):
        """
        Make duplicate child processes in case instances > 1
        """
        dup = deepcopy(self.conf['programs'])
        for k, v in dup.items():
            instances = v['instances']
            if instances > 1:
                i = 0
                while i < instances:
                    self.conf['programs'][f'{k}({i})'] = deepcopy(v)
                    i += 1
                del self.conf['programs'][k] 

    def opt_environment(self, name, option, default, needs):
        if option in self.conf['programs'][name]:
            try:
                env = {}
                for var in self.conf['programs'][name][option]:
                    split = var.split(':')
                    if len(split) != 2:
                        raise Error
                    env[split[0]] = split[1]
                self.conf['programs'][name][option] = env
            except:
                self.invalid_value(name, option, needs)
        else:
            self.conf['programs'][name][option] = default

    def opt_autorestart(self, name, option, default, needs):
        if option in self.conf['programs'][name]:
            if self.conf['programs'][name][option] not in needs:
                self.invalid_value(name, option, needs)
        else:
            self.conf['programs'][name][option] = default

    def opt_command(self, proc_name):
        if not 'command' in self.conf['programs'][proc_name]:
            raise ConfigError(f'Missing required option in [{proc_name}]: command')
        try:
            self.conf['programs'][proc_name]['command'] = list(self.conf['programs'][proc_name]['command'])
        except:
            raise ConfigError(f'Option command in [{proc_name}] needs type list')

    def opt_bool(self, name, option, default, needs):
        if option in self.conf['programs'][name]:
            if self.conf['programs'][name][option] not in needs:
                self.invalid_value(name, option, needs)
            elif self.conf['programs'][name][option].lower() == 'true':
               self.conf['programs'][name][option] = True
            elif self.conf['programs'][name][option].lower() == 'false':
               self.conf['programs'][name][option] = False
        else:
            self.conf['programs'][name][option] = default

    def opt_int(self, name, option, default, needs, base=10):
        if option in self.conf['programs'][name]:
            try:
                self.conf['programs'][name][option] = int(self.conf['programs'][name][option], base)
            except:
                self.invalid_value(name, option, needs)
        else:
            self.conf['programs'][name][option] = default

    def opt_logfile(self, name, option, default, needs):
        if option in self.conf['programs'][name]:
            try:
                with open(self.conf['programs'][name][option], 'w+') as f:
                    pass
            except IOError as e:
                self.invalid_value(name, option, needs)    
        else:
            self.conf['programs'][name][option] = default

    def opt_dir(self, name, option, default, needs):
        if option in self.conf['programs'][name]:
            cwd = os.getcwd()
            try:
                os.chdir(self.conf['programs'][name][option])
            except IOError as e:
                self.invalid_value(name, option, needs)
            finally:
                os.chdir(cwd)
        else:
            self.conf['programs'][name][option] = default

    def opt_list(self, name, option, default, needs):
        if option in self.conf['programs'][name]:
            try:
                self.conf['programs'][name][option] = [int(i) for i in self.conf['programs'][name][option]]
            except:
                self.invalid_value(name, option, needs)
        else:
            self.conf['programs'][name][option] = default

    def opt_signal(self, name, option, default, needs):
        map_signals = {
            2: signal.SIGINT,
            3: signal.SIGQUIT,
            9: signal.SIGKILL,
            15: signal.SIGTERM
        }
        if option in self.conf['programs'][name]:
            try:
                self.conf['programs'][name][option] = map_signals[int(self.conf['programs'][name][option])]
            except:
                self.invalid_value(name, option, needs)
        else:
            self.conf['programs'][name][option] = default

    def invalid_value(self, name, opt, needs):
        raise ConfigError(f'Invalid value: program [{name}] in option [{opt}] - needs {needs}')

    def invalid_option(self, name, opt):
        for o in OPTIONS:
            if opt in o:
                suggestion = o
                raise ConfigError(f'Invalid option: program [{name}] in option [{opt}] - did you mean "{suggestion}"?')
                break
        else:
            raise ConfigError(f'Invalid option: program [{name}] in option [{opt}]')
