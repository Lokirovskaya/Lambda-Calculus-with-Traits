from typing import NoReturn
import dataclasses

from .parser import *
from .visitor import NodeVisitor
from .env import Env


"""
No TraitStmt, StructStmt, ImplStmt here
"""


class InterpreterVisitor(NodeVisitor):
    def __init__(self):
        super().__init__()
        self.global_var_dict = {}  # name |-> value
        self.bounded_var_names = []  # stack
        self.stmt_eval_info = []  # [(lineno, info)]

    def _error(self, node: ASTNode, msg: str) -> NoReturn:
        raise ValueError(f"[Line {node.lineno}] Runtime Error: {msg}")
    
    def _log(self, node: ASTNode, msg: str):
        self.stmt_eval_info.append((node.lineno, msg))

    def print_eval_info(self, code: str):
        lines = code.splitlines()
        for lineno, info in self.stmt_eval_info:
            lines[lineno - 1] = f"// {info}\n{lines[lineno - 1]}"
        with open("eval.rs", "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    ###############################################################

    def visit_AssignStmt(self, node: AssignStmt):
        stmt_eval = self.visit(node.expr)
        self.global_var_dict[node.name] = stmt_eval
        self._log(node, f"{stmt_eval}")

    def visit_ExprStmt(self, node: ExprStmt):
        eval = self.visit(node.expr)
        self._log(node, f"{eval}")

    def visit_LambdaExpr(self, node: LambdaExpr):
        self.bounded_var_names.append(node.param_name)
        # Type annotation erasure
        eval = dataclasses.replace(node, body=self.visit(node.body), param_type=None)
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

        return dataclasses.replace(
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

        return dataclasses.replace(
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

        return dataclasses.replace(
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

        return dataclasses.replace(node, expr=eval)

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

        return dataclasses.replace(
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

        return dataclasses.replace(
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
                return _to_value(node, left_eval.value / right_eval.value)
            else:
                self._error(node, f"Unknown operator for MulExpr: {node.op}")

        return dataclasses.replace(
            node,
            left=left_eval,
            right=right_eval,
        )

    def visit_NegExpr(self, node: NegExpr):
        eval = self.visit(node.expr)
        if _is_val(eval):
            return _to_value(node, -eval.value)
        return dataclasses.replace(node, expr=eval)

    def visit_AppExpr(self, node: AppExpr):
        # TODO
        pass

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

        return dataclasses.replace(node, record=record_eval)

    def visit_NamedExpr(self, node: NamedExpr):
        if node.name in self.bounded_var_names:
            return node
        else:
            assert node.name in self.global_var_dict  # Ensured by type checker
            return self.global_var_dict[node.name]

    def visit_ValueExpr(self, node: ValueExpr):
        return node
    
    def visit_ListExpr(self, node: ListExpr):
        return dataclasses.replace(
            node,
            elements=[self.visit(e) for e in node.elements],
        )
    
    def visit_RecordExpr(self, node: RecordExpr):
        return dataclasses.replace(
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
    return ValueExpr(value=value, lineno=expr.lineno)
