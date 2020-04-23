import sys
import tty
import termios
import os


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
        self.x_pos = 0
        self.clear_n = 0
        self.inkey = _Getch()

    def read_in(self):
        stdin = ''
        print(self.prompt, end='', flush=True)
        while 1:
            key = self.inkey()
            # self.clear_n = len(stdin)
            if key == b'\r' or key == b'\n':
                print()
                break
            elif key == CTRLC or key == CTRLD:
                print()
                return None
            if key == UP:
                continue
            elif key == DOWN:
                continue
            elif key == RIGHT:
                if self.x_pos == len(stdin):
                    continue
                else:
                    # print(key.decode(), end="", flush=True)
                    self.x_pos += 1
            elif key == LEFT:
                if self.x_pos == 0:
                    continue
                else:
                    # print(key.decode(), end="", flush=True)
                    self.x_pos -= 1
            elif key == TAB:
                if len(stdin) > 0:
                    for c in DEFAULT_CMDS:
                        if c.startswith(stdin):
                            stdin = c
                            break
            elif key == BS:
                if self.x_pos > 0 and len(stdin):
                    stdin = self.erase(stdin, self.x_pos - 1)
                    self.x_pos -= 1
            elif key == DEL:
                if self.x_pos < len(stdin):
                    stdin = self.erase(stdin, self.x_pos)
            else:
                self.x_pos += 1
                stdin += key.decode()
            self.clear(self.clear_n)
            print(stdin, end="", flush=True)
            # print(f'  x: {self.x_pos}  in_len: {len(stdin)} input: {stdin}', end="", flush=True)
        return stdin


    def clear(self, n):
        print('\r', end='', flush=True)
        print(self.prompt, end='', flush=True)


    def erase(self, str, n):
        return str[:n] + str[n + 1:]


def main():
    e = Editor()
    while 1:
        ret = e.read_in()
        if ret == None : break
        print(ret)

if __name__ == '__main__':
    main()



