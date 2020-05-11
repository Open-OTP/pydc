from enum import IntEnum
import struct
import math

from dataclasses import dataclass
from dataslots import with_slots
from typing import List

from weakref import ref, WeakValueDictionary, proxy

from dc.util import Datagram, DatagramIterator
from dc.messagetypes import *
from dc.error import DCParseError

import collections.abc


import functools
import operator


class DCTypes(IntEnum):
    int8 = 0
    int16 = 1
    int32 = 2
    int64 = 3
    uint8 = 4
    uint16 = 5
    uint32 = 6
    uint64 = 7
    float64 = 8
    string = 9
    blob = 10
    blob32 = 11
    int16array = 12
    int32array = 13
    uint16array = 14
    uint32array = 15
    int8array = 16
    uint8array = 17
    uint32uint8array = 18
    char = 19
    invalid = 20


pack_functions = {
    DCTypes.int8: Datagram.add_int8,
    DCTypes.int16: Datagram.add_int16,
    DCTypes.int32: Datagram.add_int32,
    DCTypes.int64: Datagram.add_int64,
    DCTypes.uint8: Datagram.add_uint8,
    DCTypes.uint16: Datagram.add_uint16,
    DCTypes.uint32: Datagram.add_uint32,
    DCTypes.uint64: Datagram.add_uint64,
    DCTypes.float64: Datagram.add_float64,
    DCTypes.string: Datagram.add_string16,
    DCTypes.blob: Datagram.add_bytes,
    DCTypes.blob32: Datagram.add_string32,
    DCTypes.char: Datagram.add_uint8,

    # For individual array elements.
    DCTypes.int8array: Datagram.add_int8,
    DCTypes.uint8array: Datagram.add_uint8,
    DCTypes.int16array: Datagram.add_int16,
    DCTypes.uint16array: Datagram.add_uint16,
    DCTypes.int32array: Datagram.add_int32,
    DCTypes.uint32array: Datagram.add_uint32,
}


unpack_functions = {
    DCTypes.int8: DatagramIterator.get_int8,
    DCTypes.int16: DatagramIterator.get_int16,
    DCTypes.int32: DatagramIterator.get_int32,
    DCTypes.int64: DatagramIterator.get_int64,
    DCTypes.uint8: DatagramIterator.get_uint8,
    DCTypes.uint16: DatagramIterator.get_uint16,
    DCTypes.uint32: DatagramIterator.get_uint32,
    DCTypes.uint64: DatagramIterator.get_uint64,
    DCTypes.float64: DatagramIterator.get_float64,
    DCTypes.string: DatagramIterator.get_string16,
    DCTypes.blob: DatagramIterator.get_bytes,
    DCTypes.blob32: DatagramIterator.get_string32,
    DCTypes.char: DatagramIterator.get_uint8,
}

fixed_byte_sizes = {
    DCTypes.int8: 1,
    DCTypes.int16: 2,
    DCTypes.int32: 4,
    DCTypes.int64: 8,
    DCTypes.uint8: 1,
    DCTypes.uint16: 2,
    DCTypes.uint32: 4,
    DCTypes.uint64: 8,
    DCTypes.float64: 8,
    DCTypes.char: 1,
}


class HistoricKeywords(IntEnum):
    required = 0x0001
    broadcast = 0x0002
    ownrecv = 0x0004
    ram = 0x0008
    db = 0x0010
    clsend = 0x0020
    clrecv = 0x0040
    ownsend = 0x0080
    airecv = 0x0100

    @staticmethod
    def has_keyword(kw):
        try:
            HistoricKeywords[kw]
        except KeyError:
            return False
        else:
            return True


@with_slots
@dataclass
class IRange:
    min_n: int
    max_n: int


@with_slots
@dataclass
class FRange:
    min_n: float
    max_n: float


class DCPackable(object):
    __slots__ = '__weakref__'

    def pack_default(self, dg):
        raise NotImplementedError

    def pack_value(self, dg, value):
        raise NotImplementedError

    def unpack_value(self, dgi):
        raise NotImplementedError

    def unpack_bytes(self, dgi):
        raise NotImplementedError

    def generate_hash(self, hash_gen):
        raise NotImplementedError


