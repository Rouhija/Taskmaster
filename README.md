# Description
UNIX job control program, much like [Supervisor](http://supervisord.org/). Consists of two programs, taskmasterd is a server daemon which does the actual job control work. Taskmasterctl is an interactive UI for communicating with the daemon.

### Installation
```sh
virtualenv venv -p python3 && source venv/bin/activate
pip install -r requirements.txt
python3 setup.py develop
```

### Usage

Launch server
```sh
taskmasterd [-c/--configuration FILE] [-n/--nodaemon]
```

Run client in interactive mode
```sh
taskmasterctl
```

Run tests
```sh
python setup.py test
```

### Configuration
```yaml
programs:
    program_name:
        command: list[bin, arg, arg, ...] - REQUIRED
        autostart: true/false
        autorestart: ['always', 'never', 'unexpected']
        stderr_logfile: path
        stdout_logfile: path
        instances: int
        stop_signal: 1, 3, 5, 9 etc.
        kill_timeout: int(seconds)
        restarts: int
        expected_exit: [int, int, ...]
        startup_wait: int(seconds)
        environment: [key:val, key:val, ...]
        dir: path
        umask: octal, eg. 0o22
server:
    port: eg. 9999 - REQUIRED
```

### Commands
| CMD | ACTION |
|---------|---------|
| **help** | Display help |
| **status** | Display processes |
| **start** *name/all* | Start program |
| **stop** *name/all* | Stop program |
| **restart** *name/all* | Restart program |
| **tail** *name stdout/stderr* | Read last 10 entries from program logs |
| **attach** *name stdout/stderr* | Attach fd of a program to console |
| **reread** | Reread configuration file |
| **update** | Apply configuration file changes |
| **reload** | run reread + update |
| **shutdown** | Terminate taskmasterd |
| **quit**/**exit** | Exit |

### Dependencies
- PyYAML==5.1
