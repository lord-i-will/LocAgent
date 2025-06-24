import argparse
import ast
import os
import re
from collections import Counter, defaultdict
from typing import List

import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.lines import Line2D

VERSION = 'v2.3'
NODE_TYPE_DIRECTORY = 'directory'
NODE_TYPE_FILE = 'file'
NODE_TYPE_CLASS = 'class'
NODE_TYPE_FUNCTION = 'function'
EDGE_TYPE_CONTAINS = 'contains'
EDGE_TYPE_INHERITS = 'inherits'
EDGE_TYPE_INVOKES = 'invokes'
EDGE_TYPE_IMPORTS = 'imports'

VALID_NODE_TYPES = [NODE_TYPE_DIRECTORY, NODE_TYPE_FILE, NODE_TYPE_CLASS, NODE_TYPE_FUNCTION]
VALID_EDGE_TYPES = [EDGE_TYPE_CONTAINS, EDGE_TYPE_INHERITS, EDGE_TYPE_INVOKES, EDGE_TYPE_IMPORTS]

SKIP_DIRS = ['.github', '.git']


def is_skip_dir(dirname):
    for skip_dir in SKIP_DIRS:
        if skip_dir in dirname:
            return True
    return False


def handle_edge_cases(code):
    """
    对源代码进行预处理，解决一些可能导致语法解析错误的特殊情况。

    Args:
        code (str): 源代码

    Returns:
        str: 处理后的源代码

    Examples:
        >>> handle_edge_cases('xxx')
        'xxx'
    """
    # hard-coded edge cases
    # \ufeff 是 UTF-8 编码中的字节顺序标记（BOM），有时会出现在文件的开头。
    # 如果不去除 BOM，可能会导致解析器在处理代码时出现错误。
    # 此行代码通过替换空字符串的方式，移除所有出现的 BOM。
    code = code.replace('\ufeff', '')
    # 在某些代码库中，可能会使用 constants.False 这样的表达方式。
    # 但 False 是 Python 的保留关键字，不能作为属性名使用。
    # 为了避免语法错误，将 constants.False 替换为 _False，确保代码可以被正确解析。
    code = code.replace('constants.False', '_False')
    code = code.replace('constants.True', '_True')
    code = code.replace("False", "_False")
    code = code.replace("True", "_True")
    code = code.replace("DOMAIN\\username", "DOMAIN\\\\username")
    code = code.replace("Error, ", "Error as ")
    code = code.replace('Exception, ', 'Exception as ')
    code = code.replace("print ", "yield ")
    pattern = r'except\s+\(([^,]+)\s+as\s+([^)]+)\):'
    # Replace 'as' with ','
    code = re.sub(pattern, r'except (\1, \2):', code)
    code = code.replace("raise AttributeError as aname", "raise AttributeError")
    return code


def find_imports(filepath, repo_path, tree=None):
    """
    解析给定的 Python 源代码字符串，提取其中的导入模块。

    Args:
        filepath: Python 文件绝对路径，例如/home/code/pdi-qa_product_tree_data_cleaning/bam/merge_bam.py
        repo_path: 要分析的代码仓库根目录路径，例如/home/code/pdi-qa_product_tree_data_cleaning
        tree: 可选参数，表示已解析的抽象语法树（AST）。如果为 None，函数将从 filepath 中读取代码并解析为 AST。

    Returns:
        List[dict]: imports列表，每个dict有如下几种类型：
            {"type":"import", "module":"networkx", "alias":"nx"}
            {"type":"from", "module":"retry", "entities":[{"name":"retry_func", "alias":None}]}
            {"type":"from", "module":"errno", "entities":[{"name":"*", "alias":None}]}
            {"type":"from", "module":"collections", "entities":[{"name":"Counter", "alias":"cnt"},{"name":"defaultdict", "alias":None}]}

    Examples:
        >>> find_imports('xxx')
        'xxx'
    """
    if tree is None:
        try:
            with open(filepath, 'r') as file:
                tree = ast.parse(file.read(), filename=filepath)
        except:
            raise SyntaxError
        # include all imports for file
        # 广度优先方式遍历整棵语法树
        candidates = ast.walk(tree)
    else:
        # only include top level import for classes/functions
        # 返回根节点的直接子节点，不包含所有孙子（局部遍历）
        candidates = ast.iter_child_nodes(tree)

    imports = []
    for node in candidates:
        if isinstance(node, ast.Import):
            # Handle 'import module' and 'import module as alias'
            for alias in node.names:
                module_name = alias.name
                asname = alias.asname
                imports.append({
                    "type": "import",
                    "module": module_name,
                    "alias": asname
                })
        elif isinstance(node, ast.ImportFrom):
            # Handle 'from ... import ...' statements
            import_entities = []
            for alias in node.names:
                if alias.name == '*':
                    import_entities = [{'name': '*', 'alias': None}]
                    break
                else:
                    entity_name = alias.name
                    asname = alias.asname
                    import_entities.append({
                        "name": entity_name,
                        "alias": asname
                    })

            # Calculate the module name for relative imports
            if node.level == 0:
                # Absolute import
                module_name = node.module
            else:
                # Relative import
                rel_path = os.path.relpath(filepath, repo_path)
                # rel_dir = os.path.dirname(rel_path)
                package_parts = rel_path.split(os.sep)

                # Adjust for the level of relative import
                if len(package_parts) >= node.level:
                    package_parts = package_parts[:-node.level]
                else:
                    package_parts = []

                if node.module:
                    module_name = '.'.join(package_parts + [node.module])
                else:
                    module_name = '.'.join(package_parts)

            imports.append({
                "type": "from",
                "module": module_name,
                "entities": import_entities
            })
    return imports


