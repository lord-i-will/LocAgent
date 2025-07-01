import json

import networkx as nx

from visualize_graph import visualize_with_filters


def main():
    # file_path = "/Users/bytedance/bytedance/locagent/playground/bd/temai__product_backend"
    # file_path = "/Users/bytedance/bytedance/testing_efficiency/code/graph_building"
    file_path = "/Users/bytedance/bytedance/testing_efficiency/code/pay_demo"
    filename = "go_graph"
    with open(f'{file_path}/{filename}.json') as f:
        data = json.load(f)
    graph = nx.MultiDiGraph()
    # 添加节点
    for node in data['nodes']:
        graph.add_node(node['id'], **node)
    # 添加边
    for edge in data['edges']:
        graph.add_edge(edge['from'], edge['to'], type=edge['type'])

    output_file = f"{file_path}/{filename}.html"
    print("Visualizing...")
    visualize_with_filters(graph, output_file)
    print(f"✅ Visualization saved to {output_file}")


if __name__ == "__main__":
    main()
