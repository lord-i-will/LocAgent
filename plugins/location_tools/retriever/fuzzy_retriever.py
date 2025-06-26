from rapidfuzz import process, fuzz
import re
import pickle
from typing import Dict, List, Optional
import networkx as nx
from dependency_graph.traverse_graph import is_test_file
from dependency_graph.build_graph import (
    VALID_NODE_TYPES,
    NODE_TYPE_FILE,
    NODE_TYPE_CLASS,
    NODE_TYPE_FUNCTION,
)


def fuzzy_retrieve_from_graph_nodes(
        keyword: str,
        graph_path: Optional[str] = None,
        graph: Optional[nx.MultiDiGraph] = None,
        search_scope: str = 'all',  # enum = {'function', 'class', 'file', 'all'}
        include_files: Optional[str] = None,
        similarity_top_k: int = 5,
        return_score: bool = False,
):
    """
    在图节点中通过模糊搜索匹配关键词。
    Examples:
        # 搜索 "get_user"
        >>> fuzzy_retrieve_from_graph_nodes("get user", graph_path="graph.pkl")
        ['src/auth.py:user_get', 'src/api.py:get_user_by_id']

        # 带分数返回
        >>> fuzzy_retrieve_from_graph_nodes("get user", return_score=True)
        [('src/auth.py:user_get', 100), ('src/api.py:get_user_by_id', 85)]
    Args:
        keyword (str): 要搜索的关键词。
        graph_path (str, optional): 图结构数据的路径，比如：index_data/Loc-Bench_V1/graph_index_v2.3/avantifellows__quiz-backend-84.pkl
        graph (nx.MultiDiGraph, optional): 图结构数据的实例。
        search_scope (str, optional): 搜索范围类型（'function'/'class'/'file'/'all'）。
        include_files (str, optional): 限定搜索的文件范围。
        similarity_top_k (int, optional): 返回TopK结果。
        return_score (bool, optional): 是否返回匹配分数。
    Returns:
        List[str]: 匹配的节点ID列表或List[Tuple(nid, score)]
    """
    assert graph_path or isinstance(graph, nx.MultiDiGraph)
    assert search_scope in VALID_NODE_TYPES or search_scope == 'all'

    if graph_path:
        graph = pickle.load(open(graph_path, "rb"))

    selected_nids = list()
    filter_nids = list()
    for nid in graph:
        if is_test_file(nid): continue
        ndata = graph.nodes[nid]
        if search_scope == 'all' and \
                ndata['type'] in [NODE_TYPE_FILE, NODE_TYPE_CLASS, NODE_TYPE_FUNCTION]:

            nfile = nid.split(':')[0]
            if not include_files or nfile in include_files:
                filter_nids.append(nid)
            selected_nids.append(nid)
        elif ndata['type'] == search_scope:
            nfile = nid.split(':')[0]
            if not include_files or nfile in include_files:
                filter_nids.append(nid)
            selected_nids.append(nid)

    if not filter_nids:
        filter_nids = selected_nids

    # Custom function to split tokens on underscores and hyphens
    def custom_tokenizer(s):
        # replace会把 snake_case、kebab-case 变成单词集合，比如：'my_func-name' → ['my', 'func', 'name']
        # 正则表达式提取所有由字母/数字组成的连续序列（即单词），/、.、:等都被视为非单词字符（类似空格）
        # 举例：输入是src/auth.py:user_get，最终输出['src', 'auth', 'py', 'user', 'get']
        return re.findall(r'\b\w+\b', s.replace('_', ' ').replace('-', ' '))

    # Use token_set_ratio with custom tokenizer
    matches = process.extract(
        keyword,  # 待匹配的关键词
        filter_nids,  # 候选节点ID列表
        scorer=fuzz.token_set_ratio,  # 相似度计算函数
        processor=lambda s: ' '.join(custom_tokenizer(s)),  # keyword和节点ID预处理，确保所有字符串以统一格式参与比较。
        limit=similarity_top_k  # 返回结果数量
    )
    # token_set_ratio 算法特点：
    # 1.分词处理：内部会将字符串按空格、下划线、连字符拆分为单词集合。比如："get_user_info" → {"get", "user", "info"}
    # 2.集合匹配：比较关键词和节点ID的单词集合重叠度。
    # 3.分数计算：基于共有单词的比例和分布计算相似度（0-100分）。
    # 举例：keyword=get_user，节点ID列表=['src/auth.py:user_get','src/api.py:fetch_data']
    # token_set_ratio("get user", "src auth py user get")，单词集合部分相同（{"user", "get"}）→ 得分40
    # token_set_ratio("get user", "src api py fetch data")，无共同单词 → 得分0
    if not return_score:
        return_nids = [match[0] for match in matches]
        return return_nids

    # matches: List[Tuple(nid, score)]
    return matches
