import unittest

from dc.parser import parse_dc_file, parse_dc_files, parse_dc
from dc.util import Datagram

SWITCH_TEST = '''
struct BuffData {
  switch (uint16) {
  case 0:
    break;
  case 1:
    uint8 val1;
    break;
  case 2:
    uint8 val1;
    uint8 val2;
    break;
  case 3:
    uint8 val1;
    break;
  case 4:
    int16/100 val1;
    break;
  };
};
'''


class TestDCFile(unittest.TestCase):
    def test_parse_otp(self):
        dc = parse_dc_file('otp.dc')

        self.assertEqual(dc.hash, 1788488919)
        self.assertEqual(dc.fields[150]().name, 'removeAvatarResponse')
        self.assertEqual(dc.classes[23].name, 'DistributedPlayer')

    def test_switch(self):
        dc = parse_dc(SWITCH_TEST)

        self.assertEqual(dc.hash, 56286)

        switch = dc.fields[0]().parameter
        self.assertEqual(len(switch.cases), 5)
        self.assertEqual(switch.default_case, None)
        self.assertEqual(switch.cases[4].value, 4)
        self.assertEqual(switch.cases[0].breaked, True)


if __name__ == '__main__':
    unittest.main()
