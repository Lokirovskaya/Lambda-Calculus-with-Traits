import re
from enum import Enum, auto
from dataclasses import dataclass
from typing import List


class TokenType(Enum):
    NUMBER = auto()
    STRING = auto()
    IDENT = auto()
    COMMENT = auto()
    LPAREN = auto()
    RPAREN = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    LBRACE = auto()
    RBRACE = auto()
    DOT = auto()
    COMMA = auto()
    COLON = auto()
    SEMICOLON = auto()
    ASSIGN = auto()
    ADD = auto()
    SUB = auto()
    MULT = auto()
    DIV = auto()
    MOD = auto()
    ARROW = auto()
    EQ = auto()
    NEQ = auto()
    LT = auto()
    LEQ = auto()
    GT = auto()
    GEQ = auto()
    AND = auto()
    OR = auto()
    NOT = auto()
    TRUE = auto()
    FALSE = auto()
    BACKSLASH = auto()
    AT = auto()
    IF = auto()
    ELSE = auto()
    THEN = auto()
    TRAIT = auto()
    STRUCT = auto()
    IMPL = auto()
    LET = auto()
    IN = auto()
    FOR = auto()
    FORALL = auto()
    TYPE = auto()
    WHITESPACE = auto()
    MISMATCH = auto()
    EOF = auto()


@dataclass(repr=True)
class Token:
    type: TokenType
    value: str
    line: int
    column: int


_token_spec = {
    TokenType.NUMBER: r"\d+(\.\d+)?",
    TokenType.STRING: r'"[^"\n]*"|\'[^\'\n]*\'',
    TokenType.COMMENT: r"//[^\n]*",
    TokenType.ARROW: r"->",
    TokenType.EQ: r"==",
    TokenType.NEQ: r"!=",
    TokenType.LEQ: r"<=",
    TokenType.GEQ: r">=",
    TokenType.LPAREN: r"\(",
    TokenType.RPAREN: r"\)",
    TokenType.LBRACKET: r"\[",
    TokenType.RBRACKET: r"\]",
    TokenType.LBRACE: r"\{",
    TokenType.RBRACE: r"\}",
    TokenType.DOT: r"\.",
    TokenType.COMMA: r",",
    TokenType.COLON: r":",
    TokenType.SEMICOLON: r";",
    TokenType.ASSIGN: r"=",
    TokenType.LT: r"<",
    TokenType.GT: r">",
    TokenType.ADD: r"\+",
    TokenType.SUB: r"-",
    TokenType.MULT: r"\*",
    TokenType.DIV: r"/",
    TokenType.MOD: r"%",
    TokenType.AND: r"&&",
    TokenType.OR: r"\|\|",
    TokenType.NOT: r"!",
    TokenType.BACKSLASH: r"\\",
    TokenType.AT: r"@",
    TokenType.IDENT: r"[a-zA-Z_][a-zA-Z0-9_]*",
    TokenType.WHITESPACE: r"[ \t\r\n]+",
    TokenType.MISMATCH: r".",
}

# 合成正则表达式
_token_regex = "|".join(f"(?P<{tok.name}>{pattern})" for tok, pattern in _token_spec.items())
_master_pattern = re.compile(_token_regex)

_key_words = {
    "true": TokenType.TRUE,
    "false": TokenType.FALSE,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "then": TokenType.THEN,
    "trait": TokenType.TRAIT,
    "struct": TokenType.STRUCT,
    "impl": TokenType.IMPL,
    "let": TokenType.LET,
    "in": TokenType.IN,
    "for": TokenType.FOR,
    "forall": TokenType.FORALL,
    "type": TokenType.TYPE,
}


class TokenStream:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        if len(tokens) == 0:
            self.eof_token = Token(TokenType.EOF, "EOF", 0, 0)
        else:
            self.eof_token = Token(
                TokenType.EOF, "EOF", tokens[-1].line, tokens[-1].column + len(tokens[-1].value)
            )

    def eof(self):
        return self.pos >= len(self.tokens)

    def peek(self):
        if self.eof():
            return self.eof_token
        return self.tokens[self.pos]

    def peek_forward(self, n):
        if self.pos + n >= len(self.tokens) or self.pos + n < 0:
            return self.eof_token
        return self.tokens[self.pos + n]

    def next(self):
        if self.eof():
            return self.eof_token
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def expect(self, *expected_value):
        tok = self.next()
        if tok is None or tok.type not in expected_value:
            expects = ", ".join(f"'{v.name}'" for v in expected_value)
            self.error(tok, f"Expected {expects}, got '{tok.value if tok else 'EOF'}'")
        return tok

    def expect_type(self, expected_type):
        tok = self.next()
        if tok is None or tok.type != expected_type:
            self.error(
                tok, f"Expected token of type '{expected_type}', got '{tok.type if tok else 'EOF'}'"
            )
        return tok

    def match(self, expected_value):
        """If current token matches the value, consume it and return True."""
        tok = self.peek()
        if tok and tok.value == expected_value:
            self.next()
            return True
        return False

    def match_type(self, expected_type):
        tok = self.peek()
        if tok and tok.type == expected_type:
            self.next()
            return tok
        return None

    def error(self, tok, msg):
        if tok:
            raise SyntaxError(f"[Line {tok.line}] Syntax Error: {msg}")
        else:
            raise SyntaxError(f"[End of Input] Syntax Error: {msg}")

    def cur_line(self):
        return self.peek().line


def tokenize(code: str) -> TokenStream:
    tokens = []
    line_num = 1
    line_start = 0

    for mo in _master_pattern.finditer(code):
        kind = mo.lastgroup
        value = mo.group()
        column = mo.start() - line_start + 1  # 从1开始算列

        # 计算行号
        if "\n" in value:
            line_num += value.count("\n")
            line_start = mo.end() - (value[::-1].find("\n"))

        token_type = TokenType[kind]

        if token_type in {TokenType.WHITESPACE, TokenType.COMMENT}:
            continue
        elif token_type == TokenType.MISMATCH:
            raise SyntaxError(f"[Line {line_num}] Syntax Error: Unexpected character {value!r}")
        else:
            if value in _key_words:
                token_type = _key_words[value]
            if token_type == TokenType.STRING:
                value = value[1:-1]
            tokens.append(Token(token_type, value, line_num, column))

    return TokenStream(tokens)
