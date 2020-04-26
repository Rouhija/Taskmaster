# Taskmaster
UNIX job control program, much like [Supervisor](http://supervisord.org/)

## Installation
```sh
virtualenv venv -p python3 && source venv/bin/activate
pip install -r requirements.txt
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

## Config file options
```yaml
programs:
    program_name:
        command: list[path, arg, ...] - REQUIRED
        autostart: true/false
        autorestart: ['always', 'never', 'unexpected_only']
        stderr_logfile: path
        stdout_logfile: path
        stop_signal: 1, 3, 5, 9 etc
        kill_timeout: int(seconds)
        restarts: int
        expected_exit: [int, int, ...]
        startup_wait: int(seconds)
        environment: [str=str, str=str, ...]
        dir: path
        umask: octal, eg. 022
```

## Commands
| CMD | ACTION |
|---------|---------|
| help | Display commands |
| status | Display processes |
| start <name> | Start program |
| stop <name> | Stop program |
| restart <name> | Restart program |
| tail <name> <stdout/stderr> | Read last 10 entries from program logs |
| reread | Reread configuration file |
| update | Apply configuration file changes |
| shutdown | Terminate taskmasterd |
| quit/exit | Exit |

## Dependencies

### To-Do
- [ ] logs to /var/log/
- [ ] ENVVARS IN CONFIG
- [ ] DO unittests
- [ ] Unexpected exit
- [x] Queue from Server to monitor which controls?
- [ ] Shutdown errors
- [ ] Check start and stop logic

### References
- [Daemons](https://en.wikipedia.org/wiki/Daemon_(computing))
- [DaemonsMore](http://www.cems.uwe.ac.uk/~irjohnso/coursenotes/lrc/system/daemons/d3.htm)
- [Sockets](https://pymotw.com/2/socket/tcp.html)
- [Supervisor](https://www.digitalocean.com/community/tutorials/how-to-install-and-manage-supervisor-on-ubuntu-and-debian-vps)
- [Setup.py](https://amir.rachum.com/blog/2017/07/28/python-entry-points/)
- [Pyformat](https://pyformat.info/)
