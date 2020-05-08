from lark import Lark, Transformer, Tree, Token

from dc.util import HashGenerator

from dc.objects import *

from dc.error import DCParseError

import weakref


# TODO: default values for arrays


class DCFileTransformer(Transformer):
    def __init__(self):
        Transformer.__init__(self, visit_tokens=True)

        self.dcfile = DCFile()

    def dc_file(self, args):
        return args

    def typedef_type(self, args):
        args.pop(0)  # KW_TYPEDEF
        old_type = args.pop(0)
        if isinstance(old_type, Tree):
            if len(old_type.children) == 4:
                token, ranges, modulus, divisor = old_type.children
            else:
                token, ranges = old_type.children
                modulus = None
                divisor = 1
            old_type = token.value
        else:
            ranges = ()
            modulus = None
            divisor = 1
        new_type = args.pop(0)

        array_ranges = None

        if len(args):
            array_ranges = [arg.children for arg in args]

        typedef = TypeDef(old_type, new_type, ranges, modulus, divisor, array_ranges)
        self.dcfile.add_typedef(typedef)

    def class_type(self, args):
        class_name, parents, fields = args[1].value, args[2], args[3:]
        dclass = DClass(weakref.ref(self.dcfile), class_name, parents, is_struct=False)
        self.dcfile.add_class(dclass)
        for field in fields:
            dclass.add_field(field)

        dclass.build_inherited_fields()
        return dclass

    def struct_type(self, args):
        class_name, parents, fields = args[1].value, args[2], args[3:]
        dstruct = DClass(weakref.ref(self.dcfile), class_name, parents, is_struct=True)
        self.dcfile.add_class(dstruct)
        for field in fields:
            field.is_struct_field = True
            dstruct.add_field(field)
        return dstruct

    def dclass_base_list(self, args):
        return [weakref.proxy(self.dcfile.namespace[name]) for name in args]

    def field_decl(self, args):
        return args[0]

    def atomic_field(self, args):
        identifier = args.pop(0).value
        parameters = []
        keywords = []

        while args:
            v = args.pop(0)
            if isinstance(v, Parameter):
                parameters.append(v)

            if isinstance(v, Tree):
                if v.data == 'keyword_list':
                    keywords = v.children

        field = AtomicField(identifier, parameters, keywords)
        return field

    def parameter_field(self, args):
        parameter = args.pop(0)
        keywords = []

        while args:
            v = args.pop(0)

            if isinstance(v, Tree):
                if v.data == 'keyword_list':
                    keywords = v.children

        # Sometimes the lexer can't differentiate from the identifier or a keyword for parameters.
        if not isinstance(parameter, DSwitch) and not parameter.identifier and len(keywords):
            kw = keywords[0]
            if kw not in self.dcfile.keywords and not HistoricKeywords.has_keyword(kw):
                parameter.identifier = keywords.pop(0)

        field = ParameterField(parameter, keywords)
        return field

    def molecular_field(self, args):
        args = [arg.value for arg in args]
        identifier, subfields = args[0], args[1:]

        return MolecularField(identifier, subfields)

    def parameter(self, args):
        param_info = args.pop(0)
        identifier = None
        array_ranges = None
        ranges = []
        modulus = None
        divisor = 1

        if isinstance(param_info, Tree):
            if len(param_info.children) == 4:
                token, ranges, modulus, divisor = param_info.children
            else:
                token, ranges = param_info.children

            data_type = token

        elif isinstance(param_info, Token) and param_info.type == 'IDENTIFIER':
            token = param_info
            data_type, data_info = self.dcfile.resolve_type(token.value)
            if data_info is not None:
                ranges, modulus, divisor, array_ranges = data_info
        else:
            raise DCParseError('')

        if len(args) and isinstance(args[0], Token) and args[0].type == 'IDENTIFIER':
            identifier = args.pop(0).value

        current_array_ranges = None

        while args:
            v = args.pop(0)
            if isinstance(v, Tree):
                if v.data == 'array_range':
                    if current_array_ranges is None:
                        current_array_ranges = []
                    current_array_ranges.append(v.children)

        if array_ranges is None and current_array_ranges is not None:
            array_ranges = current_array_ranges
        elif current_array_ranges is not None:
            array_ranges = array_ranges + current_array_ranges

        if isinstance(data_type, Token):
            data_type = data_type.value

        if array_ranges is not None:
            return ArrayParameter(dtype=data_type, identifier=identifier, vrange=ranges, modulus=modulus,
                                  divisor=divisor, arange=array_ranges)
        elif token.type == 'IDENTIFIER':
            return StructParameter(dtype=data_type, identifier=identifier, vrange=ranges, modulus=modulus,
                                   divisor=divisor, arange=array_ranges)
        elif token.type == 'INT_TYPE':
            return IntParameter(dtype=data_type, identifier=identifier, vrange=ranges, modulus=modulus,
                                divisor=divisor)
        elif token.type == 'FLOAT_TYPE':
            return FloatParameter(dtype=data_type, identifier=identifier, vrange=ranges, modulus=modulus,
                                  divisor=divisor)
        elif token.type == 'CHAR_TYPE':
            return CharParameter(dtype=data_type, identifier=identifier, vrange=ranges, modulus=modulus,
                                 divisor=divisor)
        elif token.type == 'SIZED_TYPE':
            return SizedParameter(dtype=data_type, identifier=identifier, vrange=ranges, modulus=modulus,
                                  divisor=divisor)
        elif token.type == 'BUILTIN_ARRAY_TYPE':
            return ArrayParameter(dtype=data_type, identifier=identifier, vrange=ranges, modulus=modulus, divisor=divisor, arange=array_ranges)

    def switch_parameter(self, args):
        token = args.pop(0)  # KW_SWITCH
        switched_parameter = args.pop(0)

        cases = None
        default_case = None

        while args:
            v = args.pop(0)

            if isinstance(v, Tree):
                if v.data == 'switch_body':
                    cases = v.children

        for case in cases:
            if case.value is None:
                default_case = case
                break

        if default_case is not None:
            cases.remove(default_case)

        for case in cases:
            if not case.breaked:
                case.parameters.extend(default_case.parameters)

        return DSwitch(switched_parameter, cases, default_case=default_case)

    def switch_body(self, args):
        cases = []
        current_cases = []

        while args:
            v = args.pop(0)
            if isinstance(v, Tree):
                if v.data == 'switch_case':
                    token, case = v.children
                    current_cases.append(case)
                if v.data == 'default_case':
                    current_cases.append(None)
                if v.data == 'case_parameters':
                    breaked = False
                    if isinstance(v.children[-1], Token):
                        breaked = True
                        v.children.pop(-1)
                    parameters = v.children
                    cases.extend((DSwitchCase(case, parameters, breaked) for case in current_cases))
                    del current_cases[:]
        return Tree('switch_body', cases)

    def switch_case(self, args):
        args[0] = args[0].value
        args[1] = self.NUM_LITERAL(args[1].value)
        return Tree('switch_case', args)

    def default_case(self, args):
        return Tree('default_case', args)

    def constrained_builtin_array_type(self, args):
        token = args.pop(0)
        ranges = []
        modulus = None
        divisor = 1

        while args:
            v = args.pop(0)

            if isinstance(v, Tree):
                if v.data == 'int_ranges':
                    ranges = tuple(r.children for r in v.children)
                if v.data == 'int_transform':
                    modulus, divisor = v.children

        return Tree('constrained_builtin_array_type', [token, ranges, modulus, divisor])

    def array_range(self, args):
        if args:
            return Tree('array_range', [arg.children for arg in args])
        return Tree('array_range', [])

    def array_type(self, args):
        return Tree('array_type', args[0].children)

    def constrained_sized_type(self, args):
        token = args.pop(0)
        ranges = []
        while args:
            v = args.pop(0)

            if isinstance(v, Tree):
                if v.data == 'int_ranges':
                    ranges = tuple(r.children for r in v.children)

        return Tree('constrained_sized_type', [token, ranges])

    def constrained_char_type(self, args):
        token = args.pop(0)
        ranges = []
        while args:
            v = args.pop(0)

            if isinstance(v, Tree):
                if v.data == 'char_ranges':
                    ranges = v.children

        return Tree('constrained_char_type', [token, ranges])

    def char_ranges(self, args):
        ranges = []
        for arg in args:
            if isinstance(arg, Tree):
                ranges.append(IRange(*arg.children))
            elif type(arg) == str:
                c = ord(arg)
                ranges.append(IRange(c, c))

        return Tree('char_ranges', ranges)

    def constrained_float_type(self, args):
        token = args.pop(0)
        ranges = []
        modulus = None
        divisor = 1

        while args:
            v = args.pop(0)

            if isinstance(v, Tree):
                if v.data == 'float_ranges':
                    ranges = tuple(r.children for r in v.children)
                if v.data == 'float_transform':
                    modulus, divisor = v.children

        if modulus is not None and modulus < 0:
            raise DCParseError('Negative modulus not allowed.')

        if divisor == 0:
            raise DCParseError('Division by zero')

        if divisor < 0:
            raise DCParseError('Negative divisor not allowed.')

        return Tree('constrained_float_type', [token, ranges, modulus, divisor])

    def float_ranges(self, args):
        return Tree('float_ranges', args)

    def float_transform(self, args):
        return self.type_transform('float_transform', args)

    def constrained_builtin_type(self, args):
        return args[0]

    def constrained_int_type(self, args):
        token = args.pop(0)
        ranges = []
        modulus = None
        divisor = 1

        while args:
            v = args.pop(0)

            if isinstance(v, Tree):
                if v.data == 'int_ranges':
                    ranges = tuple(r.children for r in v.children)
                if v.data == 'int_transform':
                    modulus, divisor = v.children

        return Tree('constrained_int_type', [token, ranges, modulus, divisor])

    def int_transform(self, args):
        return self.type_transform('int_transform', args)

    def int_range(self, args):
        args = [int(arg.value) for arg in args]
        if len(args) == 1:
            args = args * 2

        return Tree('int_range', IRange(*args))

    def float_range(self, args):
        args = [int(arg.value) for arg in args]
        if len(args) == 1:
            args = args * 2

        return Tree('float_range', IRange(*args))

    def type_transform(self, name, args):
        modulus = None
        divisor = 1
        for i in range(0, len(args), 2):
            op = args[i]

            if op.value == '%':
                modulus = int(args[i + 1])
            elif op.value == '/':
                divisor = int(args[i + 1])

        return Tree(name, [modulus, divisor])

    def INT_LITERAL(self, args):
        if args.startswith('-'):
            args.value = int(args)
            return args

        args.value = int(args, 0)
        return args

    def FLOAT_LITERAL(self, args):
        args.value = float(''.join(args))
        return args

    def num_literal(self, args):
        if '.' in args:
            self.FLOAT_LITERAL(args)
        else:
            self.INT_LITERAL(args)

        return args.value

    def DECIMALS(self, args):
        return ''.join([token.value for token in args])

    def string_literal(self, args):
        return ''.join(args)

    def escape_sequence(self, args):
        if args[0].type == 'HEX_DIGIT':
            return chr(int(''.join((arg.value for arg in args)), 16))
        return ''.join((arg.value for arg in args))

    def string_character(self, args):
        return args[0]

    def char_literal(self, args):
        return args[0]

    def non_single_quote(self, args):
        value = args[0].value
        return value

    def non_double_quote(self, args):
        return args[0].value

    def import_decl(self, args):
        return Tree('import_decl', args)

    def keyword_list(self, args):
        args = [arg.value if isinstance(arg, Token) else arg for arg in args]
        return Tree('keyword_list', args)

    def identifier(self, args):
        return ''.join(args)


