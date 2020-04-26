import os
import sys
import tty
import termios
from taskmaster.hist import History
from taskmaster.utils import COMMANDS

class _Getch:

    def __call__(self):
        fd = sys.stdin.fileno()
        restore = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = os.read(fd, 3)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, restore)
        return ch


class Editor:

    def __init__(self):
        self.prompt = 'taskmasterctl> '
        self.inkey = _Getch()
        self.hist = History()
        self.x_pos = 0
        self.correction = 0

    def read_in(self):
        stdin = ''
        print(self.prompt, end='', flush=True)
        while 1:
            key = self.inkey()
            if key in self.fterm:
                self.x_pos = 0
                self.correction = 0
                return self.fterm[key](self, stdin)
            elif key in self.fmap:
                stdin = self.fmap[key](self, stdin, key)
            else:
                self.x_pos += 1
                stdin += key.decode()
            self.clear()
            print(stdin, end="", flush=True)
            print(f'  x: {self.x_pos}  in_len: {len(stdin) - self.correction} input: {stdin}', end="", flush=True)
        self.x_pos = 0
        self.correction = 0
        self.hist.add(stdin)
        return stdin

    def arrow_up(self, stdin, key):
        line = self.hist.get_up()
        if line is not None:
            self.x_pos = len(line)
            self.correction = 0
            return line
        else:
            return stdin

    def arrow_down(self, stdin, key):
        line = self.hist.get_down()
        if line is not None:
            self.x_pos = len(line)
            self.correction = 0
            return line
        else:
            return stdin

    def arrow_right(self, stdin, key):
        if self.x_pos < len(stdin) - self.correction:
            self.x_pos += 1
            stdin += key.decode()
            self.correction += 3
        return stdin

    def arrow_left(self, stdin, key):
        if self.x_pos:
            self.x_pos -= 1
            stdin += key.decode()
            self.correction += 3
        return stdin

    def complete(self, stdin, key):
        if len(stdin) - self.correction > 0:
            for c in COMMANDS:
                if c.startswith(stdin):
                    stdin = c
                    self.x_pos = len(stdin)
                    self.correction = 0
                    break
        return stdin

    def backspace(self, stdin, key):
        if self.x_pos > 0 and len(stdin) - self.correction > 0:
            stdin = self.erase(stdin, self.x_pos - 1)
            self.x_pos -= 1
        return stdin

    def delete(self, stdin, key):
        if self.x_pos < len(stdin) - self.correction:
            stdin = self.erase(stdin, self.x_pos)
        return stdin

    def linebreak(self, stdin):
        print()
        self.hist.add(stdin)
        return stdin

    def terminate(self, stdin):
        print()
        return None

    def clear(self):
        print('\r', end='', flush=True)
        sys.stdout.write("\033[K")
        sys.stdout.flush()
        print(self.prompt, end='', flush=True)

    @staticmethod
    def erase(str, n):
        return str[:n] + str[n + 1:]

    fmap = {
        b'\x1b[A': arrow_up,
        b'\x1b[B': arrow_down,
        b'\x1b[C': arrow_right,
        b'\x1b[D': arrow_left,
        b'\t': complete,
        b'\x7f': backspace,
        b'\x1b[3': delete
    }

    fterm = {
        b'\r': linebreak,
        b'\n': linebreak,
        b'\x03': terminate,
        b'\x04': terminate
    }


def main():
    e = Editor()
    while 1:
        ret = e.read_in()
        if ret == None : break
        print(ret)

if __name__ == '__main__':
    main()



