from typing import NoReturn

from .parser import *
from .visitor import NodeVisitor, TransformVisitor
from .env import Env
from .builtin import BoolType, IntType, StringType, TypeType, is_built_in_type


"""
No TraitStmt, StructStmt, ImplStmt here
"""


class TypeCheckerVisitor(NodeVisitor):
    def __init__(self):
        super().__init__()
        self.global_env: Env = Env()
        self.cur_env = self.global_env

        self.type_getter_visitor = _TypeGetterVisitor()

        self.stmt_type_info = []  # [(lineno, info)]

    def _error(self, node: ASTNode, msg: str) -> NoReturn:
        raise TypeError(f"[Line {node.lineno}] Type Error: {msg}")

    def _log(self, node: ASTNode, msg: str):
        self.stmt_type_info.append((node.lineno, msg))

    def print_type_info(self, code: str):
        lines = code.splitlines()
        for lineno, info in self.stmt_type_info:
            lines[lineno - 1] = f"// {info}\n{lines[lineno - 1]}"
        with open("typed.rs", "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    ###############################################################

    def visit_AssignStmt(self, node: AssignStmt):
        stmt_type = self.visit(node.expr)
        self._log(node, f"{stmt_type}")
        self.global_env.set(name=node.name, value=stmt_type)

    def visit_TypeAssignStmt(self, node: TypeAssignStmt):
        self.type_getter_visitor.update_type_assign(
            name=node.name, type=self.type_getter_visitor.visit(node.type)
        )

    def visit_ExprStmt(self, node: ExprStmt):
        stmt_type = self.visit(node.expr)
        self._log(node, f"{stmt_type}")

    def visit_Expr(self, node: Expr):
        return self.visit(node.expr)

    def visit_LambdaExpr(self, node: LambdaExpr):
        old_env = self.cur_env
        self.cur_env = Env(self.cur_env)

        param_type = self.type_getter_visitor.visit(node.param_type)
        self.cur_env.set(name=node.param_name, value=param_type)

        body_type = self.visit(node.body)

        self.cur_env = old_env
        return ArrowType(param_type, body_type)

    def visit_TypeLambdaExpr(self, node: TypeLambdaExpr):
        old_env = self.cur_env
        self.cur_env = Env(self.cur_env)
        self.cur_env.set(name=node.param_name, value=TypeType)
        self.type_getter_visitor.bounded_var_names.append(node.param_name)

        body_type = self.visit(node.body)

        self.cur_env = old_env
        self.type_getter_visitor.bounded_var_names.pop()
        return ForAllType(node.param_name, body_type)

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
        if not isinstance(func_type, ArrowType):
            self._error(node, f"Arrow type expected, got '{func_type}'")

        if func_type.left != arg_type:
            self._error(node, f"Expected '{func_type.left}', got '{arg_type}'")

        return func_type.right

    def visit_TypeAppExpr(self, node: TypeAppExpr):
        forall_type = self.visit(node.func)
        type_arg = self.type_getter_visitor.visit(node.type_arg)
        if not isinstance(forall_type, ForAllType):
            self._error(node, f"For-all type expected, got '{forall_type}'")

        return _TypeSubstitutionVisitor(
            old=NamedType(forall_type.param_name),
            new=type_arg,
        ).visit(forall_type.body)

    def visit_TypeAnnotatedExpr(self, node: TypeAnnotatedExpr):
        expr_type = self.visit(node.expr)
        if expr_type != self.type_getter_visitor.visit(node.type):
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


class _TypeGetterVisitor(NodeVisitor):
    def __init__(self):
        super().__init__()
        self.global_var_dict = {}  # name |-> type
        self.bounded_var_names = []

    def update_type_assign(self, name: str, type: Type):
        self.global_var_dict[name] = type

    def visit_ForAllType(self, node: ForAllType):
        self.bounded_var_names.append(node.param_name)
        type = self.visit(node.body)
        self.bounded_var_names.pop()
        return ForAllType(node.param_name, type)

    def visit_ArrowType(self, node: ArrowType):
        left_type = self.visit(node.left)
        right_type = self.visit(node.right)
        return ArrowType(left_type, right_type)

    def visit_NamedType(self, node: NamedType):
        if is_built_in_type(node):
            return node
        if node.name in self.bounded_var_names:
            return node
        elif node.name in self.global_var_dict:
            return self.global_var_dict[node.name]
        else:
            raise TypeError(f"[Line {node.lineno}] Unknown type '{node.name}'")

    def visit_ListType(self, node: ListType):
        return ListType(self.visit(node.element_type))

    def visit_RecordType(self, node: RecordType):
        return RecordType({label: self.visit(type) for label, type in node.fields.items()})


_temp_name_idx = 0


def _new_temp_name(name: str) -> str:
    global _temp_name_idx
    _temp_name_idx += 1
    return f"{name}${_temp_name_idx}"


class _TypeSubstitutionVisitor(TransformVisitor):
    def __init__(self, old: NamedType, new: Type):
        assert isinstance(old, NamedType)
        self.old = old
        self.new = new

    def visit_ForAllType(self, node: ForAllType):
        """
        (λx. E)[x := N] = λx. E
        (λy. E)[x := N] = λy. E[x := N]  if y ∉ FV(N)
        (λy. E)[x := N] = λz. E[y := z][x := N]
        """
        if node.param_name == self.old.name:
            return node
        elif node.param_name not in _FreeVarVisitor().visit(self.new):
            return ForAllType(node.param_name, self.visit(node.body))
        else:
            temp_name = _new_temp_name(node.param_name)
            result_body = _TypeSubstitutionVisitor(
                NamedType(node.param_name), NamedType(temp_name)
            ).visit(node.body)
            result_body = self.visit(result_body)
            return ForAllType(temp_name, result_body)

    def visit_NamedType(self, node: NamedType):
        if node.name == self.old.name:
            return self.new
        else:
            return node


class _FreeVarVisitor(NodeVisitor):
    def __init__(self):
        super().__init__()
        self.bound_var_names = []
        self.free_vars = set()

    def visit(self, node: ASTNode):
        super().visit(node)
        return self.free_vars

    def visit_ForAllType(self, node: ForAllType):
        self.bound_var_names.append(node.param_name)
        self.visit(node.body)
        self.bound_var_names.pop()

    def visit_NamedType(self, node: NamedType):
        if node.name not in self.bound_var_names:
            self.free_vars.add(node.name)
