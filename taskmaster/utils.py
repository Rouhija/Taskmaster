import pkg_resources

VERSION = pkg_resources.require("taskmaster")[0].version

DEFAULT_CMDS = [
    # 'add',
    # 'avail',
    # 'clear',
    'exit',
    # 'fg',
    # 'maintail',
    # 'open',
    # 'pid',
    'quit',
    'reload',
    # 'remove',
    # 'reread',
    # 'restart',
    # 'shutdown',
    # 'signal',
    'start',
    'status',
    'stop',
    # 'tail',
    # 'update',
    'version'
]

ARG_CMDS = [
    # 'add',
    # 'avail',
    # 'clear',
    'exit',
    # 'fg',
    # 'maintail',
    # 'open',
    # 'pid',
    'reload',
    # 'remove',
    # 'reread',
    # 'restart',
    # 'shutdown',
    # 'signal',
    'start',
    'stop',
    # 'tail',
    # 'update'
]


def print_help(command):
    if command == 'start' or command == 'stop':
        print(f'usage: {command} <name> | all')


def parser(s):
    split = s.split(' ')
    if not split[0] in DEFAULT_CMDS:
        print(f'Command not found: {split[0]}')
        return False
    elif split[0] == 'version':
        print(VERSION)
        return False
    elif len(split) == 1 and split[0] in ARG_CMDS:
        print_help(split[0])
        return False
    return True