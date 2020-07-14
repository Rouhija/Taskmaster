import logging
import argparse
import pkg_resources
from os.path import dirname, realpath

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


def arg_parserctl():
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--debug", help="log to console", action="store_true")
    return parser.parse_args()


def arg_parserd():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--configuration", help="The path to a taskmasterd configuration file")
    parser.add_argument("-n", "--nodaemon", help="Run taskmasterd in the foreground", action="store_true")
    return parser.parse_args()


def loggerd_options(nodaemon):
    if nodaemon:
        logging.basicConfig(
            level=logging.DEBUG,
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