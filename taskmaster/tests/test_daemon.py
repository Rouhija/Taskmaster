import os
import sys
import signal
import logging
import unittest
from time import sleep
from subprocess import Popen
from taskmaster.config import Config
from os.path import dirname, realpath
from taskmaster.taskmasterd import Taskmasterd

LOG = logging.getLogger(__name__)

class DaemonTests(unittest.TestCase):

    def setUp(self):
        logging.basicConfig(level='INFO')
        self.c = Config()
        self.d = Taskmasterd(self.c.conf)
        self.d.init_programs()

    def tearDown(self):
        self.d.stop_programs(['all'])
        self.d.sock.close()

    def parse_response(self, resp):
        r = []
        resp = resp.split('|')
        for line in resp:
            if len(line):
                r.append(line)
        return r

    def prog_status(self, resp, p, stat):
        resp = resp.split('|')
        for line in resp:
            if p in line:
                if stat in line:
                    return True
        return False

    def test_00(self):
        excepted = 4
        response = self.d.action('status')
        result = self.parse_response(response)
        self.assertEqual(excepted, len(result))

    def test_01(self):
        excepted = 'stopped scriptshort successfully|'
        response = self.d.action('stop scriptshort')
        self.assertEqual(excepted, response)
        excepted = 'scriptshort is already stopped|'
        response = self.d.action('stop scriptshort')
        self.assertEqual(excepted, response)

    def test_02(self):
        excepted = 'scriptshort restarted successfully|'
        response = self.d.action('restart scriptshort')
        self.assertEqual(excepted, response)

    def test_03(self):
        excepted = 'Configuration file reread successfully - run `update` to apply changes'
        response = self.d.action('reread')
        self.assertEqual(excepted, response)
        excepted = 'Update ran successfully'
        response = self.d.action('update')
        self.assertEqual(excepted, response)

    def test_04(self):
        excepted = True
        p = Popen(['killall', '-9', 'scriptshort.sh'])
        p.wait()
        self.d.manager()
        response = self.d.action('status')
        result = self.prog_status(response, 'scriptshort', 'KILLED')
        self.assertEqual(excepted, result)

    def test_05(self):
        excepted = True
        p = Popen(['killall', '-15', 'script.sh'])
        p.wait()
        self.d.manager()
        response = self.d.action('status')
        result = self.prog_status(response, 'script', 'KILLED')
        self.assertEqual(excepted, result)

    def test_06(self):
        excepted = True
        p = Popen(['killall', '-9', 'script.sh'])
        p.wait()
        self.d.manager()
        response = self.d.action('status')
        result = self.prog_status(response, 'script', 'RUNNING')
        self.assertEqual(excepted, result)


if __name__ == "__main__":
    unittest.main()