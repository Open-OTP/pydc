import unittest

from dc.util import Datagram


class TestDatagramIterator(unittest.TestCase):
    def test_get(self):
        dg = Datagram()
        dg.add_uint16(25)
        dg.add_int64(-354843598374)
        dg.add_string32('datagram iterator test'.encode('utf-8'))

        dgi = dg.iterator()
        self.assertEqual(dgi.get_uint16(), 25)
        self.assertEqual(dgi.get_int64(), -354843598374)
        self.assertEqual(dgi.get_string32(), 'datagram iterator test')

    def test_remaining(self):
        dg = Datagram()
        dg.add_uint16(25)
        dg.add_int64(-354843598374)

        dgi = dg.iterator()
        self.assertEqual(dgi.remaining(), 10)

        s = 'remaining unit test'
        dg.add_string32(s.encode('utf-8'))
        self.assertEqual(dgi.remaining(), 10 + 4 + len(s))

        self.assertEqual(dgi.get_uint16(), 25)
        self.assertEqual(dgi.remaining(), 8 + 4 + len(s))

        dgi.seek(dg.get_length())
        self.assertEqual(dgi.remaining(), 0)

        dgi.seek(0)
        self.assertEqual(dgi.remaining(), 10 + 4 + len(s))

        dgi.seek(14)
        self.assertEqual(dgi.remaining(), len(s))

        dgi.seek(999)
        self.assertEqual(dgi.remaining(), 0)

    def test_get_remaining(self):
        dg = Datagram()
        dg.add_string16(b'test string')
        dg.add_uint32(2525)

        dgi = dg.iterator()
        self.assertEqual(dgi.remaining(), 2 + len('test string') + 4)
        self.assertEqual(dgi.get_remaining(), dg.get_message().tobytes())


if __name__ == '__main__':
    unittest.main()
