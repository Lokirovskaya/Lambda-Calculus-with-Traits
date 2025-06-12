import sys
from src.parser import parse
from src.type_checker import TypeCheckerVisitor


def error(msg):
    print(f"\033[91mError!\n{msg}\033[0m")
    sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        error("No file provided")

    code_file = sys.argv[1]

    try:
        code = open(code_file, "r", encoding="utf-8").read()

        tree = parse(code)

        type_checker = TypeCheckerVisitor()
        type_checker.visit(tree)
        type_checker.print_type_info(code)

    except Exception as e:
        error(e)
