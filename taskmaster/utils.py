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
    # 'start',
    'status',
    'stop',
    # 'tail',
    # 'update',
    'version'
]


def parser(s):
    split = s.split(' ')
    if not split[0] in DEFAULT_CMDS:
        print(f'Command not found: {split[0]}')
        return False
    elif split[0] == 'version':
        print(VERSION)
        return False
    return True