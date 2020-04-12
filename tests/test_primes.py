import unittest
import numpy


# Old function
def primesfrom2to(n):
    """ Input n>=6, Returns a array of primes, 2 <= p < n """
    sieve = numpy.ones(n // 3 + (n % 6 == 2), dtype=numpy.bool)
    for i in range(1, int(n ** 0.5) // 3 + 1):
        if sieve[i]:
            k = 3 * i + 1 | 1
            sieve[k * k // 3::2 * k] = False
            sieve[k * (k - 2 * (i & 1) + 4) // 3::2 * k] = False
    return numpy.r_[2, 3, ((3 * numpy.nonzero(sieve)[0][1:] + 1) | 1)]


class OldHashGenerator(object):
    MAX_PRIMES = 10000
    MAX_N = 104744
    __slots__ = '_hash', '_index', '_primes'

    def __init__(self):
        self._hash = 0
        self._index = 0
        self._primes = primesfrom2to(OldHashGenerator.MAX_N)

    def add_int(self, n):
        self._hash += self._primes[self._index] * n
        self._index = (self._index + 1) % OldHashGenerator.MAX_PRIMES

    def add_string(self, s):
        self.add_int(len(s))
        if type(s) == str:
            for c in s:
                self.add_int(ord(c))
        elif type(s) == bytes:
            for c in s:
                self.add_int(c)
        else:
            raise Exception('Unhashable value:', s)

    def get_hash(self):
        return self._hash & 0xffffffff


from dc.util import HashGenerator


class TestHashGen(unittest.TestCase):
    def test_hash_gen(self):
        gen1 = HashGenerator()
        gen2 = OldHashGenerator()

        for i in range(5500):
            gen1.add_int(i)
            gen1.add_string('i_%d' % i)

            gen2.add_int(i)
            gen2.add_string('i_%d' % i)

            self.assertEqual(gen1.get_hash(), gen2.get_hash())


if __name__ == '__main__':
    unittest.main()
