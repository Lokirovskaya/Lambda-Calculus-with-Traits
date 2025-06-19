from .parser import NamedType


BoolType = NamedType("Bool")
IntType = NamedType("Int")
StringType = NamedType("String")
TypeType = "*"


def is_built_in_type(type: NamedType):
    return type.name in ("Bool", "Int", "String")
