import unittest

from dc.objects import AtomicField
from dc.util import Datagram
from dc.parser import parse_dc_file, parse_dc_files, parse_dc


TEST1_DC = '''
dclass A {
    fieldTest1(uint8array);
    fieldTest2(uint8[]);
    fieldTest3(uint32uint8array);
};'''


class TestDCPacker(unittest.TestCase):
    def test_legacy_arrays(self):
        dc = parse_dc(TEST1_DC)
        field = dc.fields[0]()  # type: AtomicField
        field2 = dc.fields[1]()  # type: AtomicField
        field3 = dc.fields[2]()  # type: AtomicField

        arg1 = [2, 4, 8, 16, 32]
        dg = Datagram()
        field.pack_value(dg, [arg1])
        self.assertEqual(field.unpack_value(dg.iterator())[0], [2, 4, 8, 16, 32])

        dg2 = Datagram()
        field2.pack_value(dg2, [arg1])
        self.assertEqual(field2.unpack_value(dg2.iterator())[0], [2, 4, 8, 16, 32])

        self.assertEqual(dg.get_message().tobytes(), dg2.get_message().tobytes())

        arg1 = [[1, 2], [3, 4], [5, 6]]
        dg3 = Datagram()
        field3.pack_value(dg3, [arg1])
        self.assertEqual(dg3.get_message().tobytes(),
                         b'\x0f\x00\x01\x00\x00\x00\x02\x03\x00\x00\x00\x04\x05\x00\x00\x00\x06')

        self.assertEqual(field3.unpack_value(dg3.iterator())[0], [[1, 2], [3, 4], [5, 6]])


if __name__ == '__main__':
    unittest.main()
