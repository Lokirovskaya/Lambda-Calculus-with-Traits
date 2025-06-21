import sys
from src.parser import parse
from src.trait import TraitVisitor
from src.type_solver import TypeSolverVisitor
from src.type_checker import TypeCheckerVisitor
from src.dispatcher import DispatcherVisitor
from src.interpreter import InterpreterVisitor


def error(msg):
    print(f"\033[91mError!\n{msg}\033[0m")
    sys.exit(1)

def print_program(filename, tree):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(str(tree))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        error("No file provided")
    debug = "--debug" in sys.argv[1:]

    code_file = sys.argv[1]

    try:
        code = open(code_file, "r", encoding="utf-8").read()

        tree = parse(code)

        trait = TraitVisitor()
        tree = trait.visit(tree)
        print_program("step1_desugar.rs", tree)

        type_solver = TypeSolverVisitor()
        tree = type_solver.visit(tree)
        print_program("step2_type_solved.rs", tree)

        type_checker = TypeCheckerVisitor()
        type_checker.visit(tree)

        dispatcher = DispatcherVisitor()
        tree = dispatcher.visit(tree)
        print_program("step4_dispatched.rs", tree)

        interpreter = InterpreterVisitor()
        interpreter.visit(tree)

    except Exception as e:
        if debug:
            raise e
        else:
            error(e)


