import networkx as nx
import pickle
import os
from typing import Dict, Any, Union

# --- CONFIGURATIONS ---
BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))
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

def find_shortest_path(start_node : str, end_node: str) -> Dict[str, Any]:

	G = get_graph()

	if start_node not in G:
		return {"error": f"Start node {start_node} not found."}
	if end_node not in G:
		return {"error": f"End node {end_node} not found."}

	try:
		# Dijkstra's Algorithm for optimal pathfinding. (Weight: travel time in seconds)
		path_nodes = nx.shortest_path(G=G, source=start_node, target=end_node, weight='weight')

		total_seconds = nx.shortest_path_length(G, source=start_node, target=end_node, weight='weight')

		route_details = []

		for stop_id in path_nodes:
			node_data = G.nodes[stop_id]
			route_details.append({
				"id": stop_id,
				"name": node_data.get('name', 'unknown'),
				"coords": node_data.get('pos', (0,0))
			})

		return {
			"status": "success",
			"stops": len(path_nodes),
			"total_time_min": round(total_seconds / 60, 2),
			"route": route_details
		}

	except:
		return {"error": "No route possible between these 2 stops!"}