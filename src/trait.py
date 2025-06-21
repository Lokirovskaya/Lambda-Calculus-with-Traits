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
        Show 自身作为一个 forall type
        show 作为 trait field 记录在 env
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
        for_all_type = ForAllType(node.type_params[0], record_type, trait_bounds=[node.name])
        # type definition
        type_def = TypeAssignStmt(node.name, for_all_type, lineno=node.lineno)
        stmts.append(type_def)

        # field funcs
        for item in node.items:
            # show = \a. \dict: Show a. dict.show
            trait_field_env = TraitFieldEnvStmt(
                field_name=item.name,
                trait_name=node.name,
                type=ForAllType(
                    param_name=node.type_params[0],
                    body=item.type,
                    trait_bounds=[node.name],
                    lineno=node.lineno,
                ),
                lineno=node.lineno,
            )
            stmts.append(trait_field_env)

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

        inst_decl = InstanceEnvStmt(
            node.name,
            node.type_param,
            NamedExpr(inst_name),
            lineno=node.lineno,
        )
        return [var_def, inst_decl]
