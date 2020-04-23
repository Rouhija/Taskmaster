# Taskmaster
Job control program, much like [Supervisor](http://supervisord.org/)

## Installation
```sh
virtualenv venv -p python3 && source venv/bin/activate
python3 setup.py develop
```

## Supervisor 
```
long_script                      RUNNING   pid 32676, uptime 0:00:29
```
clear
```
Error: clear requires a process name
clear <name>            Clear a process' log files.
clear <name> <name>     Clear multiple process' log files
clear all               Clear all process' log files
```

## Usage

Launch
```sh
taskmasterd -c myconfig.yml
```

Reread config and start
```sh
taskmasterctl reread
taskmaster update
```

Interactive mode
```sh
taskmasterctl
```

Follow up commands
```sh
taskmasterctl> help
taskmasterctl> stop <program>
taskmasterctl> restart <program>
taskmasterctl> start <program>
taskmasterctl> quit
```

## Dependencies

### To-Do
- [ ] Check command syntax
- [ ] Execute in daemon
- [ ] Config file from cmd args
- [ ] logs to /var/log/

### References
- [Daemons](https://en.wikipedia.org/wiki/Daemon_(computing))
- [DaemonsMore](http://www.cems.uwe.ac.uk/~irjohnso/coursenotes/lrc/system/daemons/d3.htm)
- [Sockets](https://pymotw.com/2/socket/tcp.html)
- [Supervisor](https://www.digitalocean.com/community/tutorials/how-to-install-and-manage-supervisor-on-ubuntu-and-debian-vps)
- [Setup.py](https://amir.rachum.com/blog/2017/07/28/python-entry-points/)
