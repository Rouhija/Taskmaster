# Taskmaster
Job control program, much like [Supervisor](http://supervisord.org/)

## Installation
```sh
python3 setup.py develop
```

## Usage
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

### References
- [Setup.py](https://amir.rachum.com/blog/2017/07/28/python-entry-points/)
