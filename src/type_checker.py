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
                        | TraitStmt
                        | StructStmt
                        | ImplStmt
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

RelExpr             ::= AddExpr ((">" | "<" | "==" | ">=" | "<=" | "/=") AddExpr)?

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


class TypeCheckerVisitor(NodeVisitor):
    def __init__(self):
        super().__init__()
        self.global_env: Env = Env()
        self.cur_env = self.global_env

    def _error(self, node: ASTNode, msg: str) -> NoReturn:
        raise TypeError(f"[Line {node.lineno}] {msg}")

    def visit_AssignStmt(self, node: AssignStmt):
        self.global_env.set(name=node.name, type=self.visit(node.expr))

    def visit_Expr(self, node: Expr):
        return self.visit(node.expr)

    def visit_LambdaExpr(self, node: LambdaExpr):
        old_env = self.cur_env
        self.cur_env = Env(self.cur_env)
        self.cur_env.set(name=node.param_name, type=node.param_type)

        body_type = self.visit(node.body)

        self.cur_env = old_env
        return ArrowType(node.param_type, body_type, lineno=node.lineno)

    def visit_AppExpr(self, node: AppExpr):
        func_type = self.visit(node.func)
        arg_type = self.visit(node.arg)
        if not isinstance(func_type, ArrowType):
            self._error(node, f"Arrow type expected, got '{func_type}'")

        if func_type.left != arg_type:
            self._error(node, f"Expected '{func_type.left}', got '{arg_type}'")

        return func_type.right
    
    def visit_NamedExpr(self, node: NamedExpr):
        try:
            return self.cur_env.get(node.name)
        except NameError as e:
            self._error(node, e)
        

    def visit_ValueExpr(self, node: ValueExpr):
        value = node.value
        if isinstance(value, bool):
            return NamedType("Bool", lineno=node.lineno)
        elif isinstance(value, int):
            return NamedType("Int", lineno=node.lineno)
        elif isinstance(value, str):
            return NamedType("String", lineno=node.lineno)
        else:
            self._error(value, f"Unknown value type '{type(value)}'")