class CodeAnalyzer(ast.NodeVisitor):
    """
    继承自 ast.NodeVisitor，ast.NodeVisitor 是 Python ast 模块里的一个类，用于遍历 Python 代码的抽象语法树（AST）。
    CodeAnalyzer 类的主要功能是遍历 AST 并提取类定义、函数定义相关信息。
    Attributes:
        filename (str): Python 文件绝对路径，比如 /home/code/pdi-qa_product_tree_data_cleaning/merge_bam.py
        nodes (list[dict]): 存储提取到的类定义和函数定义信息的列表。dict结构如下：{'code': 'class AKSK(object):xxx', 'start_line': 17, 'end_line': 36, 'name': 'AKSK', 'type': 'class'}、
            {'code': 'def new_token(self, uname: str):xxx', 'start_line': 23, 'end_line': 25, 'name': 'AKSK.new_token', 'parent_type': 'class', 'type': 'function'}
            注：区别于类方法定义，如果是普通函数定义，那么'parent_type': None
        node_name_stack (list): 栈结构，存储当前遍历节点名，比如['AKSK']。在处理嵌套类或函数时，通过这个栈能拼接出完整的名称，比如AKSK类里面有个new_token方法，那么当遍历到方法节点是，方法节点的全名就是AKSK.new_token
        node_type_stack (list): 同样是栈结构，存储当前遍历节点类型，比如['class']
    """

    def __init__(self, filename):
        self.filename = filename
        self.nodes = []
        self.node_name_stack = []
        self.node_type_stack = []

    def visit_ClassDef(self, node):
        """
        当 ast.NodeVisitor 在遍历 AST 过程中遇到 ClassDef 节点（即类定义节点）时，会自动调用这个方法。
        visit_ClassDef 和 visit_FunctionDef的调用顺序由源代码里类和函数定义的先后顺序决定：
            1. 如果是类的话，一定会先调用 visit_ClassDef 再调用 visit_FunctionDef，因为类的方法定义一定在类定义之后。
            2. 如果是函数的话，visit_ClassDef 和 visit_FunctionDef 的调用顺序是不确定的，因为函数定义可以在类定义之前，也可以在类定义之后。
        """
        class_name = node.name  # AKSK
        full_class_name = '.'.join(
            self.node_name_stack + [class_name])  # 也是AKSK，因为此时self.node_name_stack是空的，外层会处理成'merge_bam.py:AKSK'
        self.nodes.append({
            'name': full_class_name,
            'type': NODE_TYPE_CLASS,
            'code': self._get_source_segment(node),
            'start_line': node.lineno,
            'end_line': node.end_lineno,
        })

        self.node_name_stack.append(class_name)  # ['AKSK']
        self.node_type_stack.append(NODE_TYPE_CLASS)  # ['class']
        self.generic_visit(node)  # 递归遍历当前类节点的子节点，处理类内部的成员定义（如方法、嵌套类等）。
        self.node_name_stack.pop()
        self.node_type_stack.pop()

    def visit_FunctionDef(self, node):
        if self.node_type_stack and self.node_type_stack[-1] == NODE_TYPE_CLASS and node.name == '__init__':
            return
        self._visit_func(node)

    def visit_AsyncFunctionDef(self, node):
        self._visit_func(node)

    def _visit_func(self, node):
        function_name = node.name # new_token
        full_function_name = '.'.join(self.node_name_stack + [function_name])# AKSK.new_token
        self.nodes.append({
            'name': full_function_name,
            'parent_type': self.node_type_stack[-1] if self.node_type_stack else None,
            'type': NODE_TYPE_FUNCTION,
            'code': self._get_source_segment(node),
            'start_line': node.lineno,
            'end_line': node.end_lineno,
        })

        self.node_name_stack.append(function_name)
        self.node_type_stack.append(NODE_TYPE_FUNCTION)
        self.generic_visit(node)
        self.node_name_stack.pop()
        self.node_type_stack.pop()

    def _get_source_segment(self, node):
        with open(self.filename, 'r') as file:
            source_code = file.read()
        return ast.get_source_segment(source_code, node)


