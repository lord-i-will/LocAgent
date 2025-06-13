import pickle
from pyvis.network import Network
import networkx as nx


def load_graph(pkl_path: str) -> nx.MultiDiGraph:
    with open(pkl_path, "rb") as f:
        return pickle.load(f)


def visualize_graph(graph: nx.MultiDiGraph, output_html: str = "graph.html"):
    net = Network(height="800px", width="100%", directed=True)
    net.set_options("""
    var options = {
      "interaction": {
        "dragNodes": true,
        "hover": true,
        "navigationButtons": true,
        "keyboard": true
      },
      "physics": {
        "enabled": true,
        "barnesHut": {
          "gravitationalConstant": -20000,
          "centralGravity": 0.3,
          "springLength": 150,
          "springConstant": 0.04,
          "damping": 0.09,
          "avoidOverlap": 1
        },
        "minVelocity": 0.75
      },
      "nodes": {
        "shape": "dot",
        "size": 16,
        "font": {
          "size": 12,
          "face": "Tahoma"
        }
      },
      "edges": {
        "smooth": {
          "type": "dynamic"
        },
        "arrows": {
          "to": {
            "enabled": true,
            "scaleFactor": 0.5
          }
        }
      }
    }
    """)

    for node, attrs in graph.nodes(data=True):
        color = (
            "lightblue" if attrs.get("type") == "directory" else
            "lightgreen" if attrs.get("type") == "file" else
            "orange"
        )
        net.add_node(node, label=node, title=str(attrs), color=color)

    for u, v, k, data in graph.edges(keys=True, data=True):
        net.add_edge(u, v, label=data.get("type", ""), title=str(data))

    net.write_html(output_html)


def visualize_with_filters(graph: nx.MultiDiGraph, output_html="filtered_graph.html"):
    net = Network(height="900px", width="100%", directed=True, notebook=False)

    # 收集所有节点和边类型
    node_types = set()
    edge_types = set()

    for node, attrs in graph.nodes(data=True):
        ntype = attrs.get("type", "unknown")
        node_types.add(ntype)
        net.add_node(
            node,
            label=node,
            title=str(attrs),
            color=("lightblue" if ntype == "directory" else "lightgreen" if ntype == "file" else "orange"),
            group=ntype  # 👈 用于 JS 筛选
        )

    for u, v, k, attrs in graph.edges(keys=True, data=True):
        etype = attrs.get("type", "default")
        edge_types.add(etype)
        net.add_edge(u, v, title=str(attrs), label=etype, group=etype)

    # 设置交互与物理布局
    net.set_options("""
    var options = {
      "interaction": {
        "hover": true,
        "navigationButtons": true
      },
      "physics": {
        "enabled": true,
        "barnesHut": {
          "springLength": 150
        }
      }
    }
    """)

    # 保存 HTML 并注入筛选脚本
    net.save_graph(output_html)

    # 读取生成的 HTML，注入 JS 筛选逻辑
    with open(output_html, "r", encoding="utf-8") as f:
        html = f.read()

    filter_script = f"""
    <script type="text/javascript">
    function filterByType(type, isNode) {{
        var dataset = isNode ? nodes : edges;
        dataset.forEach(function(item) {{
            var visible = (type === 'all' || item.group === type);
            dataset.update({{id: item.id, hidden: !visible}});
        }});
    }}

    function buildFilterUI() {{
        var controls = `
        <div style='padding:10px'>
          <b>Node Type:</b>
          <select onchange="filterByType(this.value, true)">
            <option value='all'>All</option>
            {"".join(f"<option value='{t}'>{t}</option>" for t in sorted(node_types))}
          </select>
          &nbsp;&nbsp;
          <b>Edge Type:</b>
          <select onchange="filterByType(this.value, false)">
            <option value='all'>All</option>
            {"".join(f"<option value='{t}'>{t}</option>" for t in sorted(edge_types))}
          </select>
        </div>
        `;
        document.body.insertAdjacentHTML('afterbegin', controls);
    }}

    window.addEventListener('load', buildFilterUI);
    </script>
    </body>
    """

    # 注入脚本到 </body> 前
    html = html.replace("</body>", filter_script)

    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html)


def main():
    index_data_dir = "index_data/Loc-Bench_V1/graph_index_v2.3"
    # 替换为你的文件名
    graph_path = f"{index_data_dir}/product_tree_data_cleaning.pkl"
    output_file = f"{index_data_dir}/product_tree_data_cleaning.html"

    print("Loading graph...")
    graph = load_graph(graph_path)

    print("Visualizing...")
    # visualize_graph(graph, output_file)
    visualize_with_filters(graph, output_file)

    print(f"✅ Visualization saved to {output_file}")


if __name__ == "__main__":
    main()