class Parameter(DCPackable):
    __slots__ = 'dtype', 'identifier', 'default'

    def __init__(self, dtype, identifier, default):
        self.dtype = dtype
        self.identifier = identifier
        self.default = default

    def pack_default(self, dg):
        if self.default is None:
            raise DCParseError('tried packing default for parameter without default')
        return self.pack_value(dg, self.default)

    def generate_hash(self, hash_gen):
        raise NotImplementedError


class SimpleParameter(Parameter):
    __slots__ = 'vrange', 'modulus', 'divisor', 'fixed_byte_size'

    def __init__(self, dtype, vrange=None, modulus=None, divisor=1, identifier=None, default=None):
        Parameter.__init__(self, dtype, identifier, default)
        self.vrange = vrange
        self.modulus = modulus
        self.divisor = divisor

        try:
            fixed_byte_size = fixed_byte_sizes[DCTypes[self.dtype]]
        except KeyError:
            fixed_byte_size = None

        if fixed_byte_size is None and len(vrange) == 1:
            r = vrange[0]
            fixed_byte_size = r.min_n if r.min_n == r.max_n else None

        self.fixed_byte_size = fixed_byte_size

    def generate_hash(self, hash_gen):
        try:
            hash_gen.add_int(DCTypes[self.dtype])
        except KeyError:
            hash_gen.add_int(DCTypes.invalid)

        hash_gen.add_int(self.divisor)

        if self.modulus is not None:
            hash_gen.add_int(int(self.divisor * self.modulus))

        if self.vrange is not None and len(self.vrange):
            hash_gen.add_int(len(self.vrange))

            for vrange in self.vrange:
                hash_gen.add_int(math.floor(vrange.min_n * self.divisor))
                hash_gen.add_int(math.floor(vrange.max_n * self.divisor))

    def __str__(self):
        return '{}({} {} {}={} divisor={} modulus={})'.format(self.__class__.__name__, self.dtype, self.vrange,
                                                              self.identifier, self.default, self.divisor, self.modulus)

    def validate_value(self, value):
        return True

    def pack_value(self, dg, value):
        if not self.validate_value(value):
            raise DCParseError
        # TODO: remove this hacky sack
        if self.dtype == 'uint32uint8array':
            return struct.pack('<IB', *value)

        # TODO: remove this hacky sack
        if type(value) == str:
            value = value.encode()

        pack_functions[DCTypes[self.dtype]](dg, value)

    def unpack_value(self, dgi):
        return unpack_functions[DCTypes[self.dtype]](dgi)

    def unpack_bytes(self, dgi):
        return dgi.get_bytes(self.fixed_byte_size)


class IntParameter(SimpleParameter):
    def validate_value(self, v):
        if v is None:
            return True

        if self.dtype[0] == 'u':
            return v >= 0 and not v >> int(self.dtype[4:])
        else:
            return not abs(v) >> int(self.dtype[3:]) - 1

    def pack_value(self, dg, value):
        if type(value) == float:
            value = int(value * self.divisor)
            SimpleParameter.pack_value(self, dg, value)
        else:
            SimpleParameter.pack_value(self, dg, value)


class FloatParameter(SimpleParameter):
    def generate_hash(self, hash_gen):
        try:
            hash_gen.add_int(DCTypes[self.dtype])
        except KeyError:
            hash_gen.add_int(DCTypes.invalid)

        hash_gen.add_int(self.divisor)

        if self.modulus is not None:
            hash_gen.add_int(int(self.divisor * self.modulus))

        if self.vrange is not None and len(self.vrange):
            hash_gen.add_int(len(self.vrange))

            for vrange in self.vrange:
                hash_gen.add_int(math.floor(vrange.min_n * self.divisor + 0.5))
                hash_gen.add_int(math.floor(vrange.max_n * self.divisor + 0.5))


class CharParameter(SimpleParameter):
    pass


