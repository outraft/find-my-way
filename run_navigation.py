import json
import os
import sys
from datetime import datetime

# --- Configuration ---
PKL_FILENAME = "istanbul_graph.pkl" # Check if your file name matches
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(CURRENT_DIR)

# Locate the data file
possible_paths = [
    os.path.join(CURRENT_DIR, "data", "processed", PKL_FILENAME),
    os.path.join(CURRENT_DIR, "data", PKL_FILENAME),
    os.path.join(CURRENT_DIR, PKL_FILENAME)
]

found_path = None
for path in possible_paths:
    if os.path.exists(path):
        found_path = path
        break

if not found_path:
    print(f"Error: Data file '{PKL_FILENAME}' not found.")
    sys.exit(1)

# Import core modules
try:
    import core.graph
    core.graph.GRAPH_PATH = found_path
    from core.graph import get_graph
    from core.router_engine import IstanbulRouter, RouteStep, RoutingStrategy

    # Patch RouteStep for priority queue comparison
    def compare_steps(self, other):
        return self.duration_mins < other.duration_mins
    RouteStep.__lt__ = compare_steps

except ImportError as e:
    print(f"Module Import Error: {e}")
    sys.exit(1)

# --- Strategy Definitions (Mirroring api.py) ---

class CustomFastestStrategy(RoutingStrategy):
    """Standard fastest route based on duration."""
    def calculate_cost(self, edge_data: dict, current_time: datetime) -> float:
        return edge_data.get('weight', 0) / 60.0

class CustomComfortStrategy(RoutingStrategy):
    """
    Penalizes buses and minibuses.
    Favors rail systems (metro, tram) and ferries.
    """
    def calculate_cost(self, edge_data: dict, current_time: datetime) -> float:
        base_cost = edge_data.get('weight', 0) / 60.0
        mode = edge_data.get('type', 'walk')
        
        if mode in ['bus', 'minibus']:
            return base_cost * 3.0
        elif mode in ['metro', 'rail', 'tram', 'ferry', 'funicular']:
            return base_cost * 0.7
        
        return base_cost 

class CustomEconomicStrategy(RoutingStrategy):
    """
    Favors walking significantly.
    Penalizes taking any vehicle to simulate cost saving.
    """
    def calculate_cost(self, edge_data: dict, current_time: datetime) -> float:
        base_cost = edge_data.get('weight', 0) / 60.0
        mode = edge_data.get('type', 'walk')
        
        if mode == 'walk':
            return base_cost * 0.7 
        else:
            return base_cost * 2.5 

def generate_multi_routes(start_node_id, end_node_id, output_path="src/ai_route.json"):
    print(f"\nCalculating routes: {start_node_id} -> {end_node_id}")

    try:
        get_graph()
    except Exception as e:
        print(f"Graph loading failed: {e}")
        return

    router = IstanbulRouter()
    current_time = datetime.now()

    scenarios = [
        {"name": "Fastest", "strategy": CustomFastestStrategy(), "desc": "Minimizes time"},
        {"name": "Comfort", "strategy": CustomComfortStrategy(), "desc": "Prefers Metro/Ferry"},
        {"name": "Economic", "strategy": CustomEconomicStrategy(), "desc": "Prefers Walking"}
    ]

    output_data = {
        "meta": {
            "generated_at": current_time.isoformat(),
            "start_id": start_node_id,
            "end_id": end_node_id
        },
        "routes": []
    }

    routes_found = False
    for scenario in scenarios:
        try:
            print(f"  - Running strategy: {scenario['name']}...")
            result = router.find_route(start_node_id, end_node_id, current_time, scenario['strategy'])
            
            if result:
                routes_found = True
                route_entry = {
                    "type": scenario['name'],
                    "description": scenario['desc'],
                    "total_duration": round(result.total_duration_mins, 1),
                    "segments": []
                }

                for step in result.path:
                    route_entry["segments"].append({
                        "stop_id": step.from_node,
                        "type": step.mode,
                        "line": step.route_name
                    })
                
                if result.path:
                    route_entry["segments"].append({
                        "stop_id": result.path[-1].to_node,
                        "type": "finish",
                        "line": "Arrived"
                    })
                
                output_data["routes"].append(route_entry)
        
        except Exception as e:
            print(f"    Warning: Strategy {scenario['name']} failed: {e}")

    if not routes_found:
        print("No routes found between these stops.")
        output_data["routes"] = []

    # Save to JSON
    try:
        target_dir = os.path.dirname(output_path)
        if target_dir and not os.path.exists(target_dir):
            output_path = "ai_route.json"
            
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
            
        print(f"Success: Routes saved to '{output_path}'")
        
    except IOError as e:
        print(f"File Save Error: {e}")

if __name__ == "__main__":
    print("-------------------------------------------------")
    print("ISTANBUL ROUTE GENERATOR (CLI MODE)")
    print("-------------------------------------------------")
    
    start_input = input("Enter Start Node ID: ").strip()
    end_input = input("Enter End Node ID: ").strip()
    
    if start_input and end_input:
        generate_multi_routes(start_input, end_input)
    else:
        print("Invalid input. Exiting.")