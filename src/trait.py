from typing import NoReturn

from .parser import *
from .visitor import TransformVisitor

"""
trait T a {x: X;}       =>  type T = forall a. {x: X;}
struct S {x: X;}        =>  type S = {x: X;}
impl T for S {x = f;}   =>  record_T = {x = f;}

Syntatic de-sugar only, no type checking.
"""


class TraitDesugarVisitor(TransformVisitor):
    def _error(self, node: ASTNode, msg: str) -> NoReturn:
        raise TypeError(f"[Line {node.lineno}] Type Error: {msg}")

    def visit_TraitStmt(self, node: TraitStmt):
        # record body
        record = RecordType({})
        for item in node.items:
            if item.name in record.fields:
                self._error(node, f"Duplicate field name '{item.name}'")
            record.fields[item.name] = item.type

        # currying
        for_all = record
        for name in reversed(node.type_params):
            for_all = ForAllType(name, for_all)

        # type definition
        type_def = TypeAssignStmt(node.name, for_all, lineno=node.lineno)
        return type_def

    def visit_StructStmt(self, node: StructStmt):
        # record body
        record_type = RecordType({})
        for item in node.items:
            if item.name in record_type.fields:
                self._error(node, f"Duplicate field name '{item.name}'")
            record_type.fields[item.name] = item.type

        # type definition
        type_def = TypeAssignStmt(node.name, record_type, lineno=node.lineno)

        # constructor
        # S = \x1. \x2. {f1=x1, f2=x2}
        lambda_params = [NamedExpr(f"__x{i}") for i in range(len(node.items))]
        lambda_types = [item.type for item in node.items]
        lambda_expr = RecordExpr(
            {item.name: lambda_params[i] for i, item in enumerate(node.items)},
        )
        for l_param, l_type in reversed(list(zip(lambda_params, lambda_types))):
            lambda_expr = LambdaExpr(l_param.name, l_type, lambda_expr)

        constructor_def = AssignStmt(node.name, lambda_expr, lineno=node.lineno)

        return [type_def, constructor_def]