class ArrayParameter(SimpleParameter):
    __slots__ = 'arange', 'fixed_array_size', 'legacy_type'

    def __init__(self, dtype, vrange=None, modulus=None, divisor=1, identifier=None, default=None, arange=None):
        SimpleParameter.__init__(self, dtype, vrange, modulus, divisor, identifier, default)
        self.arange = arange

        fixed_array_size = []
        if self.fixed_byte_size and arange and len(arange):
            for dimension in arange:
                if len(dimension) == 1 and dimension[0].min_n == dimension[0].max_n:
                    fixed_array_size.append(dimension[0].min_n)
                else:
                    fixed_array_size.append(None)
        else:
            fixed_array_size = None

        self.fixed_array_size = fixed_array_size

    def generate_hash(self, hash_gen):
        if type(self.dtype) == str:
            # Builtin type
            SimpleParameter.generate_hash(self, hash_gen)
        else:
            self.dtype.generate_hash(hash_gen)

        if self.arange is not None:
            for dimension in self.arange[::-1]:
                if dimension is not None and len(dimension):
                    hash_gen.add_int(len(dimension))
                    for r in dimension:
                        hash_gen.add_int(r.min_n)
                        hash_gen.add_int(r.max_n)

    def pack_value(self, dg, it, dimension=None):
        primary_type = type(self.dtype) == str
        string_type = self.dtype in {'string', 'blob', 'blob32'}
        length_header_size = 2 if self.dtype != 'blob32' else 4
        legacy_array_type = primary_type and 'array' in self.dtype

        if dimension is None and self.arange:
            dimension = len(self.arange) - 1
        else:
            dimension = 0

        need_length_header = not self.fixed_array_size or not self.fixed_array_size[dimension]

        header_pos = dg.tell()

        if need_length_header:
            # Write length header now. Seek and overwrite it later.
            if length_header_size == 2:
                dg.add_uint16(0)
            else:
                dg.add_uint32(0)

        pre_pos = dg.tell()

        if dimension:
            # Pack dimension
            for i in it:
                self.pack_value(dg, i, dimension=dimension - 1)
        elif string_type:
            # TODO: fix this call
            for i in it:
                SizedParameter.pack_value(self, dg, i)
        elif legacy_array_type:
            if self.dtype == 'uint32uint8array':
                for a, b in it:
                    pack_functions[DCTypes.uint32](dg, a)
                    pack_functions[DCTypes.uint8](dg, b)
            else:
                element_type = self.dtype.replace('array', '')
                for i in it:
                    pack_functions[DCTypes[element_type]](dg, i)
        elif primary_type:
            for i in it:
                SimpleParameter.pack_value(self, dg, i)
        else:
            if hasattr(self.dtype, 'is_struct') and self.dtype.is_struct:
                for i in it:
                    self.dtype.pack_from_iterable(dg, i)
            else:
                for i in it:
                    self.dtype.pack_value(dg, i)

        if need_length_header:
            data_size = dg.tell() - pre_pos
            if data_size and need_length_header:
                post_pos = dg.tell()
                dg.seek(header_pos)
                if length_header_size == 2:
                    dg.add_uint16(data_size)
                else:
                    dg.add_uint32(data_size)
                dg.seek(post_pos)

    def unpack_value(self, dgi):
        if self.arange is None:
            return self.unpack_dimension(dgi, 0)[0]
        else:
            return self.unpack_dimension(dgi, len(self.arange) - 1)[0]

    def unpack_dimension(self, dgi, n):
        primary_type = type(self.dtype) == str
        string_type = self.dtype in {'string', 'blob', 'blob32'}
        is_blob32 = self.dtype == 'blob32'
        legacy_array_type = primary_type and self.dtype.endswith('array')

        elements = []

        if not self.fixed_array_size or not self.fixed_array_size[n]:
            length = dgi.get_uint16() if not is_blob32 else dgi.get_uint32()
            if not length:
                return elements, 0
            total_length = length + (2 if not is_blob32 else 4)
        else:
            length = total_length = self.fixed_array_size[n] * self.fixed_byte_size

        if n:
            while length:
                subelements, sublength = self.unpack_dimension(dgi, n - 1)
                elements.append(subelements)
                length -= sublength
        else:
            while length:
                if string_type:
                    element = SizedParameter.unpack_value(self, dgi)

                    if self.fixed_byte_size:
                        length -= self.fixed_byte_size
                    else:
                        length -= (2 if not is_blob32 else 4)
                        length -= len(element)
                elif legacy_array_type:
                    if self.dtype == 'uint32uint8array':
                        element = [unpack_functions[DCTypes.uint32](dgi), unpack_functions[DCTypes.uint8](dgi)]
                        length -= 5
                    else:
                        element_type = self.dtype.replace('array', '')
                        element = unpack_functions[DCTypes[element_type]](dgi)
                        length -= fixed_byte_sizes[DCTypes[element_type]]
                elif primary_type:
                    element = SimpleParameter.unpack_value(self, dgi)
                    length -= self.fixed_byte_size
                else:
                    p = dgi.tell()
                    element = self.dtype.unpack_value(dgi)
                    length -= dgi.tell() - p

                elements.append(element)

        return elements, total_length

    def unpack_bytes(self, dgi):
        is_blob32 = self.dtype == 'blob32'

        if self.arange:
            n = len(self.arange) - 1
        else:
            n = 0

        if not self.fixed_array_size or not self.fixed_array_size[n]:
            length = dgi.get_bytes(2 if not is_blob32 else 4)
            data = dgi.get_bytes(struct.unpack('<H' if not is_blob32 else '<I', length)[0])
            return b''.join((length, data))
        else:
            length = self.fixed_array_size[n]

            return dgi.get_bytes(length * self.fixed_byte_size)


