from __future__ import annotations
from dataclasses import dataclass, fields, is_dataclass
from .tokenizer import tokenize, TokenType, TokenStream

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

TraitStmt           ::= "trait" IDENT IDENT+ "where" TypeBindItem* "end"

StructStmt          ::= "struct" IDENT "where" TypeBindItem* "end"

ImplStmt            ::= "impl" IDENT "for" Type "where" ImplItem* "end"

TypeBindItem        ::= IDENT ":" Type ";"

AssignItem          ::= IDENT "=" Expr ";"



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


def parse(code: str):
    return Program.parse(tokenize(code))


@dataclass(kw_only=True)
class ASTNode:
    lineno: int

    def pretty_printer(self, indent=0) -> str:
        pad = "  " * indent
        cls_name = self.__class__.__name__
        result = f"{pad}{cls_name}"

        if not is_dataclass(self):
            return result

        for field in fields(self):
            value = getattr(self, field.name)
            result += f"\n{pad}  {field.name}: {self._format_value(value, indent + 2)}"

        return result

    def _format_value(self, val, indent: int) -> str:
        if isinstance(val, ASTNode):
            return "\n" + val._pretty(indent)
        elif isinstance(val, list):
            if not val:
                return "[]"
            return (
                "[\n"
                + "\n".join(
                    (
                        self._indent_line(v._pretty(indent + 1))
                        if isinstance(v, ASTNode)
                        else self._indent_line(str(v), indent + 1)
                    )
                    for v in val
                )
                + "\n"
                + "  " * indent
                + "]"
            )
        else:
            return str(val)

    def _indent_line(self, text: str, indent: int = 0) -> str:
        pad = "  " * indent
        return "\n".join(pad + line for line in text.splitlines())


@dataclass
class Program(ASTNode):
    statements: list[Stmt]

    @classmethod
    def parse(cls, tokens: TokenStream):
        lineno = tokens.cur_line()
        statements = []
        while not tokens.eof():
            while tokens.peek().type == TokenType.SEMICOLON:
                tokens.next()
            statements.append(Stmt.parse(tokens))
        return Program(statements, lineno=lineno)


@dataclass
class Stmt(ASTNode):
    @classmethod
    def parse(cls, tokens: TokenStream):
        if tokens.peek().type == TokenType.TRAIT:
            return TraitStmt.parse(tokens)
        elif tokens.peek().type == TokenType.STRUCT:
            return StructStmt.parse(tokens)
        elif tokens.peek().type == TokenType.IMPL:
            return ImplStmt.parse(tokens)
        elif (
            tokens.peek().type == TokenType.IDENT
            and tokens.peek_forward(1).type == TokenType.ASSIGN
        ):
            return AssignStmt.parse(tokens)
        else:
            return ExprStmt.parse(tokens)


@dataclass
class AssignStmt(Stmt):
    name: str
    expr: Expr

    @classmethod
    def parse(cls, tokens: TokenStream):
        lineno = tokens.cur_line()
        name = tokens.expect(TokenType.IDENT).value
        tokens.expect(TokenType.ASSIGN)
        value = Expr.parse(tokens)
        tokens.expect(TokenType.SEMICOLON)
        return AssignStmt(name, value, lineno=lineno)


@dataclass
class ExprStmt(Stmt):
    expr: Expr

    @classmethod
    def parse(cls, tokens: TokenStream):
        lineno = tokens.cur_line()
        expr = Expr.parse(tokens)
        tokens.expect(TokenType.SEMICOLON)
        return ExprStmt(expr, lineno=lineno)


@dataclass
class TraitStmt(Stmt):
    name: str
    type_params: list[str]
    items: list[TypeBindItem]

    @classmethod
    def parse(cls, tokens: TokenStream):
        lineno = tokens.cur_line()
        tokens.expect(TokenType.TRAIT)
        name = tokens.expect(TokenType.IDENT).value
        type_params = []
        while tokens.peek().type == TokenType.IDENT:
            type_params.append(tokens.expect(TokenType.IDENT).value)
        tokens.expect(TokenType.WHERE)
        items = []
        while tokens.peek().type != TokenType.END:
            items.append(TypeBindItem.parse(tokens))
        tokens.expect(TokenType.END)
        return TraitStmt(name, type_params, items, lineno=lineno)


@dataclass
class StructStmt(Stmt):
    name: str
    items: list[TypeBindItem]

    @classmethod
    def parse(cls, tokens: TokenStream):
        lineno = tokens.cur_line()
        tokens.expect(TokenType.STRUCT)
        name = tokens.expect(TokenType.IDENT).value
        tokens.expect(TokenType.WHERE)
        items = []
        while tokens.peek().type != TokenType.END:
            items.append(TypeBindItem.parse(tokens))
        tokens.expect(TokenType.END)
        return StructStmt(name, items, lineno=lineno)


