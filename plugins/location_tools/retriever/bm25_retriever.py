import os
import pickle
import Stemmer
import fnmatch
import mimetypes
from typing import Dict, List, Optional

from llama_index.core import SimpleDirectoryReader
from llama_index.core import Document
from llama_index.core.node_parser import SimpleFileNodeParser
from llama_index.retrievers.bm25 import BM25Retriever
from repo_index.index.epic_split import EpicSplitter

from dependency_graph import RepoEntitySearcher
from dependency_graph.traverse_graph import is_test_file
from dependency_graph.build_graph import (
    NODE_TYPE_DIRECTORY,
    NODE_TYPE_FILE,
    NODE_TYPE_CLASS,
    NODE_TYPE_FUNCTION,
)

import warnings

warnings.simplefilter('ignore', FutureWarning)

NTYPES = [
    NODE_TYPE_DIRECTORY,
    NODE_TYPE_FILE,
    NODE_TYPE_FUNCTION,
    NODE_TYPE_CLASS,
]


def build_code_retriever_from_repo(repo_path,
                                   similarity_top_k=10,
                                   min_chunk_size=100,
                                   chunk_size=500,
                                   max_chunk_size=2000,
                                   hard_token_limit=2000,
                                   max_chunks=200,
                                   persist_path=None,
                                   show_progress=False,
                                   ):
    """
    依据代码仓库构建bm25索引。

    Args:
        repo_path (str): 代码仓库的根目录，比如：playground/build_graph/5/avantifellows__quiz-backend
        similarity_top_k (int, optional): BM25检索器的相似度阈值，默认为10。
        min_chunk_size (int, optional): 最小的代码块大小，默认为100。
        chunk_size (int, optional): 代码块大小，默认为500。
        max_chunk_size (int, optional): 最大的代码块大小，默认为2000。
        hard_token_limit (int, optional): 硬令牌限制，默认为2000。
        max_chunks (int, optional): 最大的代码块数量，默认为200。
        persist_path (str, optional): 索引保存路径，比如：index_data/Loc-Bench_V1/BM25_index/avantifellows__quiz-backend-84
        show_progress (bool, optional): 是否显示进度条，默认为False。

    Returns:
        None

    Examples:
        >>> build_code_retriever_from_repo('xxx')
    """

    # print(repo_path)
    # Only extract file name and type to not trigger unnecessary embedding jobs
    def file_metadata_func(file_path: str) -> Dict:
        """
        用于提取每个文件的元信息（路径、文件名、类型、类别等），供之后索引器使用。
        """
        # print(file_path)
        file_path = file_path.replace(repo_path, '')
        if file_path.startswith('/'):
            file_path = file_path[1:]

        test_patterns = [
            '**/test/**',
            '**/tests/**',
            '**/test_*.py',
            '**/*_test.py',
        ]
        # 如果文件路径匹配上面任何一种测试模式，就将其分类为 'test'，否则为 'implementation'（即实际实现代码）。
        category = (
            'test'
            if any(fnmatch.fnmatch(file_path, pattern) for pattern in test_patterns)
            else 'implementation'
        )

        return {
            'file_path': file_path,
            'file_name': os.path.basename(file_path),
            'file_type': mimetypes.guess_type(file_path)[0],  # MIME 类型（例如 text/x-python）
            'category': category,
        }

    # 初始化一个目录读取器，用于加载整个 repo_path 中的 Python 文件。
    reader = SimpleDirectoryReader(
        input_dir=repo_path,
        exclude=[
            '**/test/**',
            '**/tests/**',
            '**/test_*.py',
            '**/*_test.py',
        ],  # 忽略所有测试代码
        file_metadata=file_metadata_func,  # 每个文件使用上面定义的函数添加元数据
        filename_as_id=True,  # 使用文件名作为节点 ID
        required_exts=['.py'],  # TODO: Shouldn't be hardcoded and filtered
        recursive=True,
    )
    # [
    # Document(id_='/Users/bytedance/bytedance/testing_efficiency/code/LocAgent/playground/build_graph/5/avantifellows_quiz-backend/app/__init__.py',
    # embedding=None,
    # metadata={
    #   'file_path': 'Users/bytedance/bytedance/testing_efficiency/code/LocAgent//app/__init__.py',
    #   'file_name': '__init__.py',
    #   'file_type': 'text/x-python',
    #   'category': 'implementation'
    # },
    # excluded_embed_metadata_keys=['file_name', 'file_type', 'file_size', 'creation_date', 'last_modified_date', 'last_accessed_date'],
    # excluded_llm_metadata_keys=['file_name', 'file_type', 'file_size', 'creation_date', 'last_modified_date', 'last_accessed_date'],
    # relationships={},
    # text='', // 文件内容
    # mimetype='text/plain',
    # start_char_idx=None,
    # end_char_idx=None,
    # text_template='{metadata_str}\n\n{content}',
    # metadata_template='{key}: {value}',
    # metadata_seperator='\n'),
    # Document(...)]
    # 每个doc代表一个.py文件。
    docs = reader.load_data()

    # splitter = CodeSplitter(
    #     language="python",
    #     chunk_lines=100,  # lines per chunk
    #     chunk_lines_overlap=15,  # lines overlap between chunks
    #     max_chars=3000,  # max chars per chunk
    # )

    splitter = EpicSplitter(
        min_chunk_size=min_chunk_size,
        chunk_size=chunk_size,
        max_chunk_size=max_chunk_size,
        hard_token_limit=hard_token_limit,
        max_chunks=max_chunks,
        repo_path=repo_path,
    )
    # [CodeNode(id_='/Users/bytedance/bytedance/testing_efficiency/code/LocAgent/playground/build_graph/5/avantifellows_quiz-backend/app/database.py__',
    # embedding=None,
    # metadata={
    #   'file_path': 'Users/bytedance/bytedance/testing_efficiency/code/LocAgent//app/database.py',
    #   'file_name': 'database.py',
    #   'file_type': 'text/x-python',
    #   'category': 'implementation',
    #   'start_line': 1,
    #   'end_line': 13,
    #   'span_ids': ['imports'],
    #   'tokens': 88
    # },
    # excluded_embed_metadata_keys=['file_name', 'file_type', 'file_size', 'creation_date', 'last_modified_date', 'last_accessed_date', 'start_line', 'end_line', 'tokens'],
    # excluded_llm_metadata_keys=['file_name', 'file_type', 'file_size', 'creation_date', 'last_modified_date', 'last_accessed_date'],
    # relationships={},
    # text='import os\nfrom pymongo import MongoClient\n\n# ..... client = MongoClient(os.getenv("MONGO_AUTH_CREDENTIALS"))',// 文档内容
    # mimetype='text/plain',
    # start_char_idx=None,
    # end_char_idx=None,
    # text_template='{metadata_str}\n\n{content}',
    # metadata_template='{key}: {value}',
    # metadata_seperator='\n'),
    # CodeNode(....)]
    # 将每个doc切分成更小粒度的CodeNode。如果doc内容很少，一个CodeNode就等价于一个doc；如果doc内容很多，就会被切分成多个CodeNode。
    prepared_nodes = splitter.get_nodes_from_documents(docs, show_progress=show_progress)

    # We can pass in the index, docstore, or list of nodes to create the retriever
    # BM25 倒排检索器，构建关键词 → CodeNode 的稀疏索引
    retriever = BM25Retriever.from_defaults(
        nodes=prepared_nodes,
        similarity_top_k=similarity_top_k,
        stemmer=Stemmer.Stemmer("english"),
        language="english",
    )
    if persist_path:
        retriever.persist(persist_path)
    return retriever
    # keyword = 'FORBIDDEN_ALIAS_PATTERN'
    # retrieved_nodes = retriever.retrieve(keyword)