# Parese the given file, use CodeAnalyzer to extract classes and helper functions from the file
def analyze_file(filepath):
    """
    解析给定的 Python 源代码文件，提取其中的类和函数。
    Args:
        filepath: Python 文件绝对路径，比如 /home/code/pdi-qa_product_tree_data_cleaning/merge_bam.py
    Returns:
        nodes: list[dict], 存储提取到的类定义和函数定义信息的列表。dict结构如下：{'code': 'class AKSK(object):xxx', 'start_line': 17, 'end_line': 36, 'name': 'AKSK', 'type': 'class'}、
            {'code': 'def new_token(self, uname: str):xxx', 'start_line': 23, 'end_line': 25, 'name': 'AKSK.new_token', 'parent_type': 'class', 'type': 'function'}
            注：区别于类方法定义，如果是普通函数定义，那么'parent_type': None
    """
    with open(filepath, 'r') as file:
        code = file.read()
        # code = handle_edge_cases(code)
        try:
            tree = ast.parse(code, filename=filepath)
        except:
            raise SyntaxError
    analyzer = CodeAnalyzer(filepath)
    try:
        analyzer.visit(tree)
    except RecursionError:
        pass
    return analyzer.nodes


def resolve_module(module_name, repo_path):
    """
    Resolve a module name to a file path in the repo.
    Returns the file path if found, or None if not found.
    """
    # Try to resolve as a .py file
    module_path = os.path.join(repo_path, module_name.replace('.', '/') + '.py')
    if os.path.isfile(module_path):
        return module_path

    # Try to resolve as a package (__init__.py)
    init_path = os.path.join(repo_path, module_name.replace('.', '/'), '__init__.py')
    if os.path.isfile(init_path):
        return init_path

    return None


def add_imports(root_node, imports, graph, repo_path):
    """
    将imports关系添加到graph中。
    Args:
        root_node (str): 文件相对路径(相对当前仓库)，bam/merge_bam.py
        imports (list[dict]): imports列表，每个dict有如下几种类型：
            {"type":"import", "module":"networkx", "alias":"nx"}
            {"type":"from", "module":"retry", "entities":[{"name":"retry_func", "alias":None}]}
            {"type":"from", "module":"errno", "entities":[{"name":"*", "alias":None}]}
            {"type":"from", "module":"collections", "entities":[{"name":"Counter", "alias":"cnt"},{"name":"defaultdict", "alias":None}]}
        graph (nx.DiGraph): The graph to add import edges to.
        repo_path (str): 代码仓库根目录路径，例如/home/code/pdi-qa_product_tree_data_cleaning
    """
    for imp in imports:
        if imp['type'] == 'import':
            # Handle 'import module' statements
            module_name = imp['module']
            module_path = resolve_module(module_name, repo_path)
            if module_path:
                imp_filename = os.path.relpath(module_path, repo_path)
                if graph.has_node(imp_filename):
                    graph.add_edge(root_node, imp_filename, type=EDGE_TYPE_IMPORTS, alias=imp['alias'])
        elif imp['type'] == 'from':
            # Handle 'from module import entity' statements
            module_name = imp['module']
            entities = imp['entities']

            if len(entities) == 1 and entities[0]['name'] == '*':
                # Handle 'from module import *' as 'import module' statement
                module_path = resolve_module(module_name, repo_path)
                if module_path:
                    imp_filename = os.path.relpath(module_path, repo_path)
                    if graph.has_node(imp_filename):
                        graph.add_edge(root_node, imp_filename, type=EDGE_TYPE_IMPORTS, alias=None)
                continue  # Skip further processing for 'import *'

            for entity in entities:
                entity_name, entity_alias = entity['name'], entity['alias']
                entity_module_name = f"{module_name}.{entity_name}"
                entity_module_path = resolve_module(entity_module_name, repo_path)
                if entity_module_path:
                    # Entity is a submodule
                    entity_filename = os.path.relpath(entity_module_path, repo_path)
                    if graph.has_node(entity_filename):
                        graph.add_edge(root_node, entity_filename, type=EDGE_TYPE_IMPORTS, alias=entity_alias)
                else:
                    # Entity might be an attribute inside the module
                    module_path = resolve_module(module_name, repo_path)
                    if module_path:
                        imp_filename = os.path.relpath(module_path, repo_path)
                        node = f"{imp_filename}:{entity_name}"
                        if graph.has_node(node):
                            graph.add_edge(root_node, node, type=EDGE_TYPE_IMPORTS, alias=entity_alias)
                        elif graph.has_node(imp_filename):
                            graph.add_edge(root_node, imp_filename, type=EDGE_TYPE_IMPORTS, alias=entity_alias)


