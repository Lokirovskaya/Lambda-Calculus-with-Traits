import sys
from src.parser import parse
from src.trait import TraitDesugarVisitor
from src.type_checker import TypeCheckerVisitor
from src.interpreter import InterpreterVisitor


def error(msg):
    print(f"\033[91mError!\n{msg}\033[0m")
    sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        error("No file provided")
    debug = "--debug" in sys.argv[1:]


    code_file = sys.argv[1]

    try:
        code = open(code_file, "r", encoding="utf-8").read()

        tree = parse(code)

        trait = TraitDesugarVisitor()
        tree = trait.visit(tree)

        type_checker = TypeCheckerVisitor()
        type_checker.visit(tree)
        type_checker.print_type_info(code)

        interpreter = InterpreterVisitor()
        interpreter.visit(tree)
        interpreter.print_eval_info(code)

    except Exception as e:
        if debug:
            raise e
        else:
            error(e)
