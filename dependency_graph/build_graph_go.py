import argparse
import json
import os
import os.path as osp
import pickle
import time

import networkx as nx

from dependency_graph.build_graph import VERSION


def build_graph(repo_path, dump_file):
    with open(f'{repo_path}/go_graph.json') as f:
        data = json.load(f)
    graph = nx.MultiDiGraph()
    # 添加节点
    for node in data['nodes']:
        if 'type' not in node:
            print(f'node {node} has no type, skipping')
            continue
        graph.add_node(node['id'], **node)
    # 添加边
    for edge in data['edges']:
        if edge['from'] not in graph.nodes:
            print(f'edge.from not in graph nodes, skipping, {edge}')
            continue
        elif edge['to'] not in graph.nodes:
            print(f'edge.to not in graph nodes, skipping, {edge}')
            continue
        graph.add_edge(edge['from'], edge['to'], type=edge['type'])
    # dump成.pkl文件
    with open(dump_file, 'wb') as f:
        pickle.dump(graph, f)
        print(f'Processed {repo_name}, graph file dumped: {dump_file}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=str, default="czlll/SWE-bench_Lite")
    parser.add_argument('--repo_path', type=str, default='playground/build_graph',
                        help='The directory where you plan to pull or have already pulled the codebase.')
    parser.add_argument('--index_dir', type=str, default='index_data',
                        help='The base directory where the generated graph index(.pkl) will be saved.')
    args = parser.parse_args()

    dataset_name = args.dataset.split('/')[-1]
    args.index_dir = f'{args.index_dir}/{dataset_name}/graph_index_{VERSION}/'
    repo_name = args.repo_path.split('/')[-1]
    output_file = f'{osp.join(args.index_dir, repo_name)}.pkl'
    if osp.exists(output_file):
        print(f'{repo_name} already processed, graph file: {output_file}, skipping.')
        exit(0)

    os.makedirs(args.index_dir, exist_ok=True)

    start_time = time.time()
    build_graph(args.repo_path, output_file)
    end_time = time.time()
    print(f'Total Execution time = {end_time - start_time:.3f}s')