def resolve_symlink(file_path):
    """
    Resolve the absolute path of a symbolic link.
    
    Args:
        file_path (str): The symbolic link file path.
    
    Returns:
        str: The absolute path of the target file if the file is a symbolic link.
        None: If the file is not a symbolic link.
    """
    if os.path.islink(file_path):
        # Get the relative path to the target file
        relative_target = os.readlink(file_path)
        # Get the directory of the symbolic link
        symlink_dir = os.path.dirname(os.path.dirname(file_path))
        # Combine the symlink directory with the relative target path
        absolute_target = os.path.abspath(os.path.join(symlink_dir, relative_target))
        if not os.path.exists(absolute_target):
            print(f"The target file does not exist: {absolute_target}")
            return None
        return absolute_target
    else:
        print(f"{file_path} is not a symbolic link.")
        return None


# Traverse all the Python files under repo_path, construct dependency graphs 
# with node types: directory, file, class, function
def build_graph(repo_path, fuzzy_search=True, global_import=False):
    """
    遍历代码仓库下所有Python文件，构建依赖图，节点类型如下：directory, file, class, function

    Args:
        repo_path(str):	要分析的代码仓库根目录路径，例如/home/code/pdi-qa_product_tree_data_cleaning
        fuzzy_search(bool):	是否启用“模糊调用查找”，调用时不精确匹配，仅根据名称匹配。
            fuzzy_search=True：在分析调用关系时，即使函数名/类名重复，也会保留所有可能的候选目标（更全面但可能引入歧义）
        global_import(bool): 是否启用“跨文件全局搜索导入”，用于增强依赖分析。
            global_import=True：当某个类/函数调用未能在当前文件的导入关系中解析到，会在整个图中尝试匹配符号名，类似“全局搜索”。

    Returns:
        networkx.MultiDiGraph: 有向异构多重图

    Examples:
        >>> build_graph('xxx', global_import=True)
    """
    graph = nx.MultiDiGraph()
    # key: 文件相对路径(相对当前仓库)，bam/merge_bam.py
    # value: 文件绝对路径，/home/code/pdi-qa_product_tree_data_cleaning/bam/merge_bam.py
    file_nodes = {}

    ## add nodes
    graph.add_node('/', type=NODE_TYPE_DIRECTORY)
    dir_stack: List[str] = []
    dir_include_stack: List[bool] = []
    # os.walk 默认采用深度优先遍历（DFS）的方式遍历目录结构，会先处理根目录，然后从第一个一级子目录开始递归进入最深的子目录，再逐级往回处理同级目录。
    # 每次迭代返回一个三元组 (root, dirs, files)：
    #   root：当前正在遍历的目录路径（字符串）。
    #   dirs：当前目录下的子目录名列表（不包括 . 和 ..）。
    #   files：当前目录下的文件名列表。
    # 比如，针对如下目录结构：
    # root/
    #     dir1/
    #         file1.txt
    #         dir1_1/
    #             file1_1.txt
    #         dir1_2/
    #             file1_2.txt
    #     dir2/
    #         file2.txt
    #     file_root.txt
    # 完整返回顺序：
    # ("root", ["dir1", "dir2"], ["file_root.txt"])
    # ("root/dir1", ["dir1_1", "dir1_2"], ["file1.txt"])
    # ("root/dir1/dir1_1", [], ["file1_1.txt"]) 处理完dir1_1后逐级返回到dir1目录，然后继续深度遍历dir1_2目录
    # ("root/dir1/dir1_2", [], ["file1_2.txt"]) 当dir1的所有子目录处理完后，返回到root目录，继续深度遍历dir2目录
    # ("root/dir2", [], ["file2.txt"])
    for root, _, files in os.walk(repo_path):
        # add directory nodes and edges
        # 从 repo_path 出发，找到 root 的相对路径
        # 比如：repo_path=/home/code/pdi-qa_product_tree_data_cleaning
        # 第一轮循环，root==repo_path，dir_name就是.
        # 第二轮循环，root=/home/code/pdi-qa_product_tree_data_cleaning/bam，dir_name就是bam
        dirname = os.path.relpath(root, repo_path)
        if dirname == '.':
            dirname = '/'
        elif is_skip_dir(dirname):
            continue
        else:
            graph.add_node(dirname, type=NODE_TYPE_DIRECTORY)
            parent_dirname = os.path.dirname(dirname)
            if parent_dirname == '':
                parent_dirname = '/'
            # 建立起如下目录之间的contains关系：/ -> bam
            graph.add_edge(parent_dirname, dirname, type=EDGE_TYPE_CONTAINS)

        # in reverse step, remove directories that do not contain .py file
        while len(dir_stack) > 0 and not dirname.startswith(dir_stack[-1]):
            if not dir_include_stack[-1]:
                # print('remove', dir_stack[-1])
                graph.remove_node(dir_stack[-1])
            dir_stack.pop()
            dir_include_stack.pop()
        if dirname != '/':
            dir_stack.append(dirname) # 由于是深度优先遍历，所以栈结构应该是['dir1','dir1/dir1_1','dir1/dir1_2','dir2']
            dir_include_stack.append(False)

        dir_has_py = False
        for file in files:
            if file.endswith('.py'):
                dir_has_py = True

                # add file nodes
                try:
                    # 文件绝对路径：/home/code/pdi-qa_product_tree_data_cleaning/merge_bam.py
                    file_path = os.path.join(root, file)
                    # 文件相对路径：merge_bam.py
                    filename = os.path.relpath(file_path, repo_path)
                    if os.path.islink(file_path):
                        continue
                    else:
                        with open(file_path, 'r') as f:
                            file_content = f.read()

                    graph.add_node(filename, type=NODE_TYPE_FILE, code=file_content)
                    file_nodes[filename] = file_path

                    nodes = analyze_file(file_path)
                except (UnicodeDecodeError, SyntaxError):
                    # Skip the file that cannot decode or parse
                    continue

                # add function/class nodes
                for node in nodes:
                    # class: merge_bam.py:AKSK
                    # function: merge_bam.py:AKSK.new_token
                    full_name = f'{filename}:{node["name"]}'
                    graph.add_node(full_name, type=node['type'], code=node['code'],
                                   start_line=node['start_line'], end_line=node['end_line'])

                # add edges with type=contains
                # directory contains file: / -> merge_bam.py
                graph.add_edge(dirname, filename, type=EDGE_TYPE_CONTAINS)
                for node in nodes:
                    # class: merge_bam.py:AKSK
                    # function: merge_bam.py:AKSK.new_token
                    full_name = f'{filename}:{node["name"]}'
                    # [AKSK] or [AKSK,new_token]
                    name_list = node['name'].split('.')
                    if len(name_list) == 1:
                        # file contains class：merge_bam.py -> AKSK
                        graph.add_edge(filename, full_name, type=EDGE_TYPE_CONTAINS)
                    else:
                        # class: AKSK
                        parent_name = '.'.join(name_list[:-1])
                        full_parent_name = f'{filename}:{parent_name}'
                        # class contains function: merge_bam.py:AKSK -> merge_bam.py:AKSK.new_token
                        graph.add_edge(full_parent_name, full_name, type=EDGE_TYPE_CONTAINS)

        # keep all parent directories
        if dir_has_py:
            for i in range(len(dir_include_stack)):
                dir_include_stack[i] = True

    # check last traversed directory
    while len(dir_stack) > 0:
        if not dir_include_stack[-1]:
            graph.remove_node(dir_stack[-1])
        dir_stack.pop()
        dir_include_stack.pop()

    ## add imports edges (file -> file/class/function)
    # filename: 文件相对路径(相对当前仓库)，bam/merge_bam.py
    # filepath: 文件绝对路径，/home/code/pdi-qa_product_tree_data_cleaning/bam/merge_bam.py
    for filename, filepath in file_nodes.items():
        try:
            imports = find_imports(filepath, repo_path)
        except SyntaxError:
            continue
        add_imports(filename, imports, graph, repo_path)

    # 最终构建的dict如下：
    # {
    #   '/': ['/'],
    #   'py': ['merge_bam.py', 'log.py', ...],
    #   'AKSK': ['merge_bam.py:AKSK'],
    #   'new_token': ['merge_bam.py:AKSK.new_token'],
    #   'Log': ['log.py:Log', 'test.py:Log'],
    # }
    global_name_dict = defaultdict(list)
    if global_import:
        for node in graph.nodes():
            # node举例：/, merge_bam.py:AKSK.new_token, retry.py:retry_func
            node_name = node.split(':')[-1].split('.')[-1]
            global_name_dict[node_name].append(node)

    ## add edges start from class/function
    # class contains function, function invokes function
    for node, attributes in graph.nodes(data=True):
        if attributes.get('type') not in [NODE_TYPE_CLASS, NODE_TYPE_FUNCTION]:
            continue

        caller_code_tree = ast.parse(graph.nodes[node]['code'])

        # construct possible callee dict (name -> node) based on graph connectivity
        callee_nodes, callee_alias = find_all_possible_callee(node, graph)
        if fuzzy_search:
            # for nodes with the same suffix, keep every nodes
            callee_name_dict = defaultdict(list)
            for callee_node in set(callee_nodes):
                callee_name = callee_node.split(':')[-1].split('.')[-1]
                callee_name_dict[callee_name].append(callee_node)
            for alias, callee_node in callee_alias.items():
                callee_name_dict[alias].append(callee_node)
        else:
            # for nodes with the same suffix, only keep the nearest node
            callee_name_dict = {
                callee_node.split(':')[-1].split('.')[-1]: callee_node
                for callee_node in callee_nodes[::-1]
            }
            callee_name_dict.update(callee_alias)

        # analysis invokes and inherits, add (top-level) imports edges (class/function -> class/function)
        if attributes.get('type') == NODE_TYPE_CLASS:
            invocations, inheritances = analyze_init(node, caller_code_tree, graph, repo_path)
        else:
            invocations = analyze_invokes(node, caller_code_tree, graph, repo_path)
            inheritances = []

        # add invokes edges (class/function -> class/function)
        for callee_name in set(invocations):
            callee_node = callee_name_dict.get(callee_name)
            if callee_node:
                if isinstance(callee_node, list):
                    for callee in callee_node:
                        graph.add_edge(node, callee, type=EDGE_TYPE_INVOKES)
                else:
                    graph.add_edge(node, callee_node, type=EDGE_TYPE_INVOKES)
            elif global_import:
                # search from global name dict
                global_fuzzy_nodes = global_name_dict.get(callee_name)
                if global_fuzzy_nodes:
                    for global_fuzzy_node in global_fuzzy_nodes:
                        graph.add_edge(node, global_fuzzy_node, type=EDGE_TYPE_INVOKES)

        # add inherits edges (class -> class)
        for callee_name in set(inheritances):
            callee_node = callee_name_dict.get(callee_name)
            if callee_node:
                if isinstance(callee_node, list):
                    for callee in callee_node:
                        graph.add_edge(node, callee, type=EDGE_TYPE_INHERITS)
                else:
                    graph.add_edge(node, callee_node, type=EDGE_TYPE_INHERITS)
            elif global_import:
                # search from global name dict
                global_fuzzy_nodes = global_name_dict.get(callee_name)
                if global_fuzzy_nodes:
                    for global_fuzzy_node in global_fuzzy_nodes:
                        graph.add_edge(node, global_fuzzy_node, type=EDGE_TYPE_INHERITS)

    return graph


