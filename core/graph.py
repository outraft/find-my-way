import networkx as nx
import pickle
import os
from typing import Dict, Any, Union
from datetime import datetime
from core.ml_predictor import predictor


# --- CONFIGURATIONS ---
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))  # project root
GRAPH_PATH = os.path.join(BASE_DIR, 'data', 'processed', 'istanbul_graph.pkl')

_graph_cache = None

def get_graph() -> nx.DiGraph:
	"""
	Singleton Pattern:
	Checks if the graph is loaded to the memory. If it is, returns it.
	Else, loads from the disk and returns it. (This is a expensive outreach, since bus routes do NOT change frequently, we can load from memory whenever possible.)
	"""

	global _graph_cache
	if _graph_cache is None:
		print(f"Loading graph from disc... | DIR: {GRAPH_PATH}")
		try:
			with open(GRAPH_PATH, "rb") as f:
				_graph_cache = pickle.load(f)
		except FileNotFoundError:
			raise RuntimeError(f"Graph not found yet! Did you run \'./etl/1_ingest_gtfs.py\'?")

	return _graph_cache

def find_shortest_path(start_node : str, end_node: str, departure_time: str = None) -> Dict[str, Any]:

	G = get_graph()

	if departure_time:
		hour = int(departure_time.split(":")[0])
	else:
		hour = datetime.now().hour

	delay_factor = predictor.predict_delay_factor(hour)

	if start_node not in G:
		return {"error": f"Start node {start_node} not found."}
	if end_node not in G:
		return {"error": f"End node {end_node} not found."}

	try:
		# Dijkstra's Algorithm for optimal pathfinding. (Weight: travel time in seconds)
		path_nodes = nx.shortest_path(G=G, source=start_node, target=end_node, weight='weight')

		base_seconds = nx.shortest_path_length(G, source=start_node, target=end_node, weight='weight')

		real_seconds = base_seconds * delay_factor

		route_segments = []

		for i in range(len(path_nodes) - 1):
			u = path_nodes[i]
			v = path_nodes[i+1]

			start_data = G.nodes[u]
			edge_data = G[u][v]

			route_segments.append({
				"from_stop": {
					"id": u,
					"name": start_data.get('name', 'nil'),
					"coords": start_data.get('pos')
				},
				"transport":{
					"type": edge_data.get('type', 'Unknown'),
					"route_name": edge_data.get('route_name', ''),
					"duration_sec": edge_data.get('weight', 0)
				}
			})

		last_id = path_nodes[-1]
		last_data = G.nodes[last_id]
		route_segments.append({
			"from_stop": {
				"id": last_id,
				"name": last_data.get('name', 'Unknown'),
				"coords": last_data.get('pos')
			},
			"transport": "ARRIVED"
		})

		return {
			"status": "success",
			"stops": len(path_nodes),
			"total_time_min": round(real_seconds / 60, 2),
			"traffic_multiplier": delay_factor,
			"route": route_segments
		}

	except nx.NetworkXNoPath:
		return {"status": "error", "message": "No route possible between these stops."}

	except Exception as e:
		# Catch-all for any other crash
		return {"status": "error", "message": str(e)}