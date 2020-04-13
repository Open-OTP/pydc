# cython: language_level=3
from libc.stdlib cimport realloc, malloc, free
from libc.string cimport memcpy
import numpy as np


cdef class Datagram:
    cdef unsigned char* buffer
    cdef unsigned int length
    cdef unsigned int offset
    cdef unsigned int buffer_size

    def __cinit__(self):
        self.length = 0
        self.offset = 0
        self.buffer_size = 64
        self.buffer = <unsigned char *>malloc(self.buffer_size)

    cdef void check_resize(self, const unsigned int min_size):
        if self.buffer_size >= min_size:
            return

        while self.buffer_size < min_size:
            self.buffer_size *= 2

        self.buffer = <unsigned char *>realloc(self.buffer, self.buffer_size)

    cdef inline void append_data(self, const void* value, const unsigned int value_size):
        cdef unsigned int new_size = max(self.offset + value_size, self.length)
        self.check_resize(new_size)
        if self.buffer is NULL:
            return
        memcpy(&self.buffer[self.offset], value, value_size)
        self.length = new_size
        self.offset += value_size

    def add_int8(self, const char value):
        self.append_data(&value, sizeof(value))
        if self.buffer is NULL:
            raise MemoryError('could not allocate memory for datagram')

    def add_uint8(self, const unsigned char value):
        self.append_data(&value, sizeof(value))
        if self.buffer is NULL:
            raise MemoryError('could not allocate memory for datagram')

    def add_int16(self, const short value):
        self.append_data(&value, sizeof(value))
        if self.buffer is NULL:
            raise MemoryError('could not allocate memory for datagram')

    def add_uint16(self, const unsigned short value):
        self.append_data(&value, sizeof(value))
        if self.buffer is NULL:
            raise MemoryError('could not allocate memory for datagram')

    def add_int32(self, const int value):
        self.append_data(&value, sizeof(value))
        if self.buffer is NULL:
            raise MemoryError('could not allocate memory for datagram')

    def add_uint32(self, const unsigned int value):
        self.append_data(&value, sizeof(value))
        if self.buffer is NULL:
            raise MemoryError('could not allocate memory for datagram')

    def add_int64(self, const long long value):
        self.append_data(&value, sizeof(value))
        if self.buffer is NULL:
            raise MemoryError('could not allocate memory for datagram')

    def add_uint64(self, const unsigned long long value):
        self.append_data(&value, sizeof(value))
        if self.buffer is NULL:
            raise MemoryError('could not allocate memory for datagram')

    def add_channel(self, value):
        self.add_uint64(value)

    def add_bytes(self, const unsigned char[:] data):
        if data.size:
            self.append_data(&data[0], data.size)
        if self.buffer is NULL:
            raise MemoryError('could not allocate memory for datagram')

    def add_string16(self, const unsigned char[:] data):
        cdef unsigned short string_length = data.size
        self.append_data(&string_length, sizeof(string_length))
        if string_length:
            self.append_data(&data[0], string_length)
        if self.buffer is NULL:
            raise MemoryError('could not allocate memory for datagram')

    def add_string32(self, const unsigned char[:] data):
        cdef unsigned int string_length = data.size
        self.append_data(&string_length, sizeof(string_length))
        if string_length:
            self.append_data(&data[0], string_length)
        if self.buffer is NULL:
            raise MemoryError('could not allocate memory for datagram')

    def add_float32(self, float value):
        self.append_data(&value, sizeof(value))
        if self.buffer is NULL:
            raise MemoryError('could not allocate memory for datagram')

    def add_float64(self, double value):
        self.append_data(&value, sizeof(value))
        if self.buffer is NULL:
            raise MemoryError('could not allocate memory for datagram')

    def add_datagram(self, Datagram dg):
        self.append_data(&dg.buffer[0], dg.length)

    def get_message(self):
        cdef unsigned char[::1] memview = <unsigned char[:self.length:1]>self.buffer
        output = np.asarray(memview)
        return output

    def get_length(self):
        return self.length

    def __dealloc__(self):
        if self.buffer is not NULL:
            free(self.buffer)
            self.buffer = NULL

    def iterator(self):
        if self.buffer is NULL:
            raise MemoryError('tried to make iterator of invalid datagram')
        cdef DatagramIterator dgi = DatagramIterator()
        dgi.set_dg(<void *>self)
        return dgi

    def copy(self):
        if self.buffer is NULL:
            raise MemoryError('tried to make copy of invalid datagram')
        cdef Datagram copy_dg = Datagram()
        copy_dg.check_resize(self.length)
        memcpy(&copy_dg.buffer[0], &self.buffer[0], self.length)
        copy_dg.length = self.length
        return copy_dg

    def seek(self, unsigned int n):
        if n < 0 or n > self.length:
            raise OverflowError('invalid pos in Datagram')
        self.offset = n

    def tell(self):
        return self.offset

