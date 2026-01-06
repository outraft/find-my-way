from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sys
from datetime import datetime

app = Flask(__name__)
CORS(app)

# --- Configuration ---
PKL_FILENAME = "istanbul_graph.pkl" # Check your file name
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(CURRENT_DIR)

# Locate data file
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

    # Patch for priority queue comparison
    def compare_steps(self, other):
        return self.duration_mins < other.duration_mins
    RouteStep.__lt__ = compare_steps
    
    get_graph()
    print("System ready. Graph loaded.")

except Exception as e:
    print(f"Initialization Error: {e}")
    sys.exit(1)

# --- Strategy ---
class FastestStrategy(RoutingStrategy):
    """Standard fastest route strategy."""
    def calculate_cost(self, edge_data: dict, current_time: datetime) -> float:
        return edge_data.get('weight', 0) / 60.0

# --- API ---
@app.route('/api/calculate', methods=['GET'])
def calculate_route():
    try:
        start_id = request.args.get('start')
        end_id = request.args.get('end')
        
        if not start_id or not end_id:
            return jsonify({"error": "Missing start or end ID"}), 400

        print(f"Request: {start_id} -> {end_id}")
        
        router = IstanbulRouter()
        now = datetime.now()
        strategy = FastestStrategy()
        
        # Calculate single route
        res = router.find_route(start_id, end_id, now, strategy)
        
        if not res:
            return jsonify({"error": "No route found"}), 404

        path_data = []
        for step in res.path:
            # Calculate distance for walking (approx 80 meters per minute)
            distance_info = ""
            if step.mode == 'walk':
                meters = int(step.duration_mins * 80)
                distance_info = f"{meters}"
            
            path_data.append({
                "stop_id": step.from_node,
                "type": step.mode,
                "line": step.route_name,
                "distance_m": distance_info # Sending estimated meters
            })
        
        # Add arrival point
        if res.path:
            path_data.append({
                "stop_id": res.path[-1].to_node,
                "type": "finish",
                "line": "Arrived",
                "distance_m": ""
            })
            
        # Return as a single object, not a list of options
        result = {
            "total_duration": round(res.total_duration_mins, 1),
            "segments": path_data
        }

        return jsonify(result)

    except Exception as server_error:
        print(f"Server Error: {server_error}")
        return jsonify({"error": "Internal Server Error"}), 500

if __name__ == '__main__':
    print("Starting server on port 5001...")
    app.run(port=5001, debug=True)