class SizedParameter(SimpleParameter):
    def pack_value(self, dg, value):
        if type(value) == str:
            value = value.encode('utf-8')

        if not self.fixed_byte_size:
          if self.dtype != 'blob32':
              dg.add_string16(value)
          else:
              dg.add_string32(value)

    def unpack_value(self, dgi):
        if not self.fixed_byte_size:
            if self.dtype == 'blob32':
                return dgi.get_blob32()
            elif self.dtype == 'blob':
                return dgi.get_blob16()
            else:
                return dgi.get_string16()
        else:
            return dgi.get_bytes(self.fixed_byte_size)

    def unpack_bytes(self, dgi):
        is_blob32 = self.dtype == 'blob32'

        if not self.fixed_byte_size:
            if not is_blob32:
                length_bytes = dgi.get_bytes(2)
            else:
                length_bytes = dgi.get_bytes(4)

            length = int.from_bytes(length_bytes, 'little')
            data_bytes = dgi.get_bytes(length)
            return b''.join((length_bytes, data_bytes))
        else:
            return dgi.get_bytes(self.fixed_byte_size)


class StructParameter(SimpleParameter):
    __slots__ = 'arange', 'fixed_array_size'

    def __init__(self, dtype, vrange=None, modulus=None, divisor=1, identifier=None, default=None, arange=None):
        SimpleParameter.__init__(self, dtype, vrange, modulus, divisor, identifier, default)
        self.arange = arange

        fixed_array_size = None
        if fixed_array_size and len(arange):
            r = arange[0]
            fixed_array_size = r.min_n if r.min_n == r.max_n else None
        else:
            fixed_array_size = None

        self.fixed_array_size = fixed_array_size

    def generate_hash(self, hash_gen):
        try:
            DCTypes[self.dtype]
            SimpleParameter.generate_hash(self, hash_gen)
        except KeyError:
            self.dtype.generate_hash(hash_gen)

    def pack_value(self, dg, value):
        # TODO: fix aliases(typedef) for base types being structs.
        if type(self.dtype) == str:
            return SimpleParameter.pack_value(self, dg, value)

        self.dtype.pack_fields_from_obj(dg, value)

    def unpack_value(self, dgi):
        # TODO: fix aliases(typedef) for base types being structs.
        if type(self.dtype) == str:
            return SimpleParameter.unpack_value(self, dgi)

        return self.dtype.unpack_value(dgi)

    def unpack_bytes(self, dgi):
        # TODO: fix aliases(typedef) for base types being structs.
        if type(self.dtype) == str:
            return SimpleParameter.unpack_bytes(self, dgi)

        return self.dtype.unpack_bytes(dgi)


