from src.parser import parse, ValueExpr
from src.visitor import NodeVisitor

code = open("code.rs", "r", encoding="utf-8").read()

tree = parse(code)

from src.type_checker import TypeCheckerVisitor

tc = TypeCheckerVisitor()
tc.visit(tree)
tc.print_type_info(code)