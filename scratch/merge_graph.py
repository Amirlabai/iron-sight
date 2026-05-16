import json
from pathlib import Path

# Load AST data
ast_data = json.loads(Path('graphify-out/.graphify_ast.json').read_text(encoding='utf-8'))

# Define Semantic Data
semantic_nodes = [
    {"label": "IRON SIGHT", "type": "Project", "summary": "Tactical intelligence engine for real-time threat analysis and visualization in the Israeli theater."},
    {"label": "TACTICAL-CORE-v1.2", "type": "Specification", "summary": "Strategic logic for merging, trajectory consolidation, and origin projection."},
    {"label": "Israel-Based Alert Relay", "type": "Service", "summary": "Node.js relay bridge used to bypass 403 Forbidden errors from the primary source."},
    {"label": "MongoDB Atlas", "type": "Database", "summary": "Cloud database for mission archives, history records, and event lifecycle logs."},
    {"label": "Event Lifecycle Logging", "type": "Feature", "summary": "Detailed timeline tracking for every tactical event from detection to purging."},
    {"label": "Numpy Vectorized Strategy Engine", "type": "Feature", "summary": "High-performance backend calculation engine using NumPy/SciPy for vectorized processing."},
    {"label": "Mission: MOBILE_UI_FIX", "type": "Mission", "summary": "Hardening mobile responsiveness and legibility across Firefox and other mobile browsers."},
    {"label": "Smart Tactical Zoom", "type": "Feature", "summary": "Priority-based map centering logic that focuses on the furthest strategic threats."},
    {"label": "Tactical Sandbox", "type": "Feature", "summary": "Simulation environment for testing threat clusters and trajectory projections."},
    {"label": "TrackingDrone", "type": "Component", "summary": "Frontend visual interpolation for hostile aircraft tracking."}
]

semantic_edges = [
    {"source": "IRON SIGHT", "target": "backend", "type": "contains"},
    {"source": "IRON SIGHT", "target": "dashboard", "type": "contains"},
    {"source": "Israel-Based Alert Relay", "target": "backend", "type": "feeds"},
    {"source": "backend", "target": "MongoDB Atlas", "type": "persists_to"},
    {"source": "backend", "target": "Numpy Vectorized Strategy Engine", "type": "implements"},
    {"source": "Mission: MOBILE_UI_FIX", "target": "dashboard/src/styles/layout.css", "type": "modified"},
    {"source": "Mission: MOBILE_UI_FIX", "target": "dashboard/src/App.css", "type": "modified"},
    {"source": "Mission: MOBILE_UI_FIX", "target": "dashboard/src/components/Sidebar/Sidebar.jsx", "type": "modified"},
    {"source": "Mission: MOBILE_UI_FIX", "target": "dashboard/src/App.jsx", "type": "modified"},
    {"source": "TACTICAL-CORE-v1.2", "target": "backend/src/core/engine.py", "type": "defined_in"}
]

# Merge logic
nodes = ast_data.get('nodes', [])
edges = ast_data.get('edges', [])

# Map labels to IDs for semantic edges if they exist in AST
label_to_id = {node['label']: node['id'] for node in nodes}

processed_semantic_nodes = []
for node in semantic_nodes:
    if node['label'] not in label_to_id:
        node_id = f"semantic_{node['label'].lower().replace(' ', '_')}"
        node['id'] = node_id
        processed_semantic_nodes.append(node)
        label_to_id[node['label']] = node_id
    else:
        # Update existing node with summary
        for n in nodes:
            if n['label'] == node['label']:
                n['summary'] = node['summary']
                n['type'] = node['type']

processed_semantic_edges = []
for edge in semantic_edges:
    src_id = label_to_id.get(edge['source'], edge['source'])
    tgt_id = label_to_id.get(edge['target'], edge['target'])
    processed_semantic_edges.append({
        "source": src_id,
        "target": tgt_id,
        "type": edge['type']
    })

final_graph = {
    "nodes": nodes + processed_semantic_nodes,
    "edges": edges + processed_semantic_edges,
    "hyperedges": []
}

Path('graphify-out/graph.json').write_text(json.dumps(final_graph, indent=2), encoding='utf-8')
print(f"Final Graph: {len(final_graph['nodes'])} nodes, {len(final_graph['edges'])} edges")