cdef class DatagramIterator:
    cdef Datagram dg
    cdef unsigned int offset

    def __cinit__(self):
        self.offset = 0

    cdef set_dg(self, void* ptr):
        self.dg = <Datagram> ptr

    cdef inline void get_data(self, void* value, const unsigned short num_bytes):
        cdef const unsigned char* buffer = self.dg.buffer
        memcpy(value, &buffer[self.offset], num_bytes)
        self.offset += num_bytes

    def get_int8(self):
        if self.offset + sizeof(char) > self.dg.length:
            raise OverflowError('tried reading past datagram')

        cdef char value
        self.get_data(&value, sizeof(value))
        return value

    def get_uint8(self):
        if self.offset + sizeof(unsigned char) > self.dg.length:
            raise OverflowError('tried reading past datagram')
        cdef unsigned char value
        self.get_data(&value, sizeof(value))
        return value

    def get_int16(self):
        if self.offset + sizeof(short) > self.dg.length:
            raise OverflowError('tried reading past datagram')
        cdef short value
        self.get_data(&value, sizeof(value))
        return value

    def get_uint16(self):
        if self.offset + sizeof(unsigned short) > self.dg.length:
            raise OverflowError('tried reading past datagram')
        cdef unsigned short value
        self.get_data(&value, sizeof(value))
        return value

    def get_int32(self):
        if self.offset + sizeof(int) > self.dg.length:
            raise OverflowError('tried reading past datagram')
        cdef int value
        self.get_data(&value, sizeof(value))
        return value

    def get_uint32(self):
        if self.offset + sizeof(unsigned int) > self.dg.length:
            raise OverflowError('tried reading past datagram')
        cdef unsigned int value
        self.get_data(&value, sizeof(value))
        return value

    def get_int64(self):
        if self.offset + sizeof(long long) > self.dg.length:
            raise OverflowError('tried reading past datagram')
        cdef long value
        self.get_data(&value, sizeof(value))
        return value

    def get_uint64(self):
        if self.offset + sizeof(unsigned long long) > self.dg.length:
            raise OverflowError('tried reading past datagram')
        cdef unsigned long value
        self.get_data(&value, sizeof(value))
        return value

    def get_float32(self):
        if self.offset + sizeof(float) > self.dg.length:
            raise OverflowError('tried reading past datagram')
        cdef float value
        self.get_data(&value, sizeof(value))
        return value

    def get_float64(self):
        if self.offset + sizeof(double) > self.dg.length:
            raise OverflowError('tried reading past datagram')
        cdef double value
        self.get_data(&value, sizeof(value))
        return value

    def get_bytes(self, unsigned int num_bytes):
        if self.offset + num_bytes > self.dg.length:
            raise OverflowError('tried reading past datagram')

        cdef bytearray value = bytearray(num_bytes)
        self.get_data(<unsigned char *>value, num_bytes)

        return value

    def get_string16(self):
        cdef unsigned short num_bytes = self.get_uint16()

        if self.offset + num_bytes > self.dg.length:
            raise OverflowError('tried reading past datagram')

        cdef bytearray value = bytearray(num_bytes)
        self.get_data(<unsigned char *>value, num_bytes)

        return value.decode('utf-8')

    def get_string32(self):
        cdef unsigned int num_bytes = self.get_uint32()
        if self.offset + num_bytes > self.dg.length:
            raise OverflowError('tried reading past datagram: string length is %d' % num_bytes)

        cdef bytearray value = bytearray(num_bytes)
        self.get_data(<unsigned char *>value, num_bytes)

        return value.decode('utf-8')

    def seek(self, int n):
        self.offset = min(n, self.dg.length)

    def skip(self, unsigned int n):
        self.offset += n
        self.offset = min(self.dg.length, self.offset)

    def remaining(self):
        cdef int remaining = self.dg.length - self.offset
        if remaining < 0:
            return 0

        return remaining

    def tell(self):
        return self.offset

    def get_channel(self):
        return self.get_int64()


cdef extern from 'primes.h':
    unsigned int initialize_primes(unsigned int);
    void free_primes();
    unsigned int get_prime(int);


cdef int MAX_PRIME = 104742
cdef int PRIME_COUNT = initialize_primes(MAX_PRIME)

cdef class HashGenerator:
    cdef long hash
    cdef int index

    def __cinit__(self):
        self.hash = 0
        self.index = 0

    def add_int(self, int n):
        self.hash += get_prime(self.index) * n
        self.index = (self.index + 1) % PRIME_COUNT

    def add_bytes(self, const unsigned char[:] data):
        self.add_int(data.size)

        cdef unsigned int i
        for i in range(data.size):
            self.add_int(data[i])

    def add_string(self, s):
        return self.add_bytes(s.encode('utf-8'))

    def get_hash(self):
        return self.hash & 0xffffffff

    @staticmethod
    def get_prime_count():
        return PRIME_COUNT
