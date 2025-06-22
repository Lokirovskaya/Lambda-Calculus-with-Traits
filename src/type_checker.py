from typing import NoReturn

from .parser import *
from .visitor import NodeVisitor
from .env import Env
from .builtin import BoolType, IntType, StringType, TypeType
from .type_solver import TypeSubstitutionVisitor


"""
No TraitStmt, StructStmt, ImplStmt here
"""


class TypeCheckerVisitor(NodeVisitor):
    def __init__(self):
        super().__init__()

        # global_env 中包含 assignment bindings 和 trait fields
        self.global_env: Env = Env()  # expr |-> type
        self.cur_env = self.global_env

        self.get_inst_types: dict[str, set[Type]] = {}  # trait_name |-> set of inst_types

        with open("step3_type_checked.rs", "w", encoding="utf-8") as f:
            pass

    def _log(self, stmt, type):
        with open("step3_type_checked.rs", "a", encoding="utf-8") as f:
            if type is not None:
                f.write(f"{stmt} // : {type}\n")
            else:
                f.write(f"{stmt}\n")

    def _error(self, node: ASTNode, msg: str) -> NoReturn:
        raise TypeError(f"[Line {node.lineno}] Type Error: {msg}")

    ###############################################################

    def visit_AssignStmt(self, node: AssignStmt):
        stmt_type = self.visit(node.expr)
        self.global_env.set(name=node.name, value=stmt_type)
        self._log(node, stmt_type)

    def visit_ExprStmt(self, node: ExprStmt):
        expr_type = self.visit(node.expr)
        self._log(node, expr_type)

    def visit_TraitFieldEnvStmt(self, node: TraitFieldEnvStmt):
        self.global_env.set(name=node.field_name, value=node.type)
        self._log(node, None)

    def visit_InstanceEnvStmt(self, node: InstanceEnvStmt):
        self.get_inst_types.setdefault(node.name, set()).add(node.type_param)
        self._log(node, None)

    def visit_Expr(self, node: Expr):
        return self.visit(node.expr)

    def visit_LambdaExpr(self, node: LambdaExpr):
        old_env = self.cur_env
        self.cur_env = Env(self.cur_env)

        self.cur_env.set(name=node.param_name, value=node.param_type)

        body_type = self.visit(node.body)

        self.cur_env = old_env
        return ArrowType(node.param_type, body_type)

    def visit_TypeLambdaExpr(self, node: TypeLambdaExpr):
        old_env = self.cur_env
        self.cur_env = Env(self.cur_env)
        self.cur_env.set(name=node.param_name, value=TypeType)

        body_type = self.visit(node.body)

        self.cur_env = old_env
        return ForAllType(node.param_name, body_type, trait_bounds=node.trait_bounds)

    def visit_IfExpr(self, node: IfExpr):
        cond_type = self.visit(node.condition)
        if_type = self.visit(node.then_expr)
        else_type = self.visit(node.else_expr)

        if cond_type != BoolType:
            self._error(node.cond, f"Expected 'Bool', got '{cond_type}'")

        if if_type != else_type:
            self._error(node, f"Expected '{if_type}', got '{else_type}'")

        return if_type

    def visit_LogicOrExpr(self, node: LogicOrExpr):
        left_type = self.visit(node.left)
        right_type = self.visit(node.right)
        if left_type != BoolType or right_type != BoolType:
            self._error(node, f"Expected 'Bool', got '{left_type}' and '{right_type}'")
        return BoolType

    def visit_LogicAndExpr(self, node: LogicAndExpr):
        left_type = self.visit(node.left)
        right_type = self.visit(node.right)
        if left_type != BoolType or right_type != BoolType:
            self._error(node, f"Expected 'Bool', got '{left_type}' and '{right_type}'")
        return BoolType

    def visit_LogicNotExpr(self, node: LogicNotExpr):
        expr_type = self.visit(node.expr)
        if expr_type != BoolType:
            self._error(node, f"Expected 'Bool', got '{expr_type}'")
        return BoolType

    def visit_RelExpr(self, node: RelExpr):
        left_type = self.visit(node.left)
        right_type = self.visit(node.right)

        if node.op in ("==", "!="):
            if left_type != right_type:
                self._error(node, f"Expected '{left_type}', got '{right_type}'")
        else:
            if left_type != IntType or right_type != IntType:
                self._error(node, f"Expected 'Int', got '{left_type}' and '{right_type}'")

        return BoolType

    def visit_AddExpr(self, node: AddExpr):
        left_type = self.visit(node.left)
        right_type = self.visit(node.right)
        if left_type != IntType or right_type != IntType:
            self._error(node, f"Expected 'Int', got '{left_type}' and '{right_type}'")
        return IntType

    def visit_MulExpr(self, node: MulExpr):
        left_type = self.visit(node.left)
        right_type = self.visit(node.right)
        if left_type != IntType or right_type != IntType:
            self._error(node, f"Expected 'Int', got '{left_type}' and '{right_type}'")
        return IntType

    def visit_NegExpr(self, node: NegExpr):
        expr_type = self.visit(node.expr)
        if expr_type != IntType:
            self._error(node, f"Expected 'Int', got '{expr_type}'")
        return IntType

    def visit_FieldAccessExpr(self, node: FieldAccessExpr):
        record_type = self.visit(node.record)

        if not isinstance(record_type, RecordType):
            self._error(node, f"Expected record, got '{record_type}'")

        if node.field_name not in record_type.fields:
            self._error(node, f"Unknown field '{node.field_name}' in {record_type}")
        record_type = record_type.fields[node.field_name]

        return record_type

    def visit_AppExpr(self, node: AppExpr):
        func_type = self.visit(node.func)
        arg_type = self.visit(node.arg)

        # try to infer type
        # id 1         App(id, 1)
        # =>
        # id @Int 1    App(TApp(id, Int), 1)
        if isinstance(func_type, ForAllType):
            if isinstance(func_type.body, ArrowType):
                inferred = simple_unify(
                    src_type=func_type.body.left,
                    tgt_type=arg_type,
                    type_param=NamedType(func_type.param_name),
                )
                if inferred is not None:
                    node.func = TypeAppExpr(node.func, inferred, lineno=node.lineno)
                    return self.visit(node)

            self._error(
                node, f"Type infer failed for '{func_type}' with argument type '{arg_type}'"
            )

        if not isinstance(func_type, ArrowType):
            self._error(node, f"Arrow type expected, got '{func_type}'")

        if func_type.left != arg_type:
            self._error(node, f"Expected '{func_type.left}', got '{arg_type}'")

        return func_type.right

    def visit_TypeAppExpr(self, node: TypeAppExpr):
        forall_type = self.visit(node.func)
        if not isinstance(forall_type, ForAllType):
            self._error(node, f"For-all type expected, got '{forall_type}'")

        if len(forall_type.trait_bounds) > 0:
            inst_types = set()
            for bound in forall_type.trait_bounds:
                inst_types.update(self.get_inst_types[bound])
            if node.type_arg not in inst_types:
                self._error(
                    node,
                    f"Type '{node.type_arg}' does not satisfy trait bounds '{" + ".join(forall_type.trait_bounds)}'",
                )

        return TypeSubstitutionVisitor(
            old=NamedType(forall_type.param_name),
            new=node.type_arg,
        ).visit(forall_type.body)

    def visit_TypeAnnotatedExpr(self, node: TypeAnnotatedExpr):
        expr_type = self.visit(node.expr)
        if expr_type != node.type:
            self._error(node, f"Annotated type '{node.type}', got '{expr_type}'")
        return expr_type

    def visit_NamedExpr(self, node: NamedExpr):
        try:
            type = self.cur_env.get(node.name)
            if type == TypeType:
                self._error(node, f"Identifier '{node.name}' is a type, not a variable")
            return type
        except NameError as e:
            self._error(node, e)

    def visit_ValueExpr(self, node: ValueExpr):
        value = node.value
        if isinstance(value, bool):
            return BoolType
        elif isinstance(value, int):
            return IntType
        elif isinstance(value, str):
            return StringType
        else:
            self._error(value, f"Unknown value type '{type(value)}'")

    def visit_ListExpr(self, node: ListExpr):
        if len(node.elements) == 0:
            return ListType(None)  # Todo

        first_type = self.visit(node.elements[0])
        for value in node.elements[1:]:
            value_type = self.visit(value)
            if first_type != value_type:
                self._error(value, f"Expected '{first_type}', got '{value_type}'")

        return ListType(first_type)

    def visit_RecordExpr(self, node: RecordExpr):
        record_type = RecordType({label: self.visit(value) for label, value in node.fields.items()})
        return record_type


def simple_unify(src_type: Type, type_param: Type, tgt_type: Type) -> Type:
    assert isinstance(type_param, NamedType)

    # X
    if isinstance(src_type, NamedType) and src_type == type_param:
        return tgt_type

    # X -> X
    if isinstance(src_type, ArrowType) and isinstance(tgt_type, ArrowType):
        left_unified = simple_unify(src_type.left, type_param, tgt_type.left)
        right_unified = simple_unify(src_type.right, type_param, tgt_type.right)
        if left_unified is not None and right_unified is not None and left_unified == right_unified:
            return left_unified

    # [X]
    if isinstance(src_type, ListType) and isinstance(tgt_type, ListType):
        return simple_unify(src_type.elem_type, type_param, tgt_type.elem_type)

    # Record
    if isinstance(src_type, RecordType) and isinstance(tgt_type, RecordType):
        if src_type.fields.keys() != tgt_type.fields.keys():
            return None
        last_unified = None
        for label, src_field_type in src_type.fields.items():
            tgt_field_type = tgt_type.fields[label]
            unified = simple_unify(src_field_type, type_param, tgt_field_type)
            if unified is None:
                return None
            if last_unified is not None and last_unified != unified:
                return None
            last_unified = unified
        return last_unified

    return None
