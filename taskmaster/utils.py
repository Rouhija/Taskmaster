import pkg_resources

VERSION = pkg_resources.require("taskmaster")[0].version

COMMANDS = [
    'exit',
    'quit',
    'reload',
    'reread',
    'restart',
    'shutdown',
    'start',
    'status',
    'stop',
    'tail',
    'update',
    'version'
]

NEEDS_ARG = [
    'exit',
    'reload',
    'restart',
    'start',
    'stop',
    'tail'
]


def print_help(command):
    if command == 'start' or command == 'stop':
        print(f'usage: {command} <name> | all')


def syntax_tail(command):
    try:
        streams = ['stdout', 'stderr']
        if len(command) != 3:
            return False
        elif command[2].lower() not in streams:
            return False
        return True
    except:
        return False


def syntax(s):
    split = s.split(' ')
    if not split[0] in COMMANDS:
        print(f'command not found: {split[0]}')
        return False
    elif split[0] == 'version':
        print(VERSION)
        return False
    elif len(split) == 1 and split[0] in NEEDS_ARG:
        print_help(split[0])
        return False
    elif split[0] == 'tail':
        if not syntax_tail(split):
            print(f'usage: tail <name> <stdout/stderr>')
            return False
    return True


def parse(command: str):
    try:
        return command.strip().lower()
    except:
        return None