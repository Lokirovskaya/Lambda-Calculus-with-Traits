from typing import NoReturn
from dataclasses import replace

from .parser import *
from .visitor import NodeVisitor, TransformVisitor


"""
No TraitStmt, StructStmt, ImplStmt here
"""


class InterpreterVisitor(NodeVisitor):
    def __init__(self):
        super().__init__()
        self.global_var_dict = {}  # name |-> value
        self.bounded_var_names = []  # stack

        self.stmt_eval_info = []  # [(lineno, info)]
        self.cur_lineno = None

        with open("step5_eval.rs", "w", encoding="utf-8"):
            pass

    def _error(self, msg: str) -> NoReturn:
        raise ValueError(f"[Line {self.cur_lineno}] Runtime Error: {msg}")

    def _log(self, stmt, result):
        with open("step5_eval.rs", "a", encoding="utf-8") as f:
            if result is not None:
                f.write(f"{stmt}  // ==> {result}\n")
            else:
                f.write(f"{stmt}\n")

    ###############################################################

    def visit_AssignStmt(self, node: AssignStmt):
        self.cur_lineno = node.lineno
        stmt_eval = self.visit(node.expr)
        self.global_var_dict[node.name] = stmt_eval
        self._log(node, stmt_eval)

    def visit_ExprStmt(self, node: ExprStmt):
        self.cur_lineno = node.lineno
        eval = self.visit(node.expr)
        self._log(node, eval)

    def visit_LambdaExpr(self, node: LambdaExpr):
        self.bounded_var_names.append(node.param_name)
        # Type annotation erasure + lazy eval
        eval = replace(node, body=node.body, param_type=None)
        self.bounded_var_names.pop()
        return eval

    def visit_TypeLambdaExpr(self, node: TypeLambdaExpr):
        # Type param erasure
        return self.visit(node.body)

    def visit_IfExpr(self, node: IfExpr):
        cond_eval = self.visit(node.condition)
        if _is_true(cond_eval):
            return self.visit(node.then_expr)
        elif _is_false(cond_eval):
            return self.visit(node.else_expr)

        return replace(
            node,
            condition=cond_eval,
            then_expr=self.visit(node.then_expr),
            else_expr=self.visit(node.else_expr),
        )

    def visit_LogicOrExpr(self, node: LogicOrExpr):
        left_eval = self.visit(node.left)
        if _is_true(left_eval):
            return left_eval

        right_eval = self.visit(node.right)
        if _is_true(right_eval):
            return right_eval

        if _is_false(left_eval) and _is_false(right_eval):
            return left_eval

        return replace(
            node,
            left=left_eval,
            right=right_eval,
        )

    def visit_LogicAndExpr(self, node: LogicAndExpr):
        left_eval = self.visit(node.left)
        if _is_false(left_eval):
            return left_eval

        right_eval = self.visit(node.right)
        if _is_false(right_eval):
            return right_eval

        if _is_true(left_eval) and _is_true(right_eval):
            return left_eval

        return replace(
            node,
            left=left_eval,
            right=right_eval,
        )

    def visit_LogicNotExpr(self, node: LogicNotExpr):
        eval = self.visit(node.expr)
        if _is_true(eval):
            return _to_value(node, False)
        elif _is_false(eval):
            return _to_value(node, True)

        return replace(node, expr=eval)

    def visit_RelExpr(self, node: RelExpr):
        left_eval = self.visit(node.left)
        right_eval = self.visit(node.right)
        if _is_val(left_eval) and _is_val(right_eval):
            if node.op == "==":
                return _to_value(node, left_eval.value == right_eval.value)
            elif node.op == "!=":
                return _to_value(node, left_eval.value != right_eval.value)
            elif node.op == ">":
                return _to_value(node, left_eval.value > right_eval.value)
            elif node.op == ">=":
                return _to_value(node, left_eval.value >= right_eval.value)
            elif node.op == "<":
                return _to_value(node, left_eval.value < right_eval.value)
            elif node.op == "<=":
                return _to_value(node, left_eval.value <= right_eval.value)
            else:
                self._error(node, f"Unknown operator for RelExpr: {node.op}")

        return replace(
            node,
            left=left_eval,
            right=right_eval,
        )

    def visit_AddExpr(self, node: AddExpr):
        left_eval = self.visit(node.left)
        right_eval = self.visit(node.right)
        if _is_val(left_eval) and _is_val(right_eval):
            if node.op == "+":
                return _to_value(node, left_eval.value + right_eval.value)
            elif node.op == "-":
                return _to_value(node, left_eval.value - right_eval.value)
            else:
                self._error(node, f"Unknown operator for AddExpr: {node.op}")
        if isinstance(left_eval, ListExpr) and isinstance(right_eval, ListExpr):
            return ListExpr(elements=left_eval.elements + right_eval.elements, lineno=node.lineno)

        return replace(
            node,
            left=left_eval,
            right=right_eval,
        )

    def visit_MulExpr(self, node: MulExpr):
        left_eval = self.visit(node.left)
        right_eval = self.visit(node.right)
        if _is_val(left_eval) and _is_val(right_eval):
            if node.op == "*":
                return _to_value(node, left_eval.value * right_eval.value)
            elif node.op == "/":
                if right_eval.value == 0:
                    self._error(node, "Division by zero")
                return _to_value(node, left_eval.value // right_eval.value)
            elif node.op == "%":
                if right_eval.value == 0:
                    self._error(node, "Division by zero")
                return _to_value(node, left_eval.value % right_eval.value)
            else:
                self._error(node, f"Unknown operator for MulExpr: {node.op}")

        return replace(
            node,
            left=left_eval,
            right=right_eval,
        )

    def visit_NegExpr(self, node: NegExpr):
        eval = self.visit(node.expr)
        if _is_val(eval):
            return _to_value(node, -eval.value)
        return replace(node, expr=eval)

    def visit_AppExpr(self, node: AppExpr):
        func_eval = self.visit(node.func)
        arg_eval = self.visit(node.arg)
        if isinstance(func_eval, LambdaExpr):
            subst = _TermSubstitutionVisitor(
                old=NamedExpr(func_eval.param_name), new=arg_eval
            ).visit(func_eval.body)
            return self.visit(subst)

        if isinstance(func_eval, NamedExpr) and func_eval.is_builtin:
            if func_eval.name == "print":
                print(arg_eval.value, end="")
                return arg_eval
            elif func_eval.name == "println":
                print(arg_eval.value)
                return arg_eval
            elif func_eval.name == "string_to_int":
                return replace(arg_eval, value=int(arg_eval.value))
            elif func_eval.name == "int_to_string":
                return replace(arg_eval, value=str(arg_eval.value))
            elif func_eval.name == "head":
                if len(arg_eval.elements) == 0:
                    self._error("Calling 'head' on empty list")
                return arg_eval.elements[0]
            elif func_eval.name == "tail":
                return replace(arg_eval, elements=arg_eval.elements[1:])

        return replace(
            node,
            func=func_eval,
            arg=arg_eval,
        )

    def visit_TypeAppExpr(self, node: TypeAppExpr):
        # Type args erasure
        return self.visit(node.func)

    def visit_TypeAnnotatedExpr(self, node: TypeAnnotatedExpr):
        # Type annotations erasure
        return self.visit(node.expr)

    def visit_FieldAccessExpr(self, node: FieldAccessExpr):
        record_eval = self.visit(node.record)
        if isinstance(record_eval, RecordExpr):
            return self.visit(record_eval.fields[node.field_name])

        return replace(node, record=record_eval)

    def visit_NamedExpr(self, node: NamedExpr):
        if node.name in self.bounded_var_names:
            return node
        elif node.name in self.global_var_dict:
            return self.global_var_dict[node.name]
        elif node.is_builtin:
            if node.name == "read":
                return ValueExpr(value=input())
            elif node.name == "cons":
                return LambdaExpr(
                    "__x",
                    None,
                    LambdaExpr(
                        "__xs",
                        None,
                        AddExpr(
                            ListExpr([NamedExpr("__x")]),
                            "+",
                            NamedExpr("__xs"),
                        ),
                    ),
                )
            else:
                return node

        # Should not happened, ensured by type checker
        self._error(f"Var '{node.name}' not found")

    def visit_ValueExpr(self, node: ValueExpr):
        return node

    def visit_ListExpr(self, node: ListExpr):
        return replace(
            node,
            elements=[self.visit(e) for e in node.elements],
        )

    def visit_RecordExpr(self, node: RecordExpr):
        return replace(
            node,
            fields={l: self.visit(v) for l, v in node.fields.items()},
        )


def _is_true(expr: ValueExpr):
    return isinstance(expr, ValueExpr) and expr.value is True


def _is_false(expr: ValueExpr):
    return isinstance(expr, ValueExpr) and expr.value is False


def _is_val(expr: ValueExpr):
    return isinstance(expr, ValueExpr)


def _to_value(expr, value):
    return ValueExpr(value=value)


_temp_name_idx = 0


def _new_temp_name(name: str) -> str:
    global _temp_name_idx
    _temp_name_idx += 1
    return f"{name}${_temp_name_idx}"


class _TermSubstitutionVisitor(TransformVisitor):
    def __init__(self, old: NamedExpr, new: Expr):
        assert isinstance(old, NamedExpr)
        self.old = old
        self.new = new

    def visit_LambdaExpr(self, node: LambdaExpr):
        """
        (λx. E)[x := N] = λx. E
        (λy. E)[x := N] = λy. E[x := N]  if y ∉ FV(N)
        (λy. E)[x := N] = λz. E[y := z][x := N]
        """
        if node.param_name == self.old.name:
            return node
        elif node.param_name not in _FreeVarVisitor().visit(self.new):
            return LambdaExpr(node.param_name, None, self.visit(node.body))
        else:
            temp_name = _new_temp_name(node.param_name)
            result_body = _TermSubstitutionVisitor(
                NamedExpr(node.param_name), NamedExpr(temp_name)
            ).visit(node.body)
            result_body = self.visit(result_body)
            return LambdaExpr(temp_name, None, result_body)

    def visit_NamedExpr(self, node: NamedExpr):
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
