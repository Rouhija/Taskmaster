import logging
import unittest
from taskmaster.utils import syntax

LOG = logging.getLogger(__name__)

class UtilTests(unittest.TestCase):

    def setUp(self):
        logging.basicConfig(level='ERROR')

    def test_00(self):
        expected = True
        result = syntax('tail script stdout')
        self.assertEqual(expected, result)

    def test_01(self):
        expected = False
        result = syntax('stop')
        self.assertEqual(expected, result)

    def test_02(self):
        expected = False
        result = syntax('tail stdout script')
        self.assertEqual(expected, result)

    def test_03(self):
        expected = True
        result = syntax('restart name name name')
        self.assertEqual(expected, result)

if __name__ == "__main__":
    unittest.main()