@dataclass
class ImplStmt(Stmt):
    name: str
    type_param: Type
    items: list[AssignItem]

    @classmethod
    def parse(cls, tokens: TokenStream):
        lineno = tokens.cur_line()
        tokens.expect(TokenType.IMPL)
        name = tokens.expect(TokenType.IDENT).value
        tokens.expect(TokenType.FOR)
        type_param = Type.parse(tokens)
        tokens.expect(TokenType.WHERE)
        items = []
        while tokens.peek().type != TokenType.END:
            items.append(AssignItem.parse(tokens))
        tokens.expect(TokenType.END)
        return ImplStmt(name, type_param, items, lineno=lineno)


@dataclass
class TypeBindItem(ASTNode):
    name: str
    type: Type

    @classmethod
    def parse(cls, tokens: TokenStream):
        lineno = tokens.cur_line()
        name = tokens.expect(TokenType.IDENT).value
        tokens.expect(TokenType.COLON)
        type = Type.parse(tokens)
        tokens.expect(TokenType.SEMICOLON)
        return TypeBindItem(name, type, lineno=lineno)


@dataclass
class AssignItem(ASTNode):
    name: str
    value: Expr

    @classmethod
    def parse(cls, tokens: TokenStream):
        lineno = tokens.cur_line()
        name = tokens.expect(TokenType.IDENT).value
        tokens.expect(TokenType.ASSIGN)
        value = Expr.parse(tokens)
        tokens.expect(TokenType.SEMICOLON)
        return AssignItem(name, value, lineno=lineno)


@dataclass
class Expr(ASTNode):
    @classmethod
    def parse(cls, tokens: TokenStream):
        return LambdaExpr.parse(tokens)


@dataclass
class LambdaExpr(Expr):
    param_name: str
    param_type: Type
    body: Expr

    @classmethod
    def parse(cls, tokens: TokenStream):
        lineno = tokens.cur_line()
        if tokens.peek().type == TokenType.BACKSLASH:
            tokens.expect(TokenType.BACKSLASH)
            param_name = tokens.expect(TokenType.IDENT).value
            tokens.expect(TokenType.COLON)
            param_type = Type.parse(tokens)
            tokens.expect(TokenType.DOT)
            body = Expr.parse(tokens)
            return LambdaExpr(param_name, param_type, body, lineno=lineno)
        else:
            return IfExpr.parse(tokens)


@dataclass
class IfExpr(Expr):
    condition: Expr
    then_expr: Expr
    else_expr: Expr

    @classmethod
    def parse(cls, tokens: TokenStream):
        lineno = tokens.cur_line()
        if tokens.peek().type == TokenType.IF:
            tokens.expect(TokenType.IF)
            condition = Expr.parse(tokens)
            tokens.expect(TokenType.THEN)
            then_expr = Expr.parse(tokens)
            tokens.expect(TokenType.ELSE)
            else_expr = Expr.parse(tokens)
            return IfExpr(condition, then_expr, else_expr, lineno=lineno)
        else:
            return LogicOrExpr.parse(tokens)


@dataclass
class LogicOrExpr(Expr):
    left: Expr
    right: Expr

    @classmethod
    def parse(cls, tokens: TokenStream):
        lineno = tokens.cur_line()
        left = LogicAndExpr.parse(tokens)
        if tokens.peek().type == TokenType.OR:
            tokens.expect(TokenType.OR)
            right = LogicOrExpr.parse(tokens)
            return LogicOrExpr(left, right, lineno=lineno)
        else:
            return left


@dataclass
class LogicAndExpr(Expr):
    left: Expr
    right: Expr

    @classmethod
    def parse(cls, tokens: TokenStream):
        lineno = tokens.cur_line()
        left = LogicNotExpr.parse(tokens)
        if tokens.peek().type == TokenType.AND:
            tokens.expect(TokenType.AND)
            right = LogicAndExpr.parse(tokens)
            return LogicAndExpr(left, right, lineno=lineno)
        else:
            return left


@dataclass
class LogicNotExpr(Expr):
    term: Expr

    @classmethod
    def parse(cls, tokens: TokenStream):
        lineno = tokens.cur_line()
        if tokens.peek().type == TokenType.NOT:
            tokens.expect(TokenType.NOT)
            term = LogicNotExpr.parse(tokens)
            return LogicNotExpr(term, lineno=lineno)
        else:
            return RelExpr.parse(tokens)


