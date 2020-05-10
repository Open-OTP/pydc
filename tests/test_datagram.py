import unittest
import struct
import random
import array
import os


from dc.util import Datagram


def pack_unsigned(n):
    return (n).to_bytes(1, byteorder='little')


class TestDatagram(unittest.TestCase):
    def test_add_uint8(self):
        dg = Datagram()
        other = b''

        dg.add_uint8(12)
        other += pack_unsigned(12)
        self.assertEqual(dg.bytes(),  other)

        dg.add_uint8(47)
        other += pack_unsigned(47)
        self.assertEqual(dg.bytes(), other)

        dg.add_uint8(255)
        other += pack_unsigned(255)
        self.assertEqual(dg.bytes(), other)

        dg.add_uint8(0)
        other += pack_unsigned(0)
        self.assertEqual(dg.bytes(), other)

        with self.assertRaises(OverflowError):
            dg.add_uint8(256)
            dg.add_uint8(-3)

    def test_add_int8(self):
        dg = Datagram()
        dg.add_int8(-127)
        dg.add_int8(127)
        other = struct.pack('<bb', -127, 127)

        self.assertEqual(dg.bytes(), other)

        with self.assertRaises(OverflowError):
            dg.add_int8(-128)
            dg.add_int8(128)

    def test_add_uint32(self):
        dg = Datagram()
        dg.add_uint32(1 << 31)

        other = struct.pack('<I', 1 << 31)
        self.assertEqual(dg.bytes(), other)

        with self.assertRaises(OverflowError):
            dg.add_uint32(1 << 32)

    def test_add_data(self):
        s = 'hello_world'.encode('utf-8')

        dg = Datagram()
        dg.add_string16(s)
        other = struct.pack(f'<H{len(s)}b', len(s), *s)
        self.assertEqual(dg.bytes(), other)

        s = 'abcdefghijklmnop'.encode('utf-8')
        dg = Datagram()
        dg.add_string32(s)
        other = struct.pack(f'<I{len(s)}b', len(s), *s)
        self.assertEqual(dg.bytes(), other)

        dg.add_bytes(b'')
        self.assertEqual(dg.bytes(), other)

        dg = Datagram()
        dg.add_string16(b'')
        self.assertEqual(dg.bytes(), b'\x00\x00')

        dg = Datagram()

        random.seed('pydc')

        s = bytes(random.randint(0, 255) for _ in range((1 << 16)))

        with self.assertRaises(OverflowError):
            dg.add_string16(s)

        dg = Datagram()
        s = bytes(random.randint(0, 255) for _ in range((1 << 16)))
        dg.add_string32(s)
        s = b''.join((struct.pack('<I', len(s)), s))
        self.assertEqual(dg.bytes(), s)

        dg = Datagram()
        dg.add_string32(b'')
        self.assertEqual(dg.bytes(), struct.pack('<I', 0))

        dg = Datagram()
        c = chr(0x1F600).encode('utf-8')
        dg.add_bytes(c)
        self.assertEqual(dg.bytes(), c)

    def test_add_datagram(self):
        dg1 = Datagram()
        dg1.add_uint16(32)

        dg2 = Datagram()
        dg2.add_string16(b'hello')

        dg1.add_datagram(dg2)

        self.assertEqual(dg1.bytes(), struct.pack('<HH5B', 32, 5, *b'hello'))

        del dg2
        self.assertEqual(dg1.bytes(), struct.pack('<HH5B', 32, 5, *b'hello'))

    def test_copy_datagram(self):
        dg = Datagram()
        dg.add_string32('testing copy'.encode('utf-8'))

        dg2 = dg.copy()

        self.assertEqual(dg.bytes(), dg2.bytes())

        dg.add_uint16(65200)

        self.assertNotEqual(dg.bytes(), dg2.bytes())

        data = dg2.bytes()
        del dg
        self.assertEqual(dg2.bytes(), data)

    def test_overwrite(self):
        dg = Datagram()
        dg.add_uint32(2828)

        pos = dg.tell()
        self.assertEqual(pos, 4)

        dg.add_uint16(24)
        dg.add_int64(-352793)
        dg.seek(pos)
        dg.add_uint16(5000)
        dg.seek(len(dg))
        dg.add_string32(b'overwrite')

        dgi = dg.iterator()
        self.assertEqual(dgi.get_uint32(), 2828)
        self.assertEqual(dgi.get_uint16(), 5000)
        self.assertEqual(dgi.get_int64(), -352793)
        self.assertEqual(dgi.get_string32(), 'overwrite')

    def test_server_header(self):
        dg = Datagram()
        targets = [4200, 2878, 300, 1]
        dg.add_server_header(targets, 10000000, 1)
        dgi = dg.iterator()
        self.assertEqual(dgi.get_uint8(), 4)
        self.assertEqual(dgi.get_channel(), 4200)
        self.assertEqual(dgi.get_channel(), 2878)
        self.assertEqual(dgi.get_channel(), 300)
        self.assertEqual(dgi.get_channel(), 1)
        self.assertEqual(dgi.get_channel(), 10000000)
        self.assertEqual(dgi.get_uint16(), 1)

    def test_initialization(self):
        dg = Datagram(b'\x01\x02\x03')
        self.assertEqual(dg.bytes(), b'\x01\x02\x03')

        random.seed('test_initialization')
        data = os.urandom(32)
        dg = Datagram(data)
        self.assertEqual(dg.bytes(), data)


if __name__ == '__main__':
    unittest.main()
