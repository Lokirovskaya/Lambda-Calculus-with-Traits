from typing import NoReturn

from .visitor import TransformVisitor, NodeVisitor
from .env import Env
from .parser import *
from .builtin import is_built_in_type, TypeType
from dataclasses import replace


class DispatcherVisitor(TransformVisitor):
    def __init__(self):
        super().__init__()

        # trait_field |-> trait_name
        self.which_trait: dict[str, str] = {}

        # (trait_name, inst_type) |-> inst_expr
        self.get_inst: dict[tuple[str, Type], Expr] = {}

        self._tmp_idx = 0

    def _error(self, node: ASTNode, msg: str) -> NoReturn:
        raise TypeError(f"[Line {node.lineno}] Type Error: {msg}")

    def temp_name(self, prefix):
        self._tmp_idx += 1
        return f"{prefix}_{self._tmp_idx}"

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
        # 正常 shadow param
        if len(node.trait_bounds) == 0:
            popped = self.which_trait.pop(node.param_name, None)
            body = self.visit(node.body)
            if popped:
                self.which_trait[node.param_name] = popped

            return replace(node, body=body)

        # 为每一个 bound 新建一个字典参数
        # \T impl A+B. body
        # =>
        # \T impl A+B. \dictA. \dictB. body
        else:
            popped = self.which_trait.pop(node.param_name, None)

            lambda_param_type = NamedType(node.param_name)

            body = node.body
            for trait in node.trait_bounds:
                dict_param = NamedExpr(self.temp_name(f"__dictp_{trait}"))
                self.get_inst[(trait, lambda_param_type)] = dict_param
                body = LambdaExpr(param_name=dict_param.name, param_type=TypeType, body=body)

            body = self.visit(body)

            if popped:
                self.which_trait[node.param_name] = popped
            return replace(node, body=body)

    def visit_TypeAppExpr(self, node: TypeAppExpr):
        """
        对于 trait field
            show @Int               TypeApp(show, Int)
            =>
            inst_show_Int.show      FieldAccess(inst_show_Int, show)
        对于一般的类型为 \T impl A+B 的表达式
            f @T                      TypeApp(f, T)
            =>
            f @T inst_T_A inst_T_B    App(App(TypeApp(f, T), inst_T_A), inst_T_B)
        """
        if isinstance(node.func, NamedExpr) and node.func.name in self.which_trait:
            trait_name = self.which_trait[node.func.name]
            inst_type = node.type_arg
            inst_expr = self.get_inst[(trait_name, inst_type)]
            return FieldAccessExpr(record=inst_expr, field_name=node.func.name, lineno=node.lineno)
        
        elif isinstance(node.func.checked_type, ForAllType) and len(node.func.checked_type.trait_bounds) > 0:
            app = node
            for trait_name in node.func.checked_type.trait_bounds:
                inst_type = node.type_arg
                inst_expr = self.get_inst[(trait_name, inst_type)]
                app = AppExpr(func=app, arg=inst_expr, lineno=node.lineno)
            return app

        return replace(node, func=self.visit(node.func))

    def visit_NamedExpr(self, node: NamedExpr):
        if node.name in self.which_trait:
            self._error(node, f"Unsolved trait field accessor, use '{node} @T' instead")
        return node