def build_retriever_from_persist_dir(path: str):
    retriever = BM25Retriever.from_persist_dir(path)
    return retriever


def build_module_retriever_from_graph(graph_path: Optional[str] = None,
                                      entity_searcher: Optional[RepoEntitySearcher] = None,
                                      search_scope: str = 'all',
                                      # enum = {'function', 'class', 'file', 'all'}
                                      similarity_top_k: int = 10,

                                      ):
    assert search_scope in NTYPES or search_scope == 'all'
    assert graph_path or isinstance(entity_searcher, RepoEntitySearcher)

    if graph_path:
        G = pickle.load(open(graph_path, "rb"))
        entity_searcher = RepoEntitySearcher(G)
    else:
        G = entity_searcher.G

    selected_nodes = list()
    for nid in G:
        if is_test_file(nid): continue

        ndata = entity_searcher.get_node_data([nid])[0]
        ndata['nid'] = nid  # add `nid` property
        if search_scope == 'all':  # and ndata['type'] in NTYPES[2:]
            selected_nodes.append(ndata)
        elif ndata['type'] == search_scope:
            selected_nodes.append(ndata)

    # initialize node parser
    splitter = SimpleFileNodeParser()
    documents = [Document(text=t['nid']) for t in selected_nodes]
    nodes = splitter.get_nodes_from_documents(documents)

    # We can pass in the index, docstore, or list of nodes to create the retriever
    retriever = BM25Retriever.from_defaults(
        nodes=nodes,
        similarity_top_k=similarity_top_k,
        stemmer=Stemmer.Stemmer("english"),
        language="english",
    )

    return retriever
