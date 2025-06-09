from inspect import signature

from plugins.location_tools import repo_ops, retriever
from plugins.location_tools.utils.dependency import import_functions

# import_functions(
#     module=retriever, function_names=retriever.__all__, target_globals=globals()
# )

import_functions(
    module=repo_ops, function_names=repo_ops.__all__, target_globals=globals()
)
__all__ = repo_ops.__all__ # + retriever.__all__

DOCUMENTATION = ''
for func_name in __all__:
    func = globals()[func_name]

    # 获取函数的 docstring 文档注释
    cur_doc = func.__doc__
    # remove indentation from docstring and extra empty lines
    # 清理 docstring 的缩进和空行，清理逻辑：
    # 1. cur_doc.split('\n')：按行拆分。
    # 2. map(lambda x: x.strip(), ...)：去掉每行前后的空白。
    # 3. filter(None, ...)：过滤掉空行（即变成空字符串的行）。
    # 4. '\n'.join(...)：重新合并为字符串。
    cur_doc = '\n'.join(filter(None, map(lambda x: x.strip(), cur_doc.split('\n'))))
    # now add a consistent 4 indentation
    # 对每一行添加 4 个空格的缩进，使格式统一、便于阅读
    cur_doc = '\n'.join(map(lambda x: ' ' * 4 + x, cur_doc.split('\n')))

    # 使用 inspect.signature() 获取函数签名（参数列表），并拼接函数名形成如：my_function(a, b=1) 这样的签名字符串。
    fn_signature = f'{func.__name__}' + str(signature(func))
    # 每个函数的说明由函数签名 + docstring 构成，中间以换行分隔，并追加到总文档中。
    # 最终 DOCUMENTATION 会像这样：
    # my_function(a, b=1):
    #     This function does something.
    #     It takes two arguments.
    DOCUMENTATION += f'{fn_signature}:\n{cur_doc}\n\n'
