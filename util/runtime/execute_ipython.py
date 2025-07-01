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

    # Inject the function into the IPython environment
    ipython_shell.user_ns['search_code_snippets'] = search_code_snippets
    ipython_shell.user_ns['get_entity_contents'] = get_entity_contents
    ipython_shell.user_ns['explore_graph_structure'] = explore_graph_structure
    ipython_shell.user_ns['explore_tree_structure'] = explore_tree_structure
    # ipython_shell.user_ns['explore_repo_structure'] = explore_repo_structure
    # ipython_shell.user_ns['search_interactions_among_modules'] = search_interactions_among_modules

    # Execute the code in the IPython shell
    with capture_output() as captured:
        ipython_shell.run_cell(code_to_execute)

    output = ''
    if captured.stdout:
        output += captured.stdout
    if captured.stderr:
        output += captured.stderr

    return output if output else None
