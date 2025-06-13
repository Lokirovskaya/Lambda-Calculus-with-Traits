from __future__ import annotations
from dataclasses import dataclass, fields, is_dataclass
from .tokenizer import tokenize, TokenType, TokenStream
from typing import ClassVar


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
                        | TypeLambdaExpr

TypeLambdaExpr      ::= "\\" IDENT "." Expr
                        | IfExpr

IfExpr              ::= "if" Expr "then" Expr "else" Expr
                        | LogicOrExpr

LogicOrExpr         ::= LogicOrExpr "or" LogicAndExpr 
                        | LogicAndExpr

LogicAndExpr        ::= LogicAndExpr "and" LogicNotExpr 
                        | LogicNotExpr

LogicNotExpr        ::= "not" LogicNotExpr
                        | RelExpr

RelExpr             ::= RelExpr (">" | "<" | "==" | ">=" | "<=" | "/=") AddExpr
                        | AddExpr

AddExpr             ::= AddExpr ("+" | "-") MulExpr
                        | MulExpr

MulExpr             ::= MulExpr ("*" | "/") NegExpr
                        | NegExpr

NegExpr             ::= "-" NegExpr
                        | AppExpr

AppExpr|TypeAppExpr ::= AppExpr (TypeAnnotatedExpr | '@' Type)
                        | TypeAnnotatedExpr

TypeAnnotatedExpr   ::= FieldAccessExpr (":" Type)?

FieldAccessExpr     ::= FieldAccessExpr "." IDENT
                        | NamedExpr

NamedExpr           ::= "(" Expr ")"
                        | IDENT
                        | ValueExpr
                        | ListExpr
                        | RecordExpr

ValueExpr           ::= "true" | "false" | INT | STRING

ListExpr            ::= "[" Expr ("," Expr)* "]"

RecordExpr          ::= "{" IDENT "=" Expr ("," Expr "=" Expr)* "}"

                        

Type                ::= ForAllType

ForAllType          ::= "forall" IDENT "." Type
                        | ArrowType

ArrowType           ::= NamedType "->" ArrowType
                        | NamedType

NamedType           ::= "(" Type ")"
                        | IDENT
                        | ListType
                        | RecordType

ListType            ::= "[" Type "]"

RecordType          ::= "{" IDENT ":" Type ("," IDENT ":" Type)* "}"

