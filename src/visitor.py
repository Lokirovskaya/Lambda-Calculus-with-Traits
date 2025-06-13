from .parser import *
from dataclasses import fields, replace


class NodeVisitor:
    def visit(self, node):
        method = "visit_" + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        for field, value in iter_fields(node):
            if isinstance(value, (list, tuple, set)):
                for item in value:
                    if isinstance(item, ASTNode):
                        self.visit(item)
            elif isinstance(value, dict):
                for v in value.values():
                    if isinstance(v, ASTNode):
                        self.visit(v)
            elif isinstance(value, ASTNode):
                self.visit(value)


class TransformVisitor:
    def visit(self, node):
        method = "visit_" + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        updated_fields = {}
        for field, value in iter_fields(node):
            if isinstance(value, list):
                new_list = []
                for item in value:
                    if isinstance(item, ASTNode):
                        new_item = self.visit(item)
                        if new_item is not None:
                            new_list.append(new_item)
                    else:
                        new_list.append(item)
                updated_fields[field] = new_list
            elif isinstance(value, dict):
                new_dict = {}
                for k, v in value.items():
                    if isinstance(v, ASTNode):
                        new_v = self.visit(v)
                        if new_v is not None:
                            new_dict[k] = new_v
                    else:
                        new_dict[k] = v
                updated_fields[field] = new_dict
            elif isinstance(value, ASTNode):
                new_node = self.visit(value)
                updated_fields[field] = new_node
            else:
                updated_fields[field] = value
        return replace(node, **updated_fields)


def iter_fields(node):
    for field in fields(node):
        try:
            yield field.name, getattr(node, field.name)
        except AttributeError:
            pass
