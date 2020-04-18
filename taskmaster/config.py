import yaml
from os.path import dirname, realpath

class Config(object):

    def __init__(self):
        parent_dir = dirname(dirname(realpath(__file__)))
        with open(f'{parent_dir}/config.yml', 'r') as cfg_stream: 
            config = yaml.load(cfg_stream, Loader=yaml.BaseLoader)
            self.conf = config
