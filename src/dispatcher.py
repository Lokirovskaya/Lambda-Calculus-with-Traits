from typing import NoReturn

from .visitor import TransformVisitor, NodeVisitor
from .env import Env
from .parser import *
from .builtin import is_built_in_type
from dataclasses import replace


class DispatcherVisitor(TransformVisitor):
    def __init__(self):
        super().__init__()

        # trait_field |-> trait_name
        self.which_trait: dict[str, str] = {}

        # (trait_name, inst_type) |-> inst_expr
        self.get_inst: dict[tuple[str, Type], Expr] = {}

    def _error(self, node: ASTNode, msg: str) -> NoReturn:
        raise TypeError(f"[Line {node.lineno}] Type Error: {msg}")

    ###############################################################

    def visit_TraitFieldEnvStmt(self, node: TraitFieldEnvStmt):
        self.which_trait[node.field_name] = node.trait_name
        return node

    def visit_InstanceEnvStmt(self, node: InstanceEnvStmt):
        self.get_inst[(node.name, node.type_param)] = node.inst_expr
        return node

    def visit_AssignStmt(self, node: AssignStmt):
        self.which_trait.pop(node.name, None)
        return replace(node, expr=self.visit(node.expr))

    def visit_LambdaExpr(self, node: LambdaExpr):
        popped = self.which_trait.pop(node.param_name, None)
        body = self.visit(node.body)
        if popped:
            self.which_trait[node.param_name] = popped
        return replace(node, body=body)

    def visit_TypeLambdaExpr(self, node: TypeLambdaExpr):
        popped = self.which_trait.pop(node.param_name, None)
        body = self.visit(node.body)
        if popped:
            self.which_trait[node.param_name] = popped
        return replace(node, body=body)

    def visit_TypeAppExpr(self, node: TypeAppExpr):
        """
        show @Int 5               App(TypeApp(show, Int), 5)
        =>
        inst_show_Int.show 5      App(FieldAccess(inst_show_Int, show), 5)
        """
        if isinstance(node.func, NamedExpr) and node.func.name in self.which_trait:
            trait_name = self.which_trait[node.func.name]
            inst_type = node.type_arg
            inst_expr = self.get_inst[(trait_name, inst_type)]
            return FieldAccessExpr(record=inst_expr, field_name=node.func.name, lineno=node.lineno)

        return replace(node, func=self.visit(node.func))
