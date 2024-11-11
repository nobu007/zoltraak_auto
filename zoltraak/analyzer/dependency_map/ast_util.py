import ast


def ast_parse(content: str) -> ast.AST:
    try:
        return ast.parse(content)
    except SyntaxError:
        return ast.AST()
