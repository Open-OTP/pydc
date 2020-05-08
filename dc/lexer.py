LEXER = r'''dc_file: type_decl ( type_decl )*

type_decl: keyword_type | typedef_type | struct_type | class_type | import_decl

class_type: KW_DCLASS IDENTIFIER dclass_base_list "{" ( field_decl ";" )* "}" ";"
struct_type: KW_STRUCT IDENTIFIER dclass_base_list "{" ( field_decl ";" )* "}" ";"
typedef_type: KW_TYPEDEF (constrained_builtin_type | IDENTIFIER) IDENTIFIER [ array_range ] ";"
keyword_type: KW_KEYWORD IDENTIFIER

dclass_base_list: (":" IDENTIFIER ("," IDENTIFIER)*)?

field_decl: parameter_field | atomic_field | molecular_field

molecular_field: IDENTIFIER ":" IDENTIFIER ( "," IDENTIFIER )*
atomic_field   : IDENTIFIER "(" (parameter ( "," parameter )*)? ")" [ keyword_list ]
parameter_field: (switch_parameter | parameter) [ keyword_list ]


parameter:  (constrained_builtin_type IDENTIFIER array_range+ ("=" array_literal)?)
    | (constrained_builtin_type array_range+ ("=" array_literal)?)
    | (constrained_builtin_type IDENTIFIER type_literal?)
    | constrained_builtin_type
    | (IDENTIFIER IDENTIFIER array_range+ ("=" array_literal)?)
    | (IDENTIFIER array_range+ ("=" array_literal)?)
    | (IDENTIFIER IDENTIFIER)
    | (IDENTIFIER)

type_literal: "=" (num_literal | char_literal | string_literal)

switch_parameter: KW_SWITCH [ IDENTIFIER ] "(" parameter ")" "{" switch_body "}"
switch_body: (switch_case switch_case* case_parameters ";")* (default_case case_parameters ";")?
switch_case: KW_CASE (num_literal | char_literal | string_literal) ":"
default_case: KW_DEFAULT ":"
case_parameters: (parameter ";")* KW_BREAK?



array_range: "[" [ int_range ("," int_range)* ] "]"
array_literal: "{" (num_literal | char_literal | string_literal | array_literal) ("," (num_literal | char_literal | string_literal | array_literal))* "}"

constrained_builtin_type: constrained_builtin_array_type | constrained_sized_type | constrained_char_type | constrained_float_type | constrained_int_type
constrained_builtin_array_type: BUILTIN_ARRAY_TYPE (int_ranges int_transform | int_transform int_ranges | int_transform | int_ranges)?
constrained_sized_type: SIZED_TYPE [ int_ranges ]
constrained_char_type: CHAR_TYPE [ char_ranges ]
constrained_float_type: FLOAT_TYPE ((float_ranges float_transform) | (float_transform float_ranges) | float_transform | float_ranges)?
constrained_int_type: INT_TYPE ((int_ranges int_transform) | (int_transform int_ranges) | int_transform | int_ranges)?

float_transform: ((MOD_OPERATOR num_literal) (DIV_OPERATOR num_literal)) | (DIV_OPERATOR num_literal) | (MOD_OPERATOR num_literal)
int_transform: ((MOD_OPERATOR INT_LITERAL) (DIV_OPERATOR INT_LITERAL)) | (DIV_OPERATOR INT_LITERAL) | (MOD_OPERATOR INT_LITERAL)

MOD_OPERATOR: "%"
DIV_OPERATOR: "/"

char_ranges: "(" (int_range | char_literal) ("," (int_range | char_literal))* ")"
float_ranges: "(" float_range ("," float_range)* ")"
int_ranges: "(" int_range ("," int_range)* ")"

int_range: INT_LITERAL [ "-" INT_LITERAL ]
float_range: num_literal [ "-" num_literal ]


keyword_list: (HISTORIC_KW | IDENTIFIER) (","? (HISTORIC_KW | IDENTIFIER))*

BUILTIN_ARRAY_TYPE.3: KW_UINT32UINT8ARRAY | KW_UINT32ARRAY | KW_UINT16ARRAY | KW_UINT8ARRAY | KW_INT32ARRAY | KW_INT16ARRAY | KW_INT8ARRAY
CHAR_TYPE.2 : "char"
INT_TYPE.2: KW_UINT64 | KW_UINT32 | KW_UINT16 | KW_UINT8 | KW_INT64 | KW_INT32 | KW_INT16 | KW_INT8
FLOAT_TYPE.2: "float64"
SIZED_TYPE.2: KW_STRING | KW_BLOB32 | KW_BLOB



import_decl: (KW_FROM MODULE_NAME MODULE_EXTENSION* star_import)
    | (KW_FROM MODULE_NAME MODULE_EXTENSION* KW_IMPORT MODULE_NAME MODULE_EXTENSION*)
    | (KW_IMPORT MODULE_NAME MODULE_EXTENSION*)

star_import: KW_IMPORT "*"

MODULE_EXTENSION: /\/[A-z]+/

MODULE_NAME: IDENTIFIER ("." IDENTIFIER)*

IDENTIFIER: /[A-Za-z_][A-Za-z_0-9]*/


char_literal    : "'" (non_single_quote | escape_sequence) "'"
string_literal  : "\"" string_character* "\""
string_character: non_double_quote | escape_sequence
escape_sequence : "\\" ( /[^\x03-\x1F]/  | ("x" HEX_DIGIT HEX_DIGIT* ))
non_single_quote: /[^\x03-\x1F'\\]/
non_double_quote: /[^\x03-\x1F"\\]/

FLOAT_LITERAL: NEG_SIGN? ((DECIMALS (DECIMAL_POINT DECIMALS)?) | (DECIMAL_POINT DECIMALS))

DECIMALS: DEC_DIGIT DEC_DIGIT*

num_literal : INT_LITERAL | FLOAT_LITERAL

DECIMAL_POINT: "."

INT_LITERAL: DEC_LITERAL | OCT_LITERAL | HEX_LITERAL | BIN_LITERAL | ZERO_LITERAL
DEC_LITERAL: NEG_SIGN? ( "1" .. "9" ) DEC_DIGIT*
NEG_SIGN: "-"
OCT_LITERAL: "0o" OCT_DIGIT+
HEX_LITERAL: "0" ( "x" | "X" ) HEX_DIGIT HEX_DIGIT*
BIN_LITERAL: "0" ( "b" | "B" ) BIN_DIGIT BIN_DIGIT*
ZERO_LITERAL : "0"

DEC_DIGIT: "0" .. "9"
OCT_DIGIT: "0" .. "7"
HEX_DIGIT: "0" .. "9" | "A" .. "F" | "a" .. "f"
BIN_DIGIT: "0" | "1"

HISTORIC_KW.4: KW_REQUIRED | KW_BROADCAST | KW_OWNRECV | KW_RAM | KW_DB | KW_CLSEND | KW_CLRECV | KW_OWNRECV | KW_AIRECV

KW_REQUIRED: "required"
KW_BROADCAST: "broadcast"
KW_OWNRECV: "ownrecv"
KW_RAM: "ram"
KW_DB: "db"
KW_CLSEND: "clsend"
KW_CLRECV: "clrecv"
KW_OWNSEND: "ownsend"
KW_AIRECV: "airecv"


KW_UINT32UINT8ARRAY: "uint32uint8array"
KW_INT32ARRAY: "int32array"
KW_INT16ARRAY: "int16array"
KW_INT8ARRAY: "int8array"
KW_UINT32ARRAY: "uint32array"
KW_UINT16ARRAY: "uint16array"
KW_UINT8ARRAY: KW_UINT8 "array"

KW_UINT64: "uint64"
KW_UINT32: "uint32"
KW_UINT16: "uint16"
KW_UINT8: "uint8"
KW_INT64: "int64"
KW_INT32: "int32"
KW_INT16: "int16"
KW_INT8: "int8"

KW_STRING: "string"
KW_BLOB32: "blob32"
KW_BLOB: "blob"


KW_SWITCH: "switch"
KW_CASE: "case"
KW_DEFAULT: "default"
KW_BREAK: "break"


KW_IMPORT: "import"
KW_FROM: "from"

KW_DCLASS: "dclass"
KW_STRUCT: "struct"
KW_TYPEDEF: "typedef"
KW_KEYWORD: "keyword"


%ignore COMMENT
COMMENT: /\/\/[^\n]*/


%ignore WHITESPACE
WHITESPACE: WHITESPACE_INLINE | /[\r\n]/+
WHITESPACE_INLINE: /[ \t]/+
'''
