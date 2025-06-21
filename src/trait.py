from typing import NoReturn

from .parser import *
from .visitor import TransformVisitor


class TraitVisitor(TransformVisitor):
    def __init__(self):
        super().__init__()
        self.inst_idx = 0

    def _error(self, node: ASTNode, msg: str) -> NoReturn:
        raise TypeError(f"[Line {node.lineno}] Type Error: {msg}")

    def visit_TraitStmt(self, node: TraitStmt):
        """
        trait Show a {show: a -> String;}
        =>
        show = \\a impl Show. \\dict: Show a. dict.show
        每当遇到 show @Int 时，查找 instance env 中 Show[Int]

        """
        if len(node.type_params) != 1:
            self._error(node, "Trait must have exactly one type parameter")

        stmts = []

        # record body
        record_type = RecordType({})
        for item in node.items:
            if item.name in record_type.fields:
                self._error(node, f"Duplicate field name '{item.name}'")
            record_type.fields[item.name] = item.type
        # for all record type
        for_all_type = ForAllType(node.type_params[0], record_type)
        # type definition
        type_def = TypeAssignStmt(node.name, for_all_type, lineno=node.lineno)
        stmts.append(type_def)

        # field funcs
        for item in node.items:
            # show = \a impl Show. \dict: Show a. dict.show
            lambda_expr = TypeLambdaExpr(
                param_name=node.type_params[0],
                trait_bounds=[node.name],
                body=LambdaExpr(
                    param_name="__dict",
                    param_type=AppType(NamedType(node.name), NamedType(node.type_params[0])),
                    body=FieldAccessExpr(record=NamedExpr("__dict"), field_name=item.name),
                ),
            )
            var_def = AssignStmt(item.name, lambda_expr, lineno=node.lineno)
            stmts.append(var_def)

        return stmts

    def visit_StructStmt(self, node: StructStmt):
        # record body
        record_type = RecordType({})
        for item in node.items:
            if item.name in record_type.fields:
                self._error(node, f"Duplicate field name '{item.name}'")
            record_type.fields[item.name] = item.type

        # type definition
        type_def = TypeAssignStmt(node.name, record_type, lineno=node.lineno)

        # constructor
        # S = \x1. \x2. {f1=x1, f2=x2}
        lambda_params = [NamedExpr(f"__x{i}") for i in range(len(node.items))]
        lambda_types = [item.type for item in node.items]
        lambda_expr = RecordExpr(
            {item.name: lambda_params[i] for i, item in enumerate(node.items)},
        )
        for l_param, l_type in reversed(list(zip(lambda_params, lambda_types))):
            lambda_expr = LambdaExpr(l_param.name, l_type, lambda_expr)

        constructor_def = AssignStmt(node.name, lambda_expr, lineno=node.lineno)

        return [type_def, constructor_def]

    def visit_ImplStmt(self, node: ImplStmt):
        """
        impl Show for Int {show = i_to_s;}
        =>
        生成 __show_inst_x 这一个 dict 作为 instance
        存储 Show[Int] = __show_inst_x
        """

        trait_forall_type = NamedType(node.name)
        # for exaultiveness check + integrity check
        expected_trait_impl_type = AppType(trait_forall_type, node.type_param)

        dict_inst = RecordExpr({item.name: item.value for item in node.items})

        inst_name = f"__{node.name}_inst_{self.inst_idx}"
        self.inst_idx += 1

        var_def = AssignStmt(
            inst_name,
            TypeAnnotatedExpr(
                dict_inst,
                expected_trait_impl_type,
                lineno=node.lineno,
            ),  # check by type checker
            lineno=node.lineno,
        )

        inst_decl = InstanceStmt(
            node.name,
            node.type_param,
            NamedExpr(inst_name),
            lineno=node.lineno,
        )
        return [var_def, inst_decl]
