import os
import sys
import tty
import termios
from taskmaster.hist import History


UP = b'\x1b[A'
DOWN = b'\x1b[B'
RIGHT = b'\x1b[C'
LEFT = b'\x1b[D'
ESC = b'\x1b'
BS = b'\x7f'
DEL = b'\x1b[3'
TAB = b'\t'
CTRLC = b'\x03'
CTRLD = b'\x04'


DEFAULT_CMDS = [
    'add',
    'avail',
    'clear',
    'exit',
    'fg',
    'maintail',
    'open',
    'pid',
    'quit',
    'reload'
    'remove',
    'reread',
    'restart',
    'shutdown',
    'signal',
    'start',
    'status',
    'stop',
    'tail',
    'update',
    'version'
]


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

    def read_in(self):
        stdin = ''
        print(self.prompt, end='', flush=True)
        while 1:
            key = self.inkey()

            # Terminating keys
            if key == b'\r' or key == b'\n':
                print()
                break
            elif key == CTRLC or key == CTRLD:
                print()
                return None

            if key == UP or key == DOWN or key == RIGHT or key == LEFT:
                stdin = self.arrows(stdin, key)
            elif key == TAB:
                stdin = self.complete(stdin)
            elif key == BS:
                pass
                # if self.x_pos > 0 and len(stdin):
                #     stdin = self.erase(stdin, self.x_pos - 1)
                #     self.x_pos -= 1
            elif key == DEL:
                pass
                # if self.x_pos < len(stdin):
                #     stdin = self.erase(stdin, self.x_pos)
            else:
                self.x_pos += 1
                stdin += key.decode()

            self.clear()
            print(stdin, end="", flush=True)
            # print(f'  x: {self.x_pos}  in_len: {len(stdin)} input: {stdin}', end="", flush=True)
        self.hist.add(stdin)
        return stdin

    def arrows(self, stdin, key):
        if key == UP:
            stdin = self.hist.get_up() or stdin
        elif key == DOWN:
            stdin = self.hist.get_down() or stdin
        elif key == RIGHT:
            pass
        #     if self.x_pos == len(stdin):
        #         continue
        #     else:
        #         self.x_pos += 1
        #         stdin += key.decode()
        elif key == LEFT:
            pass
        #     if self.x_pos == 0:
        #         continue
        #     else:
        #         self.x_pos -= 1
        #         stdin += key.decode()
        return stdin

    def complete(self, stdin):
        if len(stdin) > 0:
            for c in DEFAULT_CMDS:
                if c.startswith(stdin):
                    stdin = c
                    break
        return stdin

    def clear(self):
        print('\r', end='', flush=True)
        print(self.prompt, end='', flush=True)

    @staticmethod
    def erase(str, n):
        return str[:n] + str[n + 1:]


def main():
    e = Editor()
    while 1:
        ret = e.read_in()
        if ret == None : break
        print(ret)

if __name__ == '__main__':
    main()



