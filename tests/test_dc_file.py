import unittest

from dc.parser import parse_dc_file, parse_dc_files


class TestDCFile(unittest.TestCase):
    def test_parse_otp(self):
        dc = parse_dc_file('otp.dc')

        self.assertEqual(dc.hash, 1788488919)
        self.assertEqual(dc.fields[150]().name, 'removeAvatarResponse')
        self.assertEqual(dc.classes[23].name, 'DistributedPlayer')

        dc = parse_dc_files(('otp.dc', 'toon.dc'))
        self.assertEqual(dc.hash, 1428073344)

        toon = dc.classes[62]

        self.assertEqual(toon.name, 'DistributedToon')
        self.assertEqual(len(dc.classes), 394)
        self.assertEqual(len(toon.fields), 178)
        self.assertEqual(toon.inherited_fields[150].name, 'setDisguisePageFlag')


if __name__ == '__main__':
    unittest.main()
