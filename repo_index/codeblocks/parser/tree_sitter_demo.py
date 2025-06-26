from tree_sitter import Parser
from tree_sitter_languages import get_language


def is_language_supported(language_name):
    try:
        language = get_language(language_name)
        return language.name == language_name
    except Exception as e:
        print(f"语言 {language_name} 不支持或编译失败: {e}")
        return False


def view_ast_python():
    parser = Parser()
    parser.set_language(get_language('python'))
    tree = parser.parse(b"def foo(): pass")
    print(tree.root_node.sexp())  # 输出AST的S表达式


def view_ast_go():
    parser = Parser()
    parser.set_language(get_language('go'))
    tree = parser.parse(b"package main\nfunc foo() {}")
    print(tree.root_node.sexp())  # 输出AST的S表达式


def view_ast_go_scm():
    parser = Parser()
    lang = get_language('go')
    parser.set_language(lang)
    # 加载查询文件
    with open(f'queries/go.scm') as f:
        query = lang.query(f.read())
    # 解析代码并运行查询
    tree = parser.parse(b"package main\nfunc foo() {}")
    captures = query.captures(tree.root_node)
    for node, tag in captures:
        print(f"捕获: {tag} -> {node.text.decode()}")

# 获取捕获的表达式/return 等语句所属的函数：向上遍历语法树
def get_parent_function(node):
    while node:
        if node.type == "function_definition":
            return node.child_by_field_name("name").text.decode()
        node = node.parent
    return None  # 全局作用域

if __name__ == '__main__':
    print(is_language_supported("python"))  # True（如果 tree-sitter-python 已安装）
    print(is_language_supported("java"))
    print(is_language_supported("go"))

    view_ast_python()
    view_ast_go()
    view_ast_go_scm()
