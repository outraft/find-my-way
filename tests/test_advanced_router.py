import sys
import os
# Add project root to path to ensure modules can be imported during testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
import networkx as nx
from unittest.mock import patch, MagicMock
from datetime import datetime


from core.router_engine import find_advanced_path, GraphRepository

@pytest.fixture
def mock_graph_scenario() -> nx.DiGraph:
    """
    Creates a mock graph scenario with 3 distinct paths between A and B:
    1. BUS: Fast but uncomfortable (penalized by Comfort Strategy).
    2. METRO: Slower but comfortable (preferred by Comfort Strategy).
    3. WALK: Long duration but free (preferred by Economic Strategy).
    """
    G = nx.DiGraph()

    # Coordinates (Required for Heuristic calculation)
    # Approx 1-2 km distance
    G.add_node("A", name="Start Home", pos=(41.0000, 29.0000), elev=10)
    G.add_node("B", name="End Work", pos=(41.0100, 29.0100), elev=10)

    # Path 1: BUS (Duration: 10 min / 600 sec)
    # Comfort strategy should penalize this (*1.2)
    G.add_edge("A", "B", weight=600, type="bus", route_name="500T")

    # Path 2: METRO (Duration: 12 min / 720 sec)
    # Comfort strategy should reward this (*0.8 -> 576 perceived sec)
    # Fastest strategy should NOT select this (720 > 600)
    # We add an intermediate station since NetworkX MultiDiGraph isn't used here.
    
    G.add_node("M_STATION", name="Metro Stn", pos=(41.0050, 29.0050), elev=10)
    # Metro path total 12 min (6+6)
    G.add_edge("A", "M_STATION", weight=360, type="metro", route_name="M2")
    G.add_edge("M_STATION", "B", weight=360, type="metro", route_name="M2")

    return G

@pytest.fixture(autouse=True)
def reset_singleton():
    """
    Resets the GraphRepository singleton instance before each test.
    Ensures a clean state for the mock graph.
    """
    GraphRepository._instance = None
    yield

@patch("core.router_engine.get_graph")
def test_fastest_strategy(mock_get_graph: MagicMock, mock_graph_scenario: nx.DiGraph):
    """
    Test FASTEST Strategy:
    Should select the BUS route (10 min) over METRO (12 min).
    """
    mock_get_graph.return_value = mock_graph_scenario

    # 10:00 AM (assuming traffic multiplier 1.0 for this mock)
    
    result = find_advanced_path("A", "B", time_str="12:00", strategy_type="fastest")

    assert result["status"] == "success"
    # Verify Strategy Name
    assert result["strategy"] == "FastestStrategy"
    
    # Verify Route Selection:
    # - Bus: 1 segment (A->B)
    # - Metro: 2 segments (A->M->B)
    # Expected: Bus (Length 2 due to formatting: segment + ARRIVED)
    route = result["route"]
    assert route[0]["transport"]["type"] == "bus"
    assert route[0]["transport"]["route_name"] == "500T"

@patch("core.router_engine.get_graph")
def test_comfort_strategy(mock_get_graph: MagicMock, mock_graph_scenario: nx.DiGraph):
    """
    Test COMFORT Strategy:
    Should select METRO despite being slower.
    Bus (600s * 1.2 penalty = 720s)
    Metro (720s * 0.8 reward = 576s) -> Winner
    """
    mock_get_graph.return_value = mock_graph_scenario

    result = find_advanced_path("A", "B", time_str="12:00", strategy_type="comfort")

    assert result["status"] == "success"
    assert result["strategy"] == "ComfortStrategy"

    # Expected Route: Start -> Metro Stn -> End (Metro line M2)
    route = result["route"]
    assert route[0]["transport"]["type"] == "metro"
    assert route[0]["transport"]["route_name"] == "M2"

@patch("core.router_engine.get_graph")
def test_economic_strategy_walking(mock_get_graph: MagicMock):
    """
    Test ECONOMIC Strategy:
    Should prefer Walking over Taxi.
    
    Scenario:
    1. Taxi: 10 mins (Cost: 600)
    2. Walk: 15 mins (900s). Economic logic applies 0.5 multiplier -> 450 perceived cost.
    
    Result: Walk (450) < Taxi (600).
    """
    
    G = nx.DiGraph()
    G.add_node("A", name="Start", pos=(0,0), elev=0)
    G.add_node("B", name="End", pos=(0,0.01), elev=0) # Short distance

    # Taxi: 10 min (600s)
    G.add_edge("A", "B", weight=600, type="taxi", route_name="Taksi")
    
    # Walk: 15 min (900s) -> Economic Cost: 450 (900 * 0.5)
    # Using an intermediate node for the second path
    G.add_node("PATH", name="Path", pos=(0, 0.005), elev=0)
    
    # A -> Path -> B (Total 900s)
    G.add_edge("A", "PATH", weight=450, type="walk")
    G.add_edge("PATH", "B", weight=450, type="walk")

    mock_get_graph.return_value = G

    result = find_advanced_path("A", "B", strategy_type="economic")
    
    assert result["status"] == "success"
    assert result["strategy"] == "EconomicStrategy"
    assert result["route"][0]["transport"]["type"] == "walk"

@patch("core.router_engine.get_graph")
def test_no_path_found(mock_get_graph: MagicMock):
    """
    Ensure proper error handling when no route exists.
    """
    G = nx.DiGraph()
    G.add_node("A", name="Start", pos=(0,0))
    G.add_node("Z", name="Island", pos=(5,5))
    # No edges connected

    mock_get_graph.return_value = G

    result = find_advanced_path("A", "Z")

    assert result["status"] == "error"
    assert "No route" in result["message"]