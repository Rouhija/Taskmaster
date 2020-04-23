import yaml
from os.path import dirname, realpath

class Config(object):

    def __init__(self, path=None):
        self.path = path
        parent_dir = dirname(dirname(realpath(__file__)))

        if self.path is not None:
            with open(path, 'r') as cfg_stream: 
                self.conf = yaml.load(cfg_stream, Loader=yaml.BaseLoader)
        else:
            with open(f'{parent_dir}/config.yml', 'r') as cfg_stream: 
                self.conf = yaml.load(cfg_stream, Loader=yaml.BaseLoader)
