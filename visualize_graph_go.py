import json

import networkx as nx

from visualize_graph import visualize_with_filters


def main():
    with open(f'graph_html/go_graph_graph_building.json') as f:
        data = json.load(f)
    graph = nx.MultiDiGraph()
    # 添加节点
    for node in data['nodes']:
        graph.add_node(node['id'], **node)
    # 添加边
    for edge in data['edges']:
        graph.add_edge(edge['from'], edge['to'], type=edge['type'])

    output_file = f"graph_html/go_graph_graph_building.html"
    print("Visualizing...")
    visualize_with_filters(graph, output_file)
    print(f"✅ Visualization saved to {output_file}")


if __name__ == "__main__":
    main()
