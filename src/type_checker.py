from typing import NoReturn

from .parser import *
from .visitor import NodeVisitor
from .env import Env


"""
No TraitStmt, StructStmt, ImplStmt here
"""


"""
Program             ::= Statement*

Statement           ::= AssignStmt
                        | ExprStmt
                        | ;

AssignStmt          ::= IDENT "=" Expr ";"

ExprStmt            ::= Expr ";"


Expr                ::= LambdaExpr

LambdaExpr          ::= "\\" IDENT ":" Type "." Expr
                        | IfExpr

IfExpr              ::= "if" Expr "then" Expr "else" Expr
                        | LogicOrExpr

LogicOrExpr         ::= LogicAndExpr "or" LogicOrExpr

LogicAndExpr        ::= LogicNotExpr "and" LogicAndExpr

LogicNotExpr        ::= "not" LogicNotExpr
                        | RelExpr

RelExpr             ::= AddExpr ((">" | "<" | "==" | ">=" | "<=" | "!=") AddExpr)?

AddExpr             ::= MulExpr ("+" | "-") AddExpr

MulExpr             ::= AppExpr (("*" | "/") MulExpr

AppExpr             ::= TypeAnnotatedExpr AppExpr

TypeAnnotatedExpr   ::= NamedExpr (":" Type)?

NamedExpr           ::= "(" Expr ")"
                        | IDENT
                        | ValueExpr
                        | ListExpr
                        | RecordExpr

ValueExpr           ::= "true" | "false" | INT | STRING

ListExpr            ::= "[" Expr ("," Expr)* "]"

RecordExpr          ::= "{" IDENT "=" Expr ("," Expr "=" Expr)* "}"

                        

Type                ::= ArrowType

ArrowType           ::= AppType ("->" ArrowType)?

AppType             ::= NamedType AppType

NamedType            ::= "(" Type ")"
                        | IDENT
                        | ListType
                        | RecordType

ListType            ::= "[" Type "]"

RecordType          ::= "{" IDENT ":" Type ("," IDENT ":" Type)* "}"

"""

BoolType = NamedType("Bool")
IntType = NamedType("Int")
StringType = NamedType("String")


class TypeCheckerVisitor(NodeVisitor):
    def __init__(self):
        super().__init__()
        self.global_env: Env = Env()
        self.cur_env = self.global_env
        self.log_handle = open("type.txt", "w", encoding="utf-8")

    def _error(self, node: ASTNode, msg: str) -> NoReturn:
        raise TypeError(f"[Line {node.lineno}, Node {node.__class__.__name__}] {msg}")

    def _log(self, node: ASTNode, msg: str):
        self.log_handle.write(f"[Line {node.lineno}] {msg}\n")

    def visit_AssignStmt(self, node: AssignStmt):
        stmt_type = self.visit(node.expr)
        self._log(node, f"{node.name}: {stmt_type}")
        self.global_env.set(name=node.name, type=stmt_type)

    def visit_ExprStmt(self, node: ExprStmt):
        stmt_type = self.visit(node.expr)
        self._log(node, f"{stmt_type}")

    def visit_Expr(self, node: Expr):
        return self.visit(node.expr)

    def visit_LambdaExpr(self, node: LambdaExpr):
        old_env = self.cur_env
        self.cur_env = Env(self.cur_env)
        self.cur_env.set(name=node.param_name, type=node.param_type)

        body_type = self.visit(node.body)

        self.cur_env = old_env
        return ArrowType(node.param_type, body_type)

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

    def visit_AppExpr(self, node: AppExpr):
        func_type = self.visit(node.func)
        arg_type = self.visit(node.arg)
        if not isinstance(func_type, ArrowType):
            self._error(node, f"Arrow type expected, got '{func_type}'")

        if func_type.left != arg_type:
            self._error(node, f"Expected '{func_type.left}', got '{arg_type}'")

        return func_type.right

    def visit_TypeAnnotatedExpr(self, node: TypeAnnotatedExpr):
        expr_type = self.visit(node.expr)
        if expr_type != node.type:
            self._error(node, f"Annotated type '{node.type}', got '{expr_type}'")
        return expr_type

    def visit_NamedExpr(self, node: NamedExpr):
        try:
            return self.cur_env.get(node.name)
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
        if len(node.values) == 0:
            return ListType(None)  # Todo

        first_type = self.visit(node.values[0])
        for value in node.values[1:]:
            value_type = self.visit(value)
            if first_type != value_type:
                self._error(value, f"Expected '{first_type}', got '{value_type}'")

        return ListType(first_type)

    def visit_RecordExpr(self, node: RecordExpr):
        record_type = {label: self.visit(value) for label, value in node.fields}
        return record_type
