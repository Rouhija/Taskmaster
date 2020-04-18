#!/usr/bin/python3

"""taskmasterctl -- control applications run by taskmasterd from the cmd line.
Usage: %s [options] [action [arguments]]
Options:
-
-
-
"""

from taskmaster.config import Config

taskmaster_snek = """\
    --..,_                     _,.--.
       `'.'.                .'`__ o  `;__.
          '.'.            .'.'`  '---'`  `
            '.`'--....--'`.'
              `'--....--'`
"""

class Console:

    def __init__(self, options, stdin=None, stdout=None):
        self.options = options


def main():
    print(taskmaster_snek)
    c = Console("lol")
    # if options is None:
    #     options = ClientOptions()

    # options.realize(args, doc=__doc__)
    # c = Controller(options)

    # if options.args:
    #     c.onecmd(" ".join(options.args))
    #     sys.exit(c.exitstatus)

    # if options.interactive:
    #     c.exec_cmdloop(args, options)
    #     sys.exit(0)  # exitstatus always 0 for interactive mode

if __name__ == "__main__":
    main()

if __name__ == '__main__':
    main()