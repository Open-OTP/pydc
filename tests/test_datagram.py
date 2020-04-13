import unittest
import struct
import random


from dc.util import Datagram


def pack_unsigned(n):
    return (n).to_bytes(1, byteorder='little')


class TestDatagram(unittest.TestCase):
    def test_add_uint8(self):
        dg = Datagram()
        other = b''

        dg.add_uint8(12)
        other += pack_unsigned(12)
        self.assertEqual(dg.get_message().tobytes(),  other)

        dg.add_uint8(47)
        other += pack_unsigned(47)
        self.assertEqual(dg.get_message().tobytes(), other)

        dg.add_uint8(255)
        other += pack_unsigned(255)
        self.assertEqual(dg.get_message().tobytes(), other)

        dg.add_uint8(0)
        other += pack_unsigned(0)
        self.assertEqual(dg.get_message().tobytes(), other)

        with self.assertRaises(OverflowError):
            dg.add_uint8(256)
            dg.add_uint8(-3)

    def test_add_int8(self):
        dg = Datagram()
        dg.add_int8(-127)
        dg.add_int8(127)
        other = struct.pack('<bb', -127, 127)

        self.assertEqual(dg.get_message().tobytes(), other)

        with self.assertRaises(OverflowError):
            dg.add_int8(-128)
            dg.add_int8(128)

    def test_add_uint32(self):
        dg = Datagram()
        dg.add_uint32(1 << 31)

        other = struct.pack('<I', 1 << 31)
        self.assertEqual(dg.get_message().tobytes(), other)

        with self.assertRaises(OverflowError):
            dg.add_uint32(1 << 32)

    def test_add_data(self):
        s = 'hello_world'.encode('utf-8')

        dg = Datagram()
        dg.add_string16(s)
        other = struct.pack(f'<H{len(s)}b', len(s), *s)
        self.assertEqual(dg.get_message().tobytes(), other)

        s = 'abcdefghijklmnop'.encode('utf-8')
        dg = Datagram()
        dg.add_string32(s)
        other = struct.pack(f'<I{len(s)}b', len(s), *s)
        self.assertEqual(dg.get_message().tobytes(), other)

        dg.add_bytes(b'')
        self.assertEqual(dg.get_message().tobytes(), other)

        dg = Datagram()

        random.seed('pydc')

        s = bytes(random.randint(0, 255) for _ in range((1 << 16)))

        with self.assertRaises(OverflowError):
            dg.add_string16(s)

        dg = Datagram()
        s = bytes(random.randint(0, 255) for _ in range((1 << 16)))
        dg.add_string32(s)
        s = b''.join((struct.pack('<I', len(s)), s))
        self.assertEqual(dg.get_message().tobytes(), s)

        dg = Datagram()
        dg.add_string32(b'')
        self.assertEqual(dg.get_message().tobytes(), struct.pack('<I', 0))

        dg = Datagram()
        c = chr(0x1F600).encode('utf-8')
        dg.add_bytes(c)
        self.assertEqual(dg.get_message().tobytes(), c)

    def test_add_datagram(self):
        dg1 = Datagram()
        dg1.add_uint16(32)

        dg2 = Datagram()
        dg2.add_string16(b'hello')

        dg1.add_datagram(dg2)

        self.assertEqual(dg1.get_message().tobytes(), struct.pack('<HH5B', 32, 5, *b'hello'))

        del dg2
        self.assertEqual(dg1.get_message().tobytes(), struct.pack('<HH5B', 32, 5, *b'hello'))

    def test_copy_datagram(self):
        dg = Datagram()
        dg.add_string32('testing copy'.encode('utf-8'))

        dg2 = dg.copy()

        self.assertEqual(dg.get_message().tobytes(), dg2.get_message().tobytes())

        dg.add_uint16(65200)

        self.assertNotEqual(dg.get_message().tobytes(), dg2.get_message().tobytes())

        data = dg2.get_message().tobytes()
        del dg
        self.assertEqual(dg2.get_message().tobytes(), data)

    def test_overwrite(self):
        dg = Datagram()
        dg.add_uint32(2828)

        pos = dg.tell()
        self.assertEqual(pos, 4)

        dg.add_uint16(24)
        dg.add_int64(-352793)
        dg.seek(pos)
        dg.add_uint16(5000)
        dg.seek(dg.get_length())
        dg.add_string32(b'overwrite')

        dgi = dg.iterator()
        self.assertEqual(dgi.get_uint32(), 2828)
        self.assertEqual(dgi.get_uint16(), 5000)
        self.assertEqual(dgi.get_int64(), -352793)
        self.assertEqual(dgi.get_string32(), 'overwrite')


if __name__ == '__main__':
    unittest.main()
