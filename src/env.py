from .parser import Type


class Env:
    def __init__(self, outer=None):
        self.vars = {}
        self.outer = outer

    def get(self, name: str) -> Type:
        if name in self.vars:
            return self.vars[name]
        elif self.outer:
            return self.outer.get(name)
        else:
            raise NameError(f"Unbound variable '{name}'")

    def set(self, name: str, type: Type):
        self.vars[name] = type
