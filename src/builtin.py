from .parser import *


BoolType = NamedType("Bool")
IntType = NamedType("Int")
StringType = NamedType("String")
TypeType = "*"


def is_built_in_type(type: NamedType):
    return type.name in ("Bool", "Int", "String")


built_in_funcs = {
    "print": (
        ArrowType(StringType, StringType),
        NamedExpr("print", is_builtin=True),
    ),
    "println": (
        ArrowType(StringType, StringType),
        NamedExpr("println", is_builtin=True),
    ),
    "read": (
        StringType,
        NamedExpr("read", is_builtin=True),
    ),
    "string_to_int": (
        ArrowType(StringType, IntType),
        NamedExpr("read_int", is_builtin=True),
    ),
    "int_to_string": (
        ArrowType(IntType, StringType),
        NamedExpr("int_to_string", is_builtin=True),
    ),
    # forall a. [a] -> a
    "head": (
        ForAllType("a", ArrowType(ListType(NamedType("a")), NamedType("a")), trait_bounds=[]),
        NamedExpr("head", is_builtin=True),
    ),
    # forall a. [a] -> [a]
    "tail": (
        ForAllType(
            "a", ArrowType(ListType(NamedType("a")), ListType(NamedType("a"))), trait_bounds=[]
        ),
        NamedExpr("tail", is_builtin=True),
    ),
}