@dataclass
class RelExpr(Expr):
    left: Expr
    op: str
    right: Expr

    @classmethod
    def parse(cls, tokens: TokenStream):
        lineno = tokens.cur_line()
        ops = (
            TokenType.GT,
            TokenType.LT,
            TokenType.GEQ,
            TokenType.LEQ,
            TokenType.EQ,
            TokenType.NEQ,
        )
        left = AddExpr.parse(tokens)
        if tokens.peek().type in ops:
            op = tokens.expect(*ops).value
            right = AddExpr.parse(tokens)
            return RelExpr(left, op, right, lineno=lineno)
        else:
            return left


@dataclass
class AddExpr(Expr):
    left: Expr
    op: str
    right: Expr

    @classmethod
    def parse(cls, tokens: TokenStream):
        lineno = tokens.cur_line()
        left = MulExpr.parse(tokens)
        if tokens.peek().type in (TokenType.ADD, TokenType.SUB):
            op = tokens.expect(TokenType.ADD, TokenType.SUB).value
            right = AddExpr.parse(tokens)
            return AddExpr(left, op, right, lineno=lineno)
        else:
            return left


@dataclass
class MulExpr(Expr):
    left: Expr
    op: str
    right: Expr

    @classmethod
    def parse(cls, tokens: TokenStream):
        lineno = tokens.cur_line()
        left = AppExpr.parse(tokens)
        if tokens.peek().type in (TokenType.MULT, TokenType.DIV):
            op = tokens.expect(TokenType.MULT, TokenType.DIV).value
            right = MulExpr.parse(tokens)
            return MulExpr(left, op, right, lineno=lineno)
        else:
            return left


_named_expr_start = (
    TokenType.IDENT,
    TokenType.NUMBER,
    TokenType.LPAREN,
    TokenType.STRING,
    TokenType.LBRACKET,
    TokenType.LBRACE,
    TokenType.TRUE,
    TokenType.FALSE,
)


@dataclass
class AppExpr(Expr):
    func: Expr
    arg: Expr

    @classmethod
    def parse(cls, tokens: TokenStream):
        lineno = tokens.cur_line()
        func = TypeAnnotatedExpr.parse(tokens)
        if tokens.peek().type in _named_expr_start:
            arg = AppExpr.parse(tokens)
            return AppExpr(func, arg, lineno=lineno)
        else:
            return func


@dataclass
class TypeAnnotatedExpr(Expr):
    expr: Expr
    type: Type

    @classmethod
    def parse(cls, tokens: TokenStream):
        lineno = tokens.cur_line()
        expr = NamedExpr.parse(tokens)
        if tokens.peek().type == TokenType.COLON:
            tokens.expect(TokenType.COLON)
            type = Type.parse(tokens)
            return TypeAnnotatedExpr(expr, type, lineno=lineno)
        else:
            return expr


@dataclass
class NamedExpr(Expr):
    name: str

    @classmethod
    def parse(cls, tokens: TokenStream):
        lineno = tokens.cur_line()
        if tokens.peek().type == TokenType.IDENT:
            value = tokens.expect(TokenType.IDENT).value
            return NamedExpr(value, lineno=lineno)
        elif tokens.peek().type == TokenType.NUMBER:
            value = int(tokens.expect(TokenType.NUMBER).value)
            return ValueExpr(value, lineno=lineno)
        elif tokens.peek().type == TokenType.LPAREN:
            tokens.expect(TokenType.LPAREN)
            expr = Expr.parse(tokens)
            tokens.expect(TokenType.RPAREN)
            return expr
        elif tokens.peek().type == TokenType.STRING:
            value = tokens.expect(TokenType.STRING).value
            return ValueExpr(value, lineno=lineno)
        elif tokens.peek().type == TokenType.LBRACKET:
            return ListExpr.parse(tokens)
        elif tokens.peek().type == TokenType.LBRACE:
            return RecordExpr.parse(tokens)
        elif tokens.peek().type == TokenType.TRUE:
            tokens.expect(TokenType.TRUE)
            return ValueExpr(True, lineno=lineno)
        elif tokens.peek().type == TokenType.FALSE:
            tokens.expect(TokenType.FALSE)
            return ValueExpr(False, lineno=lineno)
        else:
            tokens.expect(_named_expr_start)


@dataclass
class ValueExpr(Expr):
    value: str | int | bool


@dataclass
class ListExpr(Expr):
    elements: list[Expr]

    @classmethod
    def parse(cls, tokens: TokenStream):
        lineno = tokens.cur_line()
        tokens.expect(TokenType.LBRACKET)
        elements = []
        while tokens.peek().type != TokenType.RBRACKET:
            elements.append(Expr.parse(tokens))
            if tokens.peek().type == TokenType.COMMA:
                tokens.expect(TokenType.COMMA)
        tokens.expect(TokenType.RBRACKET)
        return ListExpr(elements, lineno=lineno)


