import networkx as nx
import pickle
import os
from typing import Dict, Any, Union
from datetime import datetime
from core.ml_predictor import predictor
import math


CORE_DIR = os.path.dirname(os.path.abspath(__file__))

PROJECT_ROOT = os.path.dirname(CORE_DIR)


GRAPH_PATH = os.path.join(PROJECT_ROOT, 'data', 'processed', 'istanbul_graph.pkl')

_graph_cache = None

def get_graph() -> nx.DiGraph:
    global _graph_cache
    if _graph_cache is None:
        print(f"Loading graph from disc... | DIR: {GRAPH_PATH}")
        try:
            with open(GRAPH_PATH, "rb") as f:
                _graph_cache = pickle.load(f)
        except FileNotFoundError:

            raise RuntimeError(f"Graph not found at {GRAPH_PATH}! Did you run 'py etl/ingest_gtfs.py'?")

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

        path_nodes = nx.shortest_path(G=G, source=start_node, target=end_node, weight='weight')

        base_seconds = nx.shortest_path_length(G, source=start_node, target=end_node, weight='weight')

        real_seconds = base_seconds * delay_factor

        route_segments = []

        for i in range(len(path_nodes) - 1):
            u = path_nodes[i]
            v = path_nodes[i+1]

            start_data = G.nodes[u]
            edge_data = G[u][v]
            

            if isinstance(G, nx.MultiDiGraph):
                edge_data = list(edge_data.values())[0]

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
        return {"status": "error", "message": str(e)}


PROFILE_CONFIGS = {
    "FASTEST": {"desc": "En Hizli", "transfer_penalty": 0, "mode_penalties": {}},
    "COMFORT": {"desc": "Konforlu", "transfer_penalty": 15, "mode_penalties": {"Bus": 5, "Tram": 5, "Walking": 0}},
    "ECONOMIC": {"desc": "Ekonomik", "transfer_penalty": 5, "mode_penalties": {}}
}

def haversine_distance_km(pos1, pos2):
    x1, y1 = pos1
    x2, y2 = pos2
    R = 6371.0 
    phi1, phi2 = math.radians(y1), math.radians(y2)
    delta_phi = math.radians(y2 - y1)
    delta_lambda = math.radians(x2 - x1)
    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def calculate_slope_safe(node1_data, node2_data):
    elev1 = node1_data.get('elev', 0)
    elev2 = node2_data.get('elev', 0)
    pos1 = node1_data.get('pos')
    pos2 = node2_data.get('pos')
    if not pos1 or not pos2: return 0
    dist_km = haversine_distance_km(pos1, pos2)
    return (elev2 - elev1) / (dist_km * 1000.0) if dist_km > 0 else 0

def get_perceived_cost(travel_mins, line_type, profile_type, slope=0):
    config = PROFILE_CONFIGS.get(profile_type, PROFILE_CONFIGS["FASTEST"])
    cost = travel_mins
    cost += config["mode_penalties"].get(line_type, 0)
    if line_type == "Walking" and slope > 0.05 and profile_type == "COMFORT":
        cost += (slope * 100)
    return max(0, cost)

def find_advanced_routes(start_node: str, end_node: str) -> Dict[str, Any]:
    G = get_graph()
    
    if start_node not in G or end_node not in G:
        return {"status": "error", "message": "Durak bulunamadi."}

    options = []
    
    for profile in ["FASTEST", "COMFORT", "ECONOMIC"]:
        try:
            path = nx.shortest_path(G, start_node, end_node, weight='weight')
            
            total_time = 0
            walking_time = 0
            segments = []
            
            for i in range(len(path) - 1):
                u, v = path[i], path[i+1]
                
                edge_data = G[u][v]
                if isinstance(G, nx.MultiDiGraph):
                    edge_data = list(edge_data.values())[0]
                
                travel_time_min = edge_data.get('weight', 60) / 60
                line_type = edge_data.get('type', 'Bus')
                
                slope = calculate_slope_safe(G.nodes[u], G.nodes[v])
                cost = get_perceived_cost(travel_time_min, line_type, profile, slope)
                
                total_time += travel_time_min
                if line_type in ['Walking', 'Yurume']: walking_time += travel_time_min
                segments.append(line_type)

            options.append({
                "mode": profile,
                "duration_min": round(total_time),
                "walking_min": round(walking_time),
                "vehicles": " -> ".join(list(dict.fromkeys(segments)))
            })
            
        except nx.NetworkXNoPath:
            continue

    return {"status": "success", "data": options}