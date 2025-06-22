from typing import NoReturn

from .visitor import TransformVisitor, NodeVisitor
from .parser import *
from .builtin import is_built_in_type
from dataclasses import replace


class TypeSolverVisitor(TransformVisitor):
    def __init__(self):
        super().__init__()
        self.global_var_dict = {}  # name |-> type
        self.bounded_var_names = []

    def _error(self, node: ASTNode, msg: str) -> NoReturn:
        raise TypeError(f"[Line {node.lineno}] Type Error: {msg}")

    def visit_TypeAssignStmt(self, node: TypeAssignStmt):
        self.global_var_dict[node.name] = self.visit(node.type)
        return None

    def visit_LambdaExpr(self, node: LambdaExpr):
        self.bounded_var_names.append(node.param_name)
        param_type = self.visit(node.param_type)
        body = self.visit(node.body)
        self.bounded_var_names.pop()
        return replace(node, param_type=param_type, body=body)

    def visit_TypeLambdaExpr(self, node: TypeLambdaExpr):
        self.bounded_var_names.append(node.param_name)
        body = self.visit(node.body)
        self.bounded_var_names.pop()
        return replace(node, body=body)

    def visit_ForAllType(self, node: ForAllType):
        self.bounded_var_names.append(node.param_name)
        body = self.visit(node.body)
        self.bounded_var_names.pop()
        return replace(node, body=body)

    def visit_ArrowType(self, node: ArrowType):
        left_type = self.visit(node.left)
        right_type = self.visit(node.right)
        return ArrowType(left_type, right_type)

    def visit_AppType(self, node: AppType):
        func_type = self.visit(node.func)
        type_arg = self.visit(node.arg)
        if not isinstance(func_type, ForAllType):
            self._error(node, f"For all type expected, got '{func_type}'")
        app_result = TypeSubstitutionVisitor(
            old=NamedType(func_type.param_name),
            new=type_arg,
        ).visit(func_type.body)
        return app_result

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
        return ListType(self.visit(node.elem_type))

    def visit_RecordType(self, node: RecordType):
        return RecordType({label: self.visit(type) for label, type in node.fields.items()})


_temp_name_idx = 0


def _new_temp_name(name: str) -> str:
    global _temp_name_idx
    _temp_name_idx += 1
    return f"{name}${_temp_name_idx}"


class TypeSubstitutionVisitor(TransformVisitor):
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
            return replace(node, body=self.visit(node.body))
        else:
            temp_name = _new_temp_name(node.param_name)
            result_body = TypeSubstitutionVisitor(
                NamedType(node.param_name), NamedType(temp_name)
            ).visit(node.body)
            result_body = self.visit(result_body)
            return replace(node, param_name=temp_name, body=result_body)

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