"""


def parse(code: str):
    tree = Program.parse(tokenize(code))
    with open("ast.txt", "w", encoding="utf-8") as f:
        f.write(tree.pretty_print())
    return tree


@dataclass(kw_only=True)
class ASTNode:
    lineno: int = None

    def pretty_print(self, indent=0) -> str:
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
            return "\n" + val.pretty_print(indent)
        elif isinstance(val, list):
            if not val:
                return "[]"
            return (
                "[\n"
                + "\n".join(
                    (
                        self._indent_line(v.pretty_print(indent + 1))
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

    def wrap(self, arg: Expr) -> str:
        assert isinstance(arg, Expr), f"Expected Expr, got {type(arg)}"
        arg_prec = type(arg).precedence
        self_prec = type(self).precedence
        s = str(arg)
        if arg_prec < self_prec:
            return f"({s})"
        else:
            return str(s)


@dataclass
class LambdaExpr(Expr):
    param_name: str
    param_type: Type
    body: Expr
    precedence: ClassVar[int] = 0

    @classmethod
    def parse(cls, tokens: TokenStream):
        lineno = tokens.cur_line()
        if (
            tokens.peek().type == TokenType.BACKSLASH
            and tokens.peek_forward(2).type == TokenType.COLON
        ):
            tokens.expect(TokenType.BACKSLASH)
            param_name = tokens.expect(TokenType.IDENT).value
            tokens.expect(TokenType.COLON)
            param_type = Type.parse(tokens)
            tokens.expect(TokenType.DOT)
            body = Expr.parse(tokens)
            return LambdaExpr(param_name, param_type, body, lineno=lineno)
        else:
            return TypeLambdaExpr.parse(tokens)

    def __str__(self):
        if self.param_type is None:  # Erased type
            return f"\\{self.param_name}: _. {self.body}"
        else:
            return f"\\{self.param_name}: {self.param_type}. {self.body}"


@dataclass
class TypeLambdaExpr(Stmt):
    param_name: str
    body: Expr
    precedence: ClassVar[int] = 0

    @classmethod
    def parse(cls, tokens: TokenStream):
        lineno = tokens.cur_line()
        if (
            tokens.peek().type == TokenType.BACKSLASH
            and tokens.peek_forward(2).type == TokenType.DOT
        ):
            tokens.expect(TokenType.BACKSLASH)
            param_name = tokens.expect(TokenType.IDENT).value
            tokens.expect(TokenType.DOT)
            body = Expr.parse(tokens)
            return TypeLambdaExpr(param_name, body, lineno=lineno)
        else:
            return IfExpr.parse(tokens)

    def __str__(self):
        return f"\\{self.param_name}. {self.body}"


@dataclass
class IfExpr(Expr):
    condition: Expr
    then_expr: Expr
    else_expr: Expr
    precedence: ClassVar[int] = 1

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

    def __str__(self):
        return f"if {self.wrap(self.condition)} then {self.wrap(self.then_expr)} else {self.wrap(self.else_expr)}"


@dataclass
class LogicOrExpr(Expr):
    left: Expr
    right: Expr
    precedence: ClassVar[int] = 2

    @classmethod
    def parse(cls, tokens: TokenStream):
        lineno = tokens.cur_line()
        left = LogicAndExpr.parse(tokens)
        while tokens.peek().type == TokenType.OR:
            tokens.expect(TokenType.OR)
            right = LogicAndExpr.parse(tokens)
            left = LogicOrExpr(left, right, lineno=lineno)
        return left

    def __str__(self):
        return f"{self.wrap(self.left)} or {self.wrap(self.right)}"


@dataclass
class LogicAndExpr(Expr):
    left: Expr
    right: Expr
    precedence: ClassVar[int] = 3

    @classmethod
    def parse(cls, tokens: TokenStream):
        lineno = tokens.cur_line()
        left = LogicNotExpr.parse(tokens)
        while tokens.peek().type == TokenType.AND:
            tokens.expect(TokenType.AND)
            right = LogicNotExpr.parse(tokens)
            left = LogicAndExpr(left, right, lineno=lineno)
        return left

    def __str__(self):
        return f"{self.wrap(self.left)} and {self.wrap(self.right)}"


@dataclass
class LogicNotExpr(Expr):
    expr: Expr
    precedence: ClassVar[int] = 4

    @classmethod
    def parse(cls, tokens: TokenStream):
        lineno = tokens.cur_line()
        if tokens.peek().type == TokenType.NOT:
            tokens.expect(TokenType.NOT)
            term = LogicNotExpr.parse(tokens)
            return LogicNotExpr(term, lineno=lineno)
        else:
            return RelExpr.parse(tokens)

    def __str__(self):
        return f"not {self.wrap(self.expr)}"


@dataclass
class RelExpr(Expr):
    left: Expr
    op: str
    right: Expr
    precedence: ClassVar[int] = 5

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
        while tokens.peek().type in ops:
            op = tokens.expect(*ops).value
            right = AddExpr.parse(tokens)
            left = RelExpr(left, op, right, lineno=lineno)
        return left

    def __str__(self):
        return f"{self.wrap(self.left)} {self.op} {self.wrap(self.right)}"


@dataclass
class AddExpr(Expr):
    left: Expr
    op: str
    right: Expr
    precedence: ClassVar[int] = 6

    @classmethod
    def parse(cls, tokens: TokenStream):
        lineno = tokens.cur_line()
        ops = (TokenType.ADD, TokenType.SUB)
        left = MulExpr.parse(tokens)
        while tokens.peek().type in ops:
            op = tokens.expect(*ops).value
            right = MulExpr.parse(tokens)
            left = AddExpr(left, op, right, lineno=lineno)
        return left

    def __str__(self):
        return f"{self.wrap(self.left)} {self.op} {self.wrap(self.right)}"


@dataclass
class MulExpr(Expr):
    left: Expr
    op: str
    right: Expr
    precedence: ClassVar[int] = 7

    @classmethod
    def parse(cls, tokens: TokenStream):
        lineno = tokens.cur_line()
        ops = (TokenType.MULT, TokenType.DIV)
        left = NegExpr.parse(tokens)
        while tokens.peek().type in ops:
            op = tokens.expect(*ops).value
            right = NegExpr.parse(tokens)
            left = MulExpr(left, op, right, lineno=lineno)
        return left

    def __str__(self):
        return f"{self.wrap(self.left)} {self.op} {self.wrap(self.right)}"


@dataclass
class NegExpr(Expr):
    expr: Expr
    precedence: ClassVar[int] = 8

    @classmethod
    def parse(cls, tokens: TokenStream):
        lineno = tokens.cur_line()
        if tokens.peek().type == TokenType.SUB:
            tokens.expect(TokenType.SUB)
            expr = NegExpr.parse(tokens)
            return NegExpr(expr, lineno=lineno)
        else:
            return AppExpr.parse(tokens)

    def __str__(self):
        return f"-{self.wrap(self.expr)}"


_named_expr_start = {
    TokenType.IDENT,
    TokenType.NUMBER,
    TokenType.STRING,
    TokenType.TRUE,
    TokenType.FALSE,
    TokenType.LPAREN,
    TokenType.LBRACKET,
    TokenType.LBRACE,
}


@dataclass
class AppExpr(Expr):
    func: Expr
    arg: Expr
    precedence: ClassVar[int] = 9

    @classmethod
    def parse(cls, tokens: TokenStream):
        lineno = tokens.cur_line()
        func = TypeAnnotatedExpr.parse(tokens)
        while True:
            if tokens.peek().type in _named_expr_start:
                arg = TypeAnnotatedExpr.parse(tokens)
                func = AppExpr(func, arg, lineno=lineno)
            elif tokens.peek().type == TokenType.AT:
                tokens.expect(TokenType.AT)
                type_arg = Type.parse(tokens)
                func = TypeAppExpr(func, type_arg, lineno=lineno)
            else:
                break
        return func

    def __str__(self):
        return f"{self.wrap(self.func)} {self.wrap(self.arg)}"


@dataclass
class TypeAppExpr(Expr):
    func: Expr
    type_arg: Type
    precedence: ClassVar[int] = 9

    def __str__(self):
        return f"{self.wrap(self.func)} @{self.type_arg}"


@dataclass
class TypeAnnotatedExpr(Expr):
    expr: Expr
    type: Type
    precedence: ClassVar[int] = 9

    @classmethod
    def parse(cls, tokens: TokenStream):
        lineno = tokens.cur_line()
        expr = FieldAccessExpr.parse(tokens)
        if tokens.peek().type == TokenType.COLON:
            tokens.expect(TokenType.COLON)
            type = Type.parse(tokens)
            return TypeAnnotatedExpr(expr, type, lineno=lineno)
        else:
            return expr

    def __str__(self):
        return f"{self.wrap(self.expr)}: {self.type}"


@dataclass
class FieldAccessExpr(Expr):
    record: Expr
    field_name: str
    precedence: ClassVar[int] = 10

    @classmethod
    def parse(cls, tokens: TokenStream):
        lineno = tokens.cur_line()
        record = NamedExpr.parse(tokens)
        while tokens.peek().type == TokenType.DOT:
            tokens.expect(TokenType.DOT)
            field_name = tokens.expect(TokenType.IDENT).value
            record = FieldAccessExpr(record, field_name, lineno=lineno)
        return record

    def __str__(self):
        return f"{self.wrap(self.record)}.{self.field_name}"


@dataclass
class NamedExpr(Expr):
    name: str
    precedence: ClassVar[int] = 11

    @classmethod
    def parse(cls, tokens: TokenStream):
        lineno = tokens.cur_line()
        if tokens.peek().type == TokenType.IDENT:
            value = tokens.expect(TokenType.IDENT).value
            return NamedExpr(value, lineno=lineno)

        elif tokens.peek().type == TokenType.NUMBER:
            value = int(tokens.expect(TokenType.NUMBER).value)
            return ValueExpr(value, lineno=lineno)
        elif tokens.peek().type == TokenType.STRING:
            value = tokens.expect(TokenType.STRING).value
            return ValueExpr(value, lineno=lineno)
        elif tokens.peek().type == TokenType.TRUE:
            tokens.expect(TokenType.TRUE)
            return ValueExpr(True, lineno=lineno)
        elif tokens.peek().type == TokenType.FALSE:
            tokens.expect(TokenType.FALSE)
            return ValueExpr(False, lineno=lineno)

        elif tokens.peek().type == TokenType.LPAREN:
            tokens.expect(TokenType.LPAREN)
            expr = Expr.parse(tokens)
            tokens.expect(TokenType.RPAREN)
            return expr
        elif tokens.peek().type == TokenType.LBRACKET:
            return ListExpr.parse(tokens)
        elif tokens.peek().type == TokenType.LBRACE:
            return RecordExpr.parse(tokens)
        else:
            tokens.expect(*_named_expr_start)

    def __str__(self):
        return self.name


@dataclass
class ValueExpr(Expr):
    value: str | int | bool
    precedence: ClassVar[int] = 11

    def __str__(self):
        return str(self.value)


@dataclass
class ListExpr(Expr):
    elements: list[Expr]
    precedence: ClassVar[int] = 11

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

    def __str__(self):
        return f"[{', '.join(map(str, self.elements))}]"


@dataclass
class RecordExpr(Expr):
    fields: dict[str, Expr]
    precedence: ClassVar[int] = 11

    @classmethod
    def parse(cls, tokens: TokenStream):
        lineno = tokens.cur_line()
        tokens.expect(TokenType.LBRACE)
        fields = {}
        while tokens.peek().type != TokenType.RBRACE:
            field_name = tokens.expect(TokenType.IDENT).value
            if field_name in fields:
                tokens.error(tokens.peek_forward(-1), f"Duplicate field name: {field_name}")
            tokens.expect(TokenType.ASSIGN)
            field_value = Expr.parse(tokens)
            fields[field_name] = field_value
            if tokens.peek().type == TokenType.COMMA:
                tokens.expect(TokenType.COMMA)
        tokens.expect(TokenType.RBRACE)
        return RecordExpr(fields, lineno=lineno)

    def __str__(self):
        return f"{{{', '.join(f'{name} = {value}' for name, value in self.fields.items())}}}"


@dataclass
class Type(ASTNode):
    @classmethod
    def parse(cls, tokens: TokenStream):
        return ForAllType.parse(tokens)


@dataclass
class ForAllType(Type):
    param_name: str
    body: Type

    @classmethod
    def parse(cls, tokens: TokenStream):
        lineno = tokens.cur_line()
        if tokens.peek().type == TokenType.FORALL:
            tokens.expect(TokenType.FORALL)
            param_name = tokens.expect(TokenType.IDENT).value
            tokens.expect(TokenType.DOT)
            body = Type.parse(tokens)
            return ForAllType(param_name, body, lineno=lineno)
        else:
            return ArrowType.parse(tokens)

    def __str__(self):
        param_name = self.param_name
        body = str(self.body)
        return f"forall {param_name}. {body}"

    def __eq__(self, other):
        return (
            isinstance(other, ForAllType)
            and self.param_name == other.param_name
            and self.body == other.body
        )

    def __hash__(self):
        return hash((self.param_name, self.body))


@dataclass
class ArrowType(Type):
    left: Type
    right: Type

    @classmethod
    def parse(cls, tokens: TokenStream):
        lineno = tokens.cur_line()
        left = NamedType.parse(tokens)
        if tokens.peek().type == TokenType.ARROW:
            tokens.expect(TokenType.ARROW)
            right = ArrowType.parse(tokens)
            return ArrowType(left, right, lineno=lineno)
        else:
            return left

    def __str__(self):
        left = str(self.left)
        right = str(self.right)
        if isinstance(self.left, (ArrowType, ForAllType)):
            left = f"({left})"
        if isinstance(self.right, ForAllType):
            right = f"({right})"
        return f"{left} -> {right}"

    def __eq__(self, other):
        return (
            isinstance(other, ArrowType) and self.left == other.left and self.right == other.right
        )

    def __hash__(self):
        return hash((self.left, self.right))


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

    def __str__(self):
        return self.name

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

    def __str__(self):
        return f"[{self.elem_type}]"

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
                tokens.error(tokens.peek_forward(-1), f"Duplicate field name: {field_name}")
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

    def __str__(self):
        return "{" + ", ".join(f"{name}: {type}" for name, type in self.sorted_fields) + "}"

    def __eq__(self, other):
        return isinstance(other, RecordType) and self.sorted_fields == other.sorted_fields

    def __hash__(self):
        return hash(tuple(self.sorted_fields))
