import heapq
import math
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Any

# --- DEPENDENCIES ---
# Importing graph data loader from the core module (project standard)
from core.graph import get_graph 
from core.ml_predictor import predictor

# --- DATA STRUCTURES ---
@dataclass
class RouteStep:
    from_node: str
    to_node: str
    mode: str
    route_name: str
    duration_mins: float
    slope: float = 0.0

@dataclass
class RouteResult:
    strategy_name: str
    total_duration_mins: float
    path: List[RouteStep]

# --- HELPER CLASS (Graph Access Layer) ---
class GraphRepository:
    """
    Singleton wrapper for the NetworkX graph. 
    Ensures safe access to the 'get_graph()' function defined in core/graph.py.
    """
    _instance = None

    def __init__(self):
        # Load the centralized graph instance
        self.G = get_graph()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_node_name(self, node_id: str) -> str:
        return self.G.nodes[node_id].get('name', 'Unknown')

    def get_node_pos(self, node_id: str) -> Tuple[float, float]:
        pos = self.G.nodes[node_id].get('pos')
        return pos if pos else (0.0, 0.0)
    
    def find_node_by_name(self, search_name: str) -> Optional[str]:
        """
        Finds a stop node ID by a partial name match.
        Includes error handling for dirty data (NaN names or float types in CSV).
        """
        if not search_name: return None
        
        search_lower = str(search_name).lower()
        
        for node, data in self.G.nodes(data=True):
            # First get the data
            raw_name = data.get('name')
            
            # If no name, skip
            if raw_name is None:
                continue
                
            # Safe conversion: Convert whatever comes to string, then lower
            try:
                name = str(raw_name).lower()
            except:
                continue
            
            if search_lower in name:
                return node
        return None

# --- COST STRATEGIES (Strategy Pattern) ---
class RoutingStrategy(ABC):
    @abstractmethod
    def calculate_cost(self, edge_data: dict, current_time: datetime) -> float:
        pass

class FastestStrategy(RoutingStrategy):
    def calculate_cost(self, edge_data: dict, current_time: datetime) -> float:
        seconds = edge_data.get('weight', 0)
        mode = edge_data.get('type', 'walk')
        
        # Traffic factor
        multiplier = 1.0
        if mode in ['bus', 'minibus']:
             multiplier = predictor.predict_delay_factor(current_time.hour)
             
        return (seconds * multiplier) / 60.0

class ComfortStrategy(RoutingStrategy):
    def calculate_cost(self, edge_data: dict, current_time: datetime) -> float:
        base_cost = FastestStrategy().calculate_cost(edge_data, current_time)
        mode = edge_data.get('type', 'walk')
        
        # Prioritize Metro (Lower cost), Penalize Bus (Higher cost)
        if mode in ['metro', 'rail', 'tram']:
            return base_cost * 0.8 
        elif mode in ['bus', 'minibus']:
            return base_cost * 1.2
        return base_cost

class EconomicStrategy(RoutingStrategy):
    def calculate_cost(self, edge_data: dict, current_time: datetime) -> float:
        base_cost = FastestStrategy().calculate_cost(edge_data, current_time)
        mode = edge_data.get('type', 'walk')
        
        # Encourage walking (Free)
        if mode == 'walk':
            return base_cost * 0.5 
            
        return base_cost

# --- CORE ROUTING ENGINE (A* Algorithm) ---
class IstanbulRouter:
    def __init__(self):
        self.repo = GraphRepository.get_instance()

    def find_route(self, start_id: str, end_id: str, start_time: datetime, strategy: RoutingStrategy) -> Optional[RouteResult]:
        G = self.repo.G
        
        if start_id not in G or end_id not in G:
            return None

        # Heuristic: Straight line distance (Haversine)
        end_pos = self.repo.get_node_pos(end_id)
        
        def heuristic(u_id):
            u_pos = self.repo.get_node_pos(u_id)
            # Simplified distance calculation (Lat/Lon difference)
            return math.sqrt((u_pos[0]-end_pos[0])**2 + (u_pos[1]-end_pos[1])**2) * 100 

        # Priority Queue: (f_score, node_id, path_history, current_time, g_score)
        queue = [(0, start_id, [], start_time, 0.0)]
        min_costs = {start_id: 0.0}
        
        visited_count = 0
        MAX_VISIT = 5000 # Circuit breaker to prevent infinite loops in non-connected graphs

        while queue:
            f, u, path, curr_dt, g = heapq.heappop(queue)
            
            if u == end_id:
                return RouteResult("Advanced (" + strategy.__class__.__name__ + ")", g, path)
            
            if g > min_costs.get(u, float('inf')):
                continue
            
            visited_count += 1
            if visited_count > MAX_VISIT: break

            for v in G[u]:
                edge_data = G[u][v]
                step_cost = strategy.calculate_cost(edge_data, curr_dt)
                new_g = g + step_cost
                
                if new_g < min_costs.get(v, float('inf')):
                    min_costs[v] = new_g
                    new_f = new_g + heuristic(v)
                    
                    new_step = RouteStep(
                        from_node=self.repo.get_node_name(u),
                        to_node=self.repo.get_node_name(v),
                        mode=edge_data.get('type', 'walk'),
                        route_name=edge_data.get('route_name', ''),
                        duration_mins=step_cost
                    )
                    heapq.heappush(queue, (new_f, v, path + [new_step], curr_dt, new_g))
        return None

# --- ADAPTER FUNCTION ---
def find_advanced_path(start_node: str, end_node: str, time_str: str = None, strategy_type: str = "fastest") -> Dict[str, Any]:
    
    router = IstanbulRouter()
    repo = router.repo

    # 1. ID Check and Search by Name
    real_start = start_node
    if start_node not in repo.G:
        # If ID not found, attempt fuzzy search by name
        found = repo.find_node_by_name(start_node)
        if found: 
            real_start = found
        else: 
            return {"status": "error", "message": f"Start '{start_node}' not found."}

    real_end = end_node
    if end_node not in repo.G:
        # If ID not found, attempt fuzzy search by name
        found = repo.find_node_by_name(end_node)
        if found: 
            real_end = found
        else: 
            return {"status": "error", "message": f"End '{end_node}' not found."}

    # 2. Time Setting
    now = datetime.now()
    if time_str:
        try:
            h, m = map(int, time_str.split(":"))
            now = now.replace(hour=h, minute=m)
        except:
            pass
    
    # 3. Strategy Selection
    strategies = {
        "fastest": FastestStrategy(),
        "comfort": ComfortStrategy(),
        "economic": EconomicStrategy()
    }
    strategy = strategies.get(strategy_type, FastestStrategy())

    # 4. Calculate Route
    result = router.find_route(real_start, real_end, now, strategy)

    if not result:
        return {"status": "error", "message": "No route found via Advanced Engine."}

    # 5. Format Output
    route_segments = []
    for step in result.path:
        route_segments.append({
            "from_stop": {"name": step.from_node},
            "transport": {
                "type": step.mode,
                "route_name": step.route_name,
                "duration_sec": step.duration_mins * 60
            }
        })
    
    if result.path:
        route_segments.append({
            "from_stop": {"name": result.path[-1].to_node},
            "transport": "ARRIVED"
        })

    return {
        "status": "success",
        "total_time_min": round(result.total_duration_mins, 2),
        "stops": len(result.path),
        "route": route_segments,
        "engine": "Advanced A* v3.1",
        "strategy": strategy.__class__.__name__
    }