class DSwitch(Parameter):
    __slots__ = 'identifier', 'parameter', 'cases', 'default_case'

    def __init__(self, dtype, cases, identifier='', default_case=None, default=None):
        Parameter.__init__(self, dtype, identifier, default)
        self.identifier = identifier
        self.cases = cases
        self.default_case = default_case

    def validate_value(self, value):
        return True

    def generate_hash(self, hash_gen):
        hash_gen.add_string(self.identifier)

        self.dtype.generate_hash(hash_gen)

        hash_gen.add_int(len(self.cases))
        for case in self.cases:
            try:
                dg = Datagram()
                pack_functions[DCTypes[self.dtype]](dg, case.value)
            except KeyError:
                dg = Datagram()
                self.dtype.pack_value(dg, case.value)

            hash_gen.add_bytes(dg.bytes())

            hash_gen.add_int(len(case.parameters) + 1)
            self.dtype.generate_hash(hash_gen)

            for parameter in case.parameters:
                parameter.generate_hash(hash_gen)

        if self.default_case is not None:
            hash_gen.add_int(len(self.default_case.parameters) + 1)
            self.dtype.generate_hash(hash_gen)

            for parameter in self.default_case.parameters:
                parameter.generate_hash(hash_gen)

    def pack_value(self, dg, it):
        switched_val = it.pop(0)
        first = self.dtype.pack_value(switched_val)
        for case in self.cases:
            if case.value == switched_val:
                for item, parameter in zip(it, case.parameters):
                    parameter.pack_value(dg, item)
                    break
        else:
           for item, parameter in zip(it, self.default_case.parameters):
               parameter.pack_value(dg, item)

    def unpack_value(self, dgi):
        first = self.dtype.unpack_value(dgi)

        for case in self.cases:
            if case.value == first:
                rest = [parameter.unpack_value(dgi) for parameter in case.parameters]
                break
        else:
            rest = [parameter.unpack_value(dgi) for parameter in self.default_case.parameters]

        return tuple([first] + rest)

    def unpack_bytes(self, dgi):
        curr = dgi.tell()
        first_bytes = self.dtype.unpack_bytes(dgi)
        dgi.seek(curr)
        first = self.dtype.unpack_value(dgi)

        for case in self.cases:
            if case.value == first:
                rest = [parameter.unpack_bytes(dgi) for parameter in case.parameters]
                break
        else:
            rest = [parameter.unpack_bytes(dgi) for parameter in self.default_case.parameters]

        return b''.join((first_bytes, b''.join(rest)))


from typing import Any

@with_slots
@dataclass
class DSwitchCase:
    value: Any
    parameters: list
    breaked: bool


class KeywordDef(object):
    __slots__ = 'name', 'value', 'is_default'

    def __init__(self, name, value, is_default):
        self.name = name
        self.value = value
        self.is_default = is_default


class TypeDef(object):
    __slots__ = 'old_type', 'ranges', 'modulus', 'divisor', 'aranges', 'new_type', '__weakref__'

    def __init__(self, old_type, new_type, ranges=(), modulus=None, divisor=None, aranges=None):
        self.old_type = old_type
        self.new_type = new_type
        self.ranges = ranges
        self.modulus = modulus
        self.divisor = divisor
        self.aranges = aranges


class DCField(DCPackable):
    __slots__ = 'name', 'keywords', 'number', 'dclass', 'flags'

    def __init__(self, name, keywords=()):
        self.name = name
        self.keywords = keywords
        self.number = -1
        self.dclass = None
        self.flags = self.calc_flags()

    @property
    def is_broadcast(self):
        return self.flags & HistoricKeywords.broadcast

    @property
    def is_ram(self):
        return self.flags & HistoricKeywords.ram

    @property
    def is_required(self):
        return self.flags & HistoricKeywords.required

    @property
    def is_db(self):
        return self.flags & HistoricKeywords.db

    @property
    def is_ownsend(self):
        return self.flags & HistoricKeywords.ownsend

    @property
    def is_clsend(self):
        return self.flags & HistoricKeywords.clsend

    @property
    def is_airecv(self):
        return self.flags & HistoricKeywords.airecv

    @property
    def is_ownrecv(self):
        return self.flags & HistoricKeywords.ownrecv

    @property
    def is_clrecv(self):
        return self.flags & HistoricKeywords.clrecv

    def generate_hash(self, hash_gen):
        hash_gen.add_string(self.name)
        hash_gen.add_int(self.number)

    def calc_flags(self):
        flags = 0

        for kw in self.keywords:
            # TODO: remove historic keyword bitmask if it is redefined.
            try:
                flags |= HistoricKeywords[kw]
            except KeyError:
                continue

        return flags

    def get_dclass(self):
        if not self.dclass:
            return None

        return self.dclass()

    def __str__(self):
        return '%s %s %s %s' % (self.__class__.__name__, self.name, self.keywords, self.number)

    def num_args(self):
        return 0

    def receive_update(self, obj, dgi):
        if isinstance(self, ParameterField):
            value = self.unpack_value(dgi)
            setattr(obj, self.name, value)
        else:
            if not hasattr(obj, self.name):
                v = self.unpack_value(dgi)
                return

            else:
                value = self.unpack_value(dgi)

                getattr(obj, self.name)(*value)

    def client_format_update(self, do_id, args):
        # TODO
        pass

    def ai_format_update(self, do_id, to_id, from_id, args):
        dg = Datagram()

        dg.add_uint8(1)
        dg.add_channel(to_id)
        dg.add_channel(from_id)
        dg.add_uint16(STATESERVER_OBJECT_UPDATE_FIELD)
        dg.add_uint32(do_id)
        dg.add_uint16(self.number)
        self.pack_value(dg, args)
        return dg

    def ai_format_update_msg_type(self, do_id, to_id, from_id, msg_type, args):
        # TODO
        pass


class ParameterField(DCField):
    __slots__ = 'parameter', 'is_struct_field'

    def __init__(self, parameter, keywords):
        DCField.__init__(self, '', keywords)
        self.parameter = parameter
        self.is_struct_field = False
        self.name = parameter.identifier

    def generate_hash(self, hash_gen):
        if not self.is_struct_field and len(self.keywords):
            if self.flags != ~0:
                hash_gen.add_int(self.flags)

        self.parameter.generate_hash(hash_gen)

    def pack_value(self, dg, arg):
        self.parameter.pack_value(dg, arg)

    def unpack_value(self, dgi):
        return self.parameter.unpack_value(dgi)

    def unpack_bytes(self, dgi):
        return self.parameter.unpack_bytes(dgi)

    def __str__(self):
        return '%s (%s) keywords=%s, flags=%s' % (self.__class__.__name__, str(self.parameter), self.keywords, self.flags)

    def num_args(self):
        return 1


class AtomicField(DCField):
    __slots__ = 'parameters'

    def __init__(self, name, parameters=(), keywords=()):
        DCField.__init__(self, name, keywords)
        self.parameters = parameters

    def generate_hash(self, hash_gen):
        DCField.generate_hash(self, hash_gen)
        hash_gen.add_int(len(self.parameters))

        for i, parameter in enumerate(self.parameters):
            parameter.generate_hash(hash_gen)

        if self.flags != ~0:
            hash_gen.add_int(self.flags)

    def pack_value(self, dg, args):
        if len(args) != len(self.parameters):
            raise DCParseError('Expected %s for packing, received %s.' % (len(self.parameters), len(args)))

        for parameter, arg in zip(self.parameters, args):
            parameter.pack_value(dg, arg)

    def unpack_value(self, dgi):
        return tuple(parameter.unpack_value(dgi) for parameter in self.parameters)

    def unpack_bytes(self, dgi):
        return b''.join((parameter.unpack_bytes(dgi) for parameter in self.parameters))

    def num_args(self):
        return len(self.parameters)


class MolecularField(DCField):
    __slots__ = 'subfields'

    def __init__(self, name, subfields, keywords=()):
        DCField.__init__(self, name, keywords)
        self.subfields = subfields  # type: List[DCField]

    def resolve_keywords(self):
        keywords = set(self.keywords)
        for subfield in self.subfields:
            for kw in subfield.keywords:
                if kw not in keywords:
                    keywords.add(kw)

        self.keywords = tuple(keywords)
        self.flags = self.calc_flags()

    def generate_hash(self, hash_gen):
        DCField.generate_hash(self, hash_gen)
        hash_gen.add_int(len(self.subfields))

        for subfield in self.subfields:
            subfield.generate_hash(hash_gen)

    def pack_value(self, dg, args):
        n = self.num_args()
        assert len(args) == n

        for subfield in self.subfields:
            n = subfield.num_args()
            subfield.pack_value(dg, args[:n])
            args = args[n:]

    def num_args(self):
        return sum((subfield.num_args() for subfield in self.subfields))

    def unpack_value(self, dgi):
        return functools.reduce(operator.iconcat, [field.unpack_value(dgi) for field in self.subfields], [])

    def unpack_bytes(self, dgi):
        return b''.join((field.unpack_bytes(dgi) for field in self.subfields))