def get_inner_nodes(query_node, src_node, graph):
    inner_nodes = []
    for _, dst_node, attr in graph.edges(src_node, data=True):
        if attr['type'] == EDGE_TYPE_CONTAINS and dst_node != query_node:
            inner_nodes.append(dst_node)
            if graph.nodes[dst_node]['type'] == NODE_TYPE_CLASS:  # only include class's inner nodes
                inner_nodes.extend(get_inner_nodes(query_node, dst_node, graph))
    return inner_nodes


def find_all_possible_callee(node, graph):
    callee_nodes, callee_alias = [], {}
    cur_node = node
    pre_node = node

    def find_parent(_cur_node):
        for predecessor in graph.predecessors(_cur_node):
            for key, attr in graph.get_edge_data(predecessor, _cur_node).items():
                if attr['type'] == EDGE_TYPE_CONTAINS:
                    return predecessor

    while True:
        callee_nodes.extend(get_inner_nodes(pre_node, cur_node, graph))

        if graph.nodes[cur_node]['type'] == NODE_TYPE_FILE:

            # check recursive imported files
            file_list = []
            file_stack = [cur_node]
            while len(file_stack) > 0:
                for _, dst_node, attr in graph.edges(file_stack.pop(), data=True):
                    if attr['type'] == EDGE_TYPE_IMPORTS and dst_node not in file_list + [cur_node]:
                        if graph.nodes[dst_node]['type'] == NODE_TYPE_FILE and dst_node.endswith('__init__.py'):
                            file_list.append(dst_node)
                            file_stack.append(dst_node)

            for file in file_list:
                callee_nodes.extend(get_inner_nodes(cur_node, file, graph))
                for _, dst_node, attr in graph.edges(file, data=True):
                    if attr['type'] == EDGE_TYPE_IMPORTS:
                        if attr['alias'] is not None:
                            callee_alias[attr['alias']] = dst_node
                        if graph.nodes[dst_node]['type'] in [NODE_TYPE_FILE, NODE_TYPE_CLASS]:
                            callee_nodes.extend(get_inner_nodes(file, dst_node, graph))
                        if graph.nodes[dst_node]['type'] in [NODE_TYPE_FUNCTION, NODE_TYPE_CLASS]:
                            callee_nodes.append(dst_node)

            # check imported functions and classes
            for _, dst_node, attr in graph.edges(cur_node, data=True):
                if attr['type'] == EDGE_TYPE_IMPORTS:
                    if attr['alias'] is not None:
                        callee_alias[attr['alias']] = dst_node
                    if graph.nodes[dst_node]['type'] in [NODE_TYPE_FILE, NODE_TYPE_CLASS]:
                        callee_nodes.extend(get_inner_nodes(cur_node, dst_node, graph))
                    if graph.nodes[dst_node]['type'] in [NODE_TYPE_FUNCTION, NODE_TYPE_CLASS]:
                        callee_nodes.append(dst_node)

            break

        pre_node = cur_node
        cur_node = find_parent(cur_node)

    return callee_nodes, callee_alias


