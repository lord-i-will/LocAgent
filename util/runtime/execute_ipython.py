from IPython.terminal.interactiveshell import TerminalInteractiveShell
from IPython.utils.capture import capture_output

from plugins.location_tools.repo_ops.repo_ops import (
    search_code_snippets,
    get_entity_contents,
    explore_graph_structure,
    explore_tree_structure,
)


def execute_ipython(code_to_execute):
    """
    在 IPython shell 中执行动态 Python 代码（code_to_execute 字符串中提到的函数），并将其输出（stdout 和
    stderr）捕获返回。ipython环境中注入了如下4个函数：search_code_snippets、get_entity_contents
    、explore_graph_structure、explore_tree_structure

    Args:
        code_to_execute (str): 包含函数调用的字符串。
            比如：如果传入search_code_snippets('xxx')，那么会调用search_code_snippets函数。

    Returns:
        str: 函数执行的结果，如果函数执行失败，返回None。
    """
    # Manually initialize an IPython shell
    ipython_shell = TerminalInteractiveShell.instance()

    # 存储get_entity_contents的调用记录
    get_entity_contents_calls = []

    def log_get_entity_contents(func):
        def wrapper(entity_names, *args, **kwargs):
            # 记录调用信息
            call_info = {
                "function": "get_entity_contents",
                "entity_names": entity_names,
                "additional_args": args,  # 其他位置参数（如果有）
                "additional_kwargs": kwargs  # 其他关键字参数（如果有）
            }
            get_entity_contents_calls.append(call_info)
            # 执行原函数
            return func(entity_names, *args, **kwargs)

        return wrapper

    # Inject the function into the IPython environment
    ipython_shell.user_ns['search_code_snippets'] = search_code_snippets
    ipython_shell.user_ns['get_entity_contents'] = log_get_entity_contents(get_entity_contents)
    ipython_shell.user_ns['explore_graph_structure'] = explore_graph_structure
    ipython_shell.user_ns['explore_tree_structure'] = explore_tree_structure
    # ipython_shell.user_ns['explore_repo_structure'] = explore_repo_structure
    # ipython_shell.user_ns['search_interactions_among_modules'] = search_interactions_among_modules

    # Execute the code in the IPython shell
    with capture_output() as captured:
        ipython_shell.run_cell(code_to_execute)

    output = ''
    if captured.stdout:
        output += handle_output(captured.stdout, get_entity_contents_calls)
    if captured.stderr:
        output += captured.stderr

    return output if output else None


def handle_output(stdout, calls: list):
    if len(calls) == 0:
        return stdout

    downstream_invokes = explore_tree_structure(start_entities=calls[0].get('entity_names'), direction='downstream',
                                                traversal_depth=1,
                                                dependency_type_filter=['invokes'])

    return f'{stdout}\n下游依赖（深度1）:\n{downstream_invokes}\n'