@dataclass
class RecordExpr(Expr):
    fields: dict[str, Expr]

    @classmethod
    def parse(cls, tokens: TokenStream):
        lineno = tokens.cur_line()
        tokens.expect(TokenType.LBRACE)
        fields = {}
        while tokens.peek().type != TokenType.RBRACE:
            field_name = tokens.expect(TokenType.IDENT).value
            if field_name in fields:
                raise tokens.error(tokens.peek_forward(-1), f"Duplicate field name: {field_name}")
            tokens.expect(TokenType.ASSIGN)
            field_value = Expr.parse(tokens)
            fields[field_name] = field_value
            if tokens.peek().type == TokenType.COMMA:
                tokens.expect(TokenType.COMMA)
        tokens.expect(TokenType.RBRACE)
        return RecordExpr(fields, lineno=lineno)


@dataclass
class Type(ASTNode):
    @classmethod
    def parse(cls, tokens: TokenStream):
        return ArrowType.parse(tokens)


@dataclass
class ArrowType(Type):
    left: Type
    right: Type

    @classmethod
    def parse(cls, tokens: TokenStream):
        lineno = tokens.cur_line()
        left = AppType.parse(tokens)
        if tokens.peek().type == TokenType.ARROW:
            tokens.expect(TokenType.ARROW)
            right = ArrowType.parse(tokens)
            return ArrowType(left, right, lineno=lineno)
        else:
            return left

    def __eq__(self, other):
        return (
            isinstance(other, ArrowType) and self.left == other.left and self.right == other.right
        )

    def __hash__(self):
        return hash((self.left, self.right))


@dataclass
class AppType(Type):
    func: Type
    arg: Type

    @classmethod
    def parse(cls, tokens: TokenStream):
        lineno = tokens.cur_line()
        func = NamedType.parse(tokens)
        if tokens.peek().type in (
            TokenType.LPAREN,
            TokenType.IDENT,
            TokenType.LBRACKET,
            TokenType.LBRACE,
        ):
            arg = AppType.parse(tokens)
            return AppType(func, arg, lineno=lineno)
        else:
            return func

    def __eq__(self, other):
        return isinstance(other, AppType) and self.func == other.func and self.arg == other.arg

    def __hash__(self):
        return hash((self.func, self.arg))


@dataclass
class NamedType(Type):
    name: str

    @classmethod
    def parse(cls, tokens: TokenStream):
        lineno = tokens.cur_line()
        if tokens.peek().type == TokenType.IDENT:
            name = tokens.expect(TokenType.IDENT).value
            return NamedType(name, lineno=lineno)
        elif tokens.peek().type == TokenType.LPAREN:
            tokens.expect(TokenType.LPAREN)
            type = Type.parse(tokens)
            tokens.expect(TokenType.RPAREN)
            return type
        elif tokens.peek().type == TokenType.LBRACKET:
            return ListType.parse(tokens)
        elif tokens.peek().type == TokenType.LBRACE:
            return RecordType.parse(tokens)
        else:
            tokens.expect(TokenType.IDENT, TokenType.LPAREN, TokenType.LBRACKET, TokenType.LBRACE)

    def __eq__(self, other):
        return isinstance(other, NamedType) and self.name == other.name

    def __hash__(self):
        return hash(self.name)


@dataclass
class ListType(Type):
    elem_type: Type

    @classmethod
    def parse(cls, tokens: TokenStream):
        lineno = tokens.cur_line()
        tokens.expect(TokenType.LBRACKET)
        elem_type = Type.parse(tokens)
        tokens.expect(TokenType.RBRACKET)
        return ListType(elem_type, lineno=lineno)

    def __eq__(self, other):
        return isinstance(other, ListType) and self.elem_type == other.elem_type

    def __hash__(self):
        return hash(self.elem_type)


@dataclass
class RecordType(Type):
    fields: dict[str, Type]

    @classmethod
    def parse(cls, tokens: TokenStream):
        lineno = tokens.cur_line()
        tokens.expect(TokenType.LBRACE)
        fields = {}
        while tokens.peek().type != TokenType.RBRACE:
            field_name = tokens.expect(TokenType.IDENT).value
            if field_name in fields:
                raise tokens.error(tokens.peek_forward(-1), f"Duplicate field name: {field_name}")
            tokens.expect(TokenType.COLON)
            field_type = Type.parse(tokens)
            fields[field_name] = field_type
            if tokens.peek().type == TokenType.COMMA:
                tokens.expect(TokenType.COMMA)
        tokens.expect(TokenType.RBRACE)
        return RecordType(fields, lineno=lineno)

    @property
    def sorted_fields(self):
        return sorted(self.fields.items())

    def __eq__(self, other):
        return isinstance(other, RecordType) and self.sorted_fields == other.sorted_fields

    def __hash__(self):
        return hash(tuple(self.sorted_fields))