def analyze_init(node, code_tree, graph, repo_path):
    caller_name = node.split(':')[-1].split('.')[-1]
    file_path = os.path.join(repo_path, node.split(':')[0])

    invocations = []
    inheritances = []

    def add_invoke(func_name):
        # if func_name in callee_names:
        invocations.append(func_name)

    def add_inheritance(class_name):
        inheritances.append(class_name)

    def process_decorator_node(_decorator_node):
        if isinstance(_decorator_node, ast.Name):
            add_invoke(_decorator_node.id)
        else:
            for _sub_node in ast.walk(_decorator_node):
                if isinstance(_sub_node, ast.Call) and isinstance(_sub_node.func, ast.Name):
                    add_invoke(_sub_node.func.id)
                elif isinstance(_sub_node, ast.Attribute):
                    add_invoke(_sub_node.attr)

    def process_inheritance_node(_inheritance_node):
        if isinstance(_inheritance_node, ast.Attribute):
            add_inheritance(_inheritance_node.attr)
        if isinstance(_inheritance_node, ast.Name):
            add_inheritance(_inheritance_node.id)

    for ast_node in ast.walk(code_tree):
        if isinstance(ast_node, ast.ClassDef) and ast_node.name == caller_name:
            # add imports
            imports = find_imports(file_path, repo_path, tree=ast_node)
            add_imports(node, imports, graph, repo_path)

            for inheritance_node in ast_node.bases:
                process_inheritance_node(inheritance_node)

            for decorator_node in ast_node.decorator_list:
                process_decorator_node(decorator_node)

            for body_item in ast_node.body:
                if isinstance(body_item, ast.FunctionDef) and body_item.name == '__init__':
                    # add imports
                    imports = find_imports(file_path, repo_path, tree=body_item)
                    add_imports(node, imports, graph, repo_path)

                    for decorator_node in body_item.decorator_list:
                        process_decorator_node(decorator_node)

                    for sub_node in ast.walk(body_item):
                        if isinstance(sub_node, ast.Call):
                            if isinstance(sub_node.func, ast.Name):  # function or class
                                add_invoke(sub_node.func.id)
                            if isinstance(sub_node.func, ast.Attribute):  # member function
                                add_invoke(sub_node.func.attr)
                    break
            break

    return invocations, inheritances


