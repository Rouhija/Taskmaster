import os
import readline
from taskmaster.utils import COMMANDS


def autocomplete(text, state):
    options = [i for i in COMMANDS if i.startswith(text)]
    if state < len(options):
        return options[state]
    else:
        return None


class Editor:
    def __init__(self):
        readline.parse_and_bind("tab: complete")
        readline.set_completer(autocomplete)
        self.prompt = 'taskmasterctl> '

    def user_input(self):
        try:
            stdin = input(self.prompt)
            return stdin
        except KeyboardInterrupt:
            return None


def main():
    e = Editor()
    while 1:
        ret = e.user_input()
        if ret == None : break
        print(ret)

if __name__ == '__main__':
    main()