class DCFile:
    def __init__(self):
        self.namespace = WeakValueDictionary()
        self.classes = []  # type: List[DClass]
        self.fields = []  # type: List[ref]
        self.keywords = []  # type: List[KeywordDef]
        self.typedefs = []  # type: List[TypeDef]

    def add_typedef(self, typedef):
        self.namespace[typedef.new_type] = typedef
        self.typedefs.append(typedef)

    def add_class(self, dclass):
        if dclass.name in self.namespace:
            return False

        self.namespace[dclass.name] = dclass

        if not dclass.is_struct:
            dclass.number = len(self.classes)

        self.classes.append(dclass)

    def add_keyword(self, keyword):
        pass

    def add_field(self, field):
        field.number = len(self.fields)
        self.fields.append(weakref.ref(field))

    def generate_hash(self, hash_gen):
        hash_gen.add_int(1)

        hash_gen.add_int(len(self.classes))

        for dclass in self.classes:
            dclass.generate_hash(hash_gen)

    @property
    def hash(self):
        h = HashGenerator()
        self.generate_hash(h)
        return h.get_hash()

    def resolve_type(self, identifier):
        type_obj = None
        type_info = None

        while type_obj is None:
            try:
                if hasattr(DCTypes, identifier):
                    type_obj = identifier
                    break

                obj = self.namespace[identifier]

                if isinstance(obj, TypeDef):
                    identifier = obj.old_type
                    if type_info is not None and type_info[3] is not None and obj.aranges is not None:
                        aranges = type_info[3] + obj.aranges
                    else:
                        aranges = obj.aranges

                    type_info = (obj.ranges, obj.modulus, obj.divisor, aranges)
                else:
                    type_obj = obj

            except KeyError:
                raise DCParseError('unknown type', identifier)

        return type_obj, type_info


import os

from .lexer import LEXER


def parse_dc_file(fp: str, debug=False) -> DCFile:
    transformer = DCFileTransformer()
    dc_parser = Lark(LEXER, start='dc_file', debug=debug, parser='lalr', lexer='contextual', transformer=transformer)
    with open(fp, 'r') as f2:
        tree = dc_parser.parse(f2.read(),)

    return transformer.dcfile


def parse_dc_files(fps, debug=False) -> DCFile:
    data = ''

    for fp in fps:
        with open(fp, 'r') as f:
            data = ''.join((data, f.read()))
            f.close()

    transformer = DCFileTransformer()
    dc_parser = Lark(LEXER, start='dc_file', debug=debug, parser='lalr', lexer='contextual', transformer=transformer)
    dc_parser.parse(data,)

    return transformer.dcfile


def parse_dc(data: str, debug=False) -> DCFile:
    transformer = DCFileTransformer()
    dc_parser = Lark(LEXER, start='dc_file', debug=debug, parser='lalr', lexer='contextual', transformer=transformer)
    dc_parser.parse(data,)

    return transformer.dcfile