def analyze_invokes(node, code_tree, graph, repo_path):
    caller_name = node.split(':')[-1].split('.')[-1]
    file_path = os.path.join(repo_path, node.split(':')[0])

    # store all the invokes found
    invocations = []

    def add_invoke(func_name):
        # if func_name in callee_names:
        invocations.append(func_name)

    def process_decorator_node(_decorator_node):
        if isinstance(_decorator_node, ast.Name):
            add_invoke(_decorator_node.id)
        else:
            for _sub_node in ast.walk(_decorator_node):
                if isinstance(_sub_node, ast.Call) and isinstance(_sub_node.func, ast.Name):
                    add_invoke(_sub_node.func.id)
                elif isinstance(_sub_node, ast.Attribute):
                    add_invoke(_sub_node.attr)

    def traverse_call(_node):
        for child in ast.iter_child_nodes(_node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                # Skip inner function/class definition
                continue
            elif isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    add_invoke(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    add_invoke(child.func.attr)
            # Recursively traverse child nodes
            traverse_call(child)

    # Traverse AST nodes to find invokes
    for ast_node in ast.walk(code_tree):
        if (isinstance(ast_node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and ast_node.name == caller_name):
            # Add imports
            imports = find_imports(file_path, repo_path, tree=ast_node)
            add_imports(node, imports, graph, repo_path)

            # Traverse decorators
            for decorator_node in ast_node.decorator_list:
                process_decorator_node(decorator_node)

            # Traverse all the invokes nodes inside the function body, excluding inner functions and classes
            traverse_call(ast_node)
            break

    return invocations


def visualize_graph(G):
    node_types = set(nx.get_node_attributes(G, 'type').values())
    node_shapes = {NODE_TYPE_CLASS: 'o', NODE_TYPE_FUNCTION: 's', NODE_TYPE_FILE: 'D',
                   NODE_TYPE_DIRECTORY: '^'}
    node_colors = {NODE_TYPE_CLASS: 'lightgreen', NODE_TYPE_FUNCTION: 'lightblue',
                   NODE_TYPE_FILE: 'lightgrey', NODE_TYPE_DIRECTORY: 'orange'}

    edge_types = set(nx.get_edge_attributes(G, 'type').values())
    edge_colors = {EDGE_TYPE_IMPORTS: 'forestgreen', EDGE_TYPE_CONTAINS: 'skyblue',
                   EDGE_TYPE_INVOKES: 'magenta', EDGE_TYPE_INHERITS: 'brown'}
    edge_styles = {EDGE_TYPE_IMPORTS: 'solid', EDGE_TYPE_CONTAINS: 'dashed', EDGE_TYPE_INVOKES: 'dotted',
                   EDGE_TYPE_INHERITS: 'dashdot'}

    # pos = nx.spring_layout(G, k=2, iterations=50)
    pos = nx.shell_layout(G)
    # pos = nx.circular_layout(G, scale=2, center=(0, 0))

    plt.figure(figsize=(20, 20))
    plt.margins(0.15)  # Add padding around the plot

    # Draw nodes with different shapes and colors based on their type
    for ntype in node_types:
        nodelist = [n for n, d in G.nodes(data=True) if d['type'] == ntype]
        nx.draw_networkx_nodes(
            G,
            pos,
            nodelist=nodelist,
            node_shape=node_shapes[ntype],
            node_color=node_colors[ntype],
            node_size=700,
            label=ntype,
        )

    # Draw labels
    nx.draw_networkx_labels(G, pos, font_size=12, font_family='sans-serif')

    # Group edges between the same pair of nodes
    edge_groups = {}
    for u, v, key, data in G.edges(keys=True, data=True):
        if (u, v) not in edge_groups:
            edge_groups[(u, v)] = []
        edge_groups[(u, v)].append((key, data))

    # Draw edges with adjusted 'rad' values
    for (u, v), edges in edge_groups.items():
        num_edges = len(edges)
        for i, (key, data) in enumerate(edges):
            edge_type = data['type']
            # Adjust 'rad' to spread the edges
            rad = 0.1 * (i - (num_edges - 1) / 2)
            nx.draw_networkx_edges(
                G,
                pos,
                edgelist=[(u, v)],
                edge_color=edge_colors[edge_type],
                style=edge_styles[edge_type],
                connectionstyle=f'arc3,rad={rad}',
                arrows=True,
                arrowstyle='-|>',
                arrowsize=15,
                min_source_margin=15,
                min_target_margin=15,
                width=1.5
            )

    # Create legends for edge types and node types
    edge_legend_elements = [
        Line2D([0], [0], color=edge_colors[etype], lw=2, linestyle=edge_styles[etype], label=etype)
        for etype in edge_types
    ]
    node_legend_elements = [
        Line2D([0], [0], marker=node_shapes[ntype], color='w', label=ntype,
               markerfacecolor=node_colors[ntype], markersize=15)
        for ntype in node_types
    ]

    # Combine legends
    plt.legend(handles=edge_legend_elements + node_legend_elements, loc='upper left')
    plt.axis('off')
    plt.savefig('plots/dp_v3.png')


def traverse_directory_structure(graph, root='/'):
    def traverse(node, prefix, is_last):
        if node == root:
            print(f"{node}")
            new_prefix = ''
        else:
            connector = '└── ' if is_last else '├── '
            print(f"{prefix}{connector}{node}")
            new_prefix = prefix + ('    ' if is_last else '│   ')

        # Stop if the current node is a file (leaf node)
        if graph.nodes[node].get('type') == 'file':
            return

        # Traverse neighbors with edge type 'contains'
        neighbors = list(graph.neighbors(node))
        for i, neighbor in enumerate(neighbors):
            for key in graph[node][neighbor]:
                if graph[node][neighbor][key].get('type') == 'contains':
                    is_last_child = (i == len(neighbors) - 1)
                    traverse(neighbor, new_prefix, is_last_child)

    traverse(root, '', False)


def main():
    # Generate Dependency Graph
    graph = build_graph(args.repo_path, global_import=args.global_import)

    if args.visualize:
        visualize_graph(graph)

    inherit_list = []
    edge_types = []
    for u, v, data in graph.edges(data=True):
        if data['type'] == EDGE_TYPE_IMPORTS:
            inherit_list.append((u, v))
            # print((u, v))
        edge_types.append(data['type'])
    print()
    print(Counter(edge_types))

    node_types = []
    for node, data in graph.nodes(data=True):
        node_types.append(data['type'])
    print(Counter(node_types))

    traverse_directory_structure(graph)
    # breakpoint()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo_path', type=str, default='DATA/repo/pallets__flask-5063')
    parser.add_argument('--visualize', action='store_true')
    parser.add_argument('--global_import', action='store_true')
    args = parser.parse_args()

    main()
