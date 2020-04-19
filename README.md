# Taskmaster
Job control program, much like [Supervisor](http://supervisord.org/)

## Installation
```sh
virtualenv venv && source venv/bin/activate
python3 setup.py develop
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
- [ ] Communicate to taskmasterd from taskmasterctl over sockets
- [ ] Config file from cmd args

### References
- [Daemons](https://en.wikipedia.org/wiki/Daemon_(computing))
- [DaemonsMore](http://www.cems.uwe.ac.uk/~irjohnso/coursenotes/lrc/system/daemons/d3.htm)
- [Supervisor](https://www.digitalocean.com/community/tutorials/how-to-install-and-manage-supervisor-on-ubuntu-and-debian-vps)
- [Setup.py](https://amir.rachum.com/blog/2017/07/28/python-entry-points/)
