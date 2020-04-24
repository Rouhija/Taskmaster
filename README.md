# Taskmaster
Job control program, much like [Supervisor](http://supervisord.org/)

## Installation
```sh
virtualenv venv -p python3 && source venv/bin/activate
python3 setup.py develop
```

## Usage

Launch server
```sh
taskmasterd [-c/--configuration FILE] [-n/--nodaemon]
```

Run client in interactive mode
```sh
taskmasterctl
```

## Commands
| CMD | ACTION |
|---------|---------|
| help | Display commands |
| status | Display processes |
| start <name> | Start program |
| stop <name> | Stop program |
| restart <name> | Restart program |
| clear <name> | Clear program log files |
| tail <name> <stdout/stderr> <n> | Read from program logs |
| reread | Reread configuration file |
| update | Apply configuration file changes |
| shutdown | Terminate taskmasterd |
| quit/exit | Exit |

## Dependencies

### To-Do
- [ ] Berrer parser and return curated command
- [ ] Config file from cmd args
- [ ] logs to /var/log/
- [ ] Implement config file options
- [ ] Print response as is in ctl and send line by line

### References
- [Daemons](https://en.wikipedia.org/wiki/Daemon_(computing))
- [DaemonsMore](http://www.cems.uwe.ac.uk/~irjohnso/coursenotes/lrc/system/daemons/d3.htm)
- [Sockets](https://pymotw.com/2/socket/tcp.html)
- [Supervisor](https://www.digitalocean.com/community/tutorials/how-to-install-and-manage-supervisor-on-ubuntu-and-debian-vps)
- [Setup.py](https://amir.rachum.com/blog/2017/07/28/python-entry-points/)
- [Pyformat](https://pyformat.info/)
