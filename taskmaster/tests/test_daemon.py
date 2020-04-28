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
        logging.basicConfig(level='ERROR')
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
        flag = False
        resp = resp.split('|')
        for line in resp:
            if line and (p in line or p == 'all'):
                if stat in line:
                    flag = True
                else:
                    flag = False
        return flag

    def test_00(self):
        expected = 4
        response = self.d.action('status')
        result = self.parse_response(response)
        self.assertEqual(expected, len(result))

    def test_01(self):
        expected = 'stopped scriptshort successfully|'
        response = self.d.action('stop scriptshort')
        self.assertEqual(expected, response)
        expected = 'scriptshort is already stopped|'
        response = self.d.action('stop scriptshort')
        self.assertEqual(expected, response)

    def test_02(self):
        expected = 'scriptshort restarted successfully|'
        response = self.d.action('restart scriptshort')
        self.assertEqual(expected, response)

    def test_03(self):
        expected = 'Configuration file reread successfully - run `update` to apply changes'
        response = self.d.action('reread')
        self.assertEqual(expected, response)
        expected = 'Update ran successfully'
        response = self.d.action('update')
        self.assertEqual(expected, response)

    def test_04(self):
        expected = True
        p = Popen(['killall', '-9', 'scriptshort.sh'])
        p.wait()
        self.d.manager()
        response = self.d.action('status')
        result = self.prog_status(response, 'scriptshort', 'EXITED')
        self.assertEqual(expected, result)

    def test_05(self):
        expected = True
        p = Popen(['killall', '-15', 'script.sh'])
        p.wait()
        self.d.manager()
        response = self.d.action('status')
        result = self.prog_status(response, 'script', 'EXITED')
        self.assertEqual(expected, result)

    def test_06(self):
        expected = True
        p = Popen(['killall', '-9', 'script.sh'])
        p.wait()
        self.d.manager()
        response = self.d.action('status')
        result = self.prog_status(response, 'script', 'RUNNING')
        self.assertEqual(expected, result)

    def test_07(self):
        expected = 'echoing to stdout'
        response = self.d.action('tail short_echo stdout')
        self.assertEqual(expected, response.strip())
        expected = 'echoing to stderr'
        response = self.d.action('tail short_echo stderr')
        self.assertEqual(expected, response.strip())

    def test_08(self):
        expected = b'error!\n'
        response = self.d.programs['script(0)']['p'].stderr.readline()
        self.assertEqual(expected, response)

    def test_09(self):
        expected = True
        self.d.action('restart all')
        response = self.d.action('status')
        result = self.prog_status(response, 'all', 'RUNNING')
        self.assertEqual(expected, result)


if __name__ == "__main__":
    unittest.main()