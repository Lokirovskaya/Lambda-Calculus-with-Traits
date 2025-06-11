from src.parser import parse, ValueExpr
from src.visitor import NodeVisitor

code = open("code.txt", "r", encoding="utf-8").read()
out = open("out.ast", "w", encoding="utf-8")

tree = parse(code)
print(tree, file=out)

from src.type_checker import TypeCheckerVisitor

tc = TypeCheckerVisitor()
tc.visit(tree)