class DClass:
    def __init__(self, dcfile, name, parents, is_struct):
        self.dcfile = dcfile  # type: ref
        self.name = name  # type: str
        self.fields = []  # type: List[DCField]
        self.fields_by_index = WeakValueDictionary()
        self.fields_by_name = WeakValueDictionary()
        self.inherited_fields = []  # type: List[ref]
        self.number = -1
        self.parents = parents  # type: List[DClass]
        self.is_struct = is_struct  # type: bool
        self.constructor = None

    def __getitem__(self, item):
        if type(item) == int:
            return self.inherited_fields[item]
        else:
            return self.fields_by_name[item]

    def add_field(self, field):
        field.dclass = ref(self)

        if isinstance(field, MolecularField):
            field.subfields = [proxy(self[name]) for name in field.subfields]
            field.resolve_keywords()

        if field.name:
            if field.name == self.name:
                if not self.is_struct:
                    raise DCParseError('A non-network field cannot be stored on a dclass')

                if self.constructor is not None:
                    raise DCParseError('Duplicate constructor for %s.' % self.name)

                if not isinstance(field, AtomicField):
                    raise DCParseError('Constructor fields must be atomic fields. Received %s instead.' % field.__class__)

                self.fields_by_name[field.name] = field
                self.constructor = field
                return

            if field.name in self.fields_by_name:
                raise DCParseError('duplicate field name', field.name)

            self.fields_by_name[field.name] = field

        self.dcfile().add_field(field)

        if field.number in self.fields_by_index:
            raise DCParseError

        self.fields_by_index[field.number] = field

        self.fields.append(field)

    def build_inherited_fields(self):

        namespace = set()

        for parent in self.parents:
            for field in parent.inherited_fields:
                name = field.name
                if not name:
                    self.inherited_fields.append(field)
                elif name not in namespace:
                    self.inherited_fields.append(field)
                    namespace.add(name)

                    self.fields_by_name[name] = field

        for field in self.fields:
            name = field.name
            if not name:
                self.inherited_fields.append(field)
            else:
                if name in namespace:
                    self.shadow_inherited_field(name)

                self.fields_by_name[name] = field
                self.inherited_fields.append(field)

    def shadow_inherited_field(self, name):
        for field in self.inherited_fields:
            if field.name == name:
                self.inherited_fields.remove(field)
                return

    def generate_hash(self, hash_gen):
        hash_gen.add_string(self.name)

        if self.is_struct:
            hash_gen.add_int(1)

        hash_gen.add_int(len(self.parents))
        for parent in self.parents:
            hash_gen.add_int(parent.number)

        if self.constructor is not None:
            self.constructor.generate_hash(hash_gen)

        hash_gen.add_int(len(self.fields))
        for field in self.fields:
            field.generate_hash(hash_gen)

    def __str__(self):
        if not self.is_struct:
            return 'dclass {}'.format(self.name)
        return 'struct {}'.format(self.name)

    def pack_fields_from_obj(self, dg, obj):
        for field in self.fields:
            self.pack_field(dg, obj, field)

    def receive_update(self, obj, dgi):
        field_index = dgi.get_uint16()
        field = self.fields_by_index[field_index]
        field.receive_update(obj, dgi)

    def receive_update_broadcast_required(self, obj, dgi):
        for field in self.inherited_fields:
            if not isinstance(field, MolecularField) and field.is_required and field.is_broadcast:
                field.receive_update(obj, dgi)

    def receive_update_broadcast_required_owner(self, obj, dgi):
        for field in self.inherited_fields:
            if not isinstance(field, MolecularField) and field.is_required:  # TODO: check if ownrecv, if not discard value
                field.receive_update(obj, dgi)

    def receive_update_all_required(self, obj, dgi):
        for field in self.inherited_fields:
            if not isinstance(field, MolecularField) and field.is_required:
                field.receive_update(obj, dgi)

    def receive_update_other(self, obj, dgi):
        num_fields = dgi.get_uint16()

        for i in range(num_fields):
            self.receive_update(obj, dgi)

    def direct_update(self, obj, field_name, blob):
        self.fields_by_name[field_name].receive_update(obj, blob)

    def pack_required_field(self, dg, obj, field):
        self.pack_field(dg, obj, field)

    def ai_format_update(self, field_name, do_id, to_id, from_id, args):
        return self.fields_by_name[field_name].ai_format_update(do_id, to_id, from_id, args)

    def ai_format_update_msg_type(self, field_name, do_id, to_id, from_id, msgtype, args):
        return self.fields_by_name[field_name].ai_format_update_msg_type(do_id, to_id, from_id, msgtype, args)

    def ai_format_generate(self, obj, do_id, parent_id, zone_id, district_channel_id, from_channel_id, optional_fields):
        dg = Datagram()
        dg.add_uint8(1)
        dg.add_channel(district_channel_id)
        dg.add_channel(from_channel_id)
        if optional_fields:
            dg.add_uint16(STATESERVER_OBJECT_GENERATE_WITH_REQUIRED_OTHER)
        else:
            dg.add_uint16(STATESERVER_OBJECT_GENERATE_WITH_REQUIRED)

        #if parent_id:
        dg.add_uint32(parent_id)

        dg.add_uint32(zone_id)
        dg.add_uint16(self.number)
        dg.add_uint32(do_id)

        for field in self.inherited_fields:
            if not isinstance(field, MolecularField) and field.is_required:
                self.pack_field(dg, obj, field)

        if optional_fields:
            dg.add_uint16(len(optional_fields))

            for field_name in optional_fields:
                field = self.fields_by_name[field_name]
                dg.add_uint16(field.number)
                self.pack_field(dg, obj, field)

        return dg

    def pack_field(self, dg, obj, field):
        if isinstance(field, ParameterField):
            try:
                if field.name:
                    val = getattr(obj, field.name)
                    field.pack_value(dg, val)
                    return
                elif isinstance(obj, collections.abc.Sequence):
                    val = obj[self.fields.index(field)]
                    field.pack_value(dg, val)
                    return
                else:
                    raise AttributeError
            except AttributeError:
                assert field.parameter.default is not None
                field.pack_default(dg)
                return
        elif isinstance(field, MolecularField):
            raise Exception
        else:

            if not len(field.parameters):
                return

            getter = field.name

            if getter[:3] == 'set':
                getter = ''.join(('get', getter[3:]))

            try:
                if field.name:
                    val = getattr(obj, getter)()

                    if len(field.parameters) == 1:
                        val = (val, )
                    else:
                        assert isinstance(val, collections.abc.Sequence)
                    field.pack_value(dg, val)
                    return

                elif isinstance(obj, collections.abc.Sequence):
                    val = obj[self.fields.index(field)]
                    field.pack_value(dg, val)
                    return
                else:
                    raise AttributeError
            except AttributeError as e:
                assert field.parameter.default is not None
                field.pack_default(dg)

    def ai_database_generate_context(self, context_id, parent_id, zone_id, owner_channel, database_server_id, from_channel_id):
        dg = Datagram()
        dg.add_uint8(1)
        dg.add_channel(database_server_id)
        dg.add_channel(from_channel_id)
        dg.add_uint16(STATESERVER_OBJECT_CREATE_WITH_REQUIRED_CONTEXT)
        dg.add_uint32(parent_id)
        dg.add_uint32(zone_id)
        dg.add_uint32(owner_channel)
        dg.add_uint16(self.number)
        dg.add_uint32(context_id)

        for field in self.inherited_fields:
            if not isinstance(field, MolecularField) and field.is_required:
                field.pack_default(dg)

        return dg

    def database_generate_context(self, obj, context_id, parent_id, zone_id, owner_channel, database_server_id, from_channel_id):
        dg = Datagram()
        dg.add_uint8(1)
        dg.add_channel(database_server_id)
        dg.add_channel(from_channel_id)
        dg.add_uint16(STATESERVER_OBJECT_CREATE_WITH_REQUIRED_CONTEXT)
        dg.add_uint32(parent_id)
        dg.add_uint32(zone_id)
        dg.add_channel(owner_channel)
        dg.add_uint16(self.number)
        dg.add_uint32(context_id)

        for field in self.inherited_fields:
            if not isinstance(field, MolecularField) and field.is_required:
                self.pack_required_field(dg, obj, field)

        return dg

    def pack_value(self, dg, obj):
        for field in self.fields:
            self.pack_field(dg, obj, field)

    def pack_from_iterable(self, dg, it):
        for field, value in zip(self.fields, it):
            field.pack_value(dg, value)

    def unpack_value(self, dgi):
        return [field.unpack_value(dgi) for field in self.fields]

    def unpack_bytes(self, dgi):
        return b''.join([field.unpack_bytes(dgi) for field in self.fields])
