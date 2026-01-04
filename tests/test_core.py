import pytest
import networkx as nx
from unittest.mock import patch, MagicMock
from core.graph import find_shortest_path
from datetime import datetime
from core.ml_predictor import predictor

# THIS FILE TESTS THE MATH BEHIND DIJKSTRA'S WITH A MOCK-TABLE, ESSENTIAL FOR USAGE.

@pytest.fixture
def mock_graph_linear() -> nx.DiGraph:
	"""
	Creates a tiny, mock graph: A -> B -> C
	A -> B takes 10 minutes
	B -> C takes 5 minutes
	No connection between A -> C
	Total from A -> C is supposed to take 15 minutes, per calculation by hand.
	"""

	G = nx.DiGraph()
	G.add_node("A", name="Station A", pos=(0,0))
	G.add_node("B", name="Station B", pos=(1,1))
	G.add_node("C", name="Station C", pos=(2,2))

	G.add_edge("A", "B", weight=600) # seconds
	G.add_edge("B", "C", weight=300) # seconds

	return G

@pytest.fixture
def mock_graph_shortcut() -> nx.DiGraph:
	"""
	Creates a tiny, mock graph: A -> B -> C
	A -> B takes 10 minutes
	B -> C takes 5 minutes
	A -> C has a connection, 7min 30secs.
	Total from A -> C is supposed to take 15 minutes, per calculation by hand.
	"""

	G = nx.DiGraph()
	G.add_node("A", name="Station A", pos=(0,0))
	G.add_node("B", name="Station B", pos=(1,1))
	G.add_node("C", name="Station C", pos=(2,2))

	G.add_edge("A", "B", weight=600) # seconds
	G.add_edge("B", "C", weight=300) # seconds
	G.add_edge("A", "C", weight=450) # seconds

	return G

@patch("core.graph.get_graph") # ! LINEAR - EARLY (0.5 MULTIPLIER)
def test_linear_path_early(mock_get_graph: MagicMock, mock_graph_linear: nx.DiGraph) -> None:
	mock_get_graph.return_value = mock_graph_linear

	result = find_shortest_path("A", "C", "05:00")

	assert result["status"] == "success"
	assert result["total_time_min"] == 15.0*0.5
	assert result["traffic_multiplier"] == 0.5
	assert result["stops"] == 3
	assert result["route"][0]["from_stop"]["id"] == "A"
	assert result["route"][-1]["from_stop"]["id"] == "C"

@patch("core.graph.get_graph") # ! LINEAR - EARLY TRAFFIC (1.5 MULTIPLIER)
def test_linear_path_early_traffic(mock_get_graph: MagicMock, mock_graph_linear: nx.DiGraph) -> None:
	mock_get_graph.return_value = mock_graph_linear

	result = find_shortest_path("A", "C", "08:00")

	assert result["status"] == "success"
	assert result["total_time_min"] == 15.0*1.5
	assert result["traffic_multiplier"] == 1.5
	assert result["stops"] == 3
	assert result["route"][0]["from_stop"]["id"] == "A"
	assert result["route"][-1]["from_stop"]["id"] == "C"

@patch("core.graph.get_graph") # ! LINEAR - MID DAY (1 MULTIPLIER)
def test_linear_path_mid_day(mock_get_graph: MagicMock, mock_graph_linear: nx.DiGraph) -> None:
	mock_get_graph.return_value = mock_graph_linear

	result = find_shortest_path("A", "C", "12:00")

	assert result["status"] == "success"
	assert result["total_time_min"] == 15.0*1.0
	assert result["traffic_multiplier"] == 1.0
	assert result["stops"] == 3
	assert result["route"][0]["from_stop"]["id"] == "A"
	assert result["route"][-1]["from_stop"]["id"] == "C"

@patch("core.graph.get_graph") # ! LINEAR - LATE TRAFFIC (1.5 MULTIPLIER)
def test_linear_path_late_traffic(mock_get_graph: MagicMock, mock_graph_linear: nx.DiGraph) -> None:
	mock_get_graph.return_value = mock_graph_linear

	result = find_shortest_path("A", "C", "18:00")

	assert result["status"] == "success"
	assert result["total_time_min"] == 15.0*1.5
	assert result["traffic_multiplier"] == 1.5
	assert result["stops"] == 3
	assert result["route"][0]["from_stop"]["id"] == "A"
	assert result["route"][-1]["from_stop"]["id"] == "C"

@patch("core.graph.get_graph") # ! LINEAR - INSTANTANEOUS TRAFFIC
def test_linear_path_early(mock_get_graph: MagicMock, mock_graph_linear: nx.DiGraph) -> None:
	mock_get_graph.return_value = mock_graph_linear

	result = find_shortest_path("A", "C")

	assert result["status"] == "success"
	assert result["total_time_min"] == (15.0 * predictor.predict_delay_factor(datetime.now().hour))
	assert result["traffic_multiplier"] == predictor.predict_delay_factor(datetime.now().hour)
	assert result["stops"] == 3
	assert result["route"][0]["from_stop"]["id"] == "A"
	assert result["route"][-1]["from_stop"]["id"] == "C"

# ======================================= SHORTCUT =======================================

@patch("core.graph.get_graph") # ! SHORTCUT - EARLY (0.5 MULTIPLIER)
def test_shortcut_early(mock_get_graph: MagicMock, mock_graph_shortcut: nx.DiGraph) -> None:
	mock_get_graph.return_value = mock_graph_shortcut

	result = find_shortest_path("A", "C", "05:00")

	assert result["status"] == "success"
	assert result["total_time_min"] == 7.5*0.5
	assert result["traffic_multiplier"] == 0.5
	assert result["stops"] == 2
	assert result["route"][0]["from_stop"]["id"] == "A"
	assert result["route"][-1]["from_stop"]["id"] == "C"

@patch("core.graph.get_graph") # ! SHORTCUT - EARLY (1.5 MULTIPLIER)
def test_shortcut_path_early_traffic(mock_get_graph: MagicMock, mock_graph_shortcut: nx.DiGraph) -> None:
	mock_get_graph.return_value = mock_graph_shortcut

	result = find_shortest_path("A", "C", "08:00")

	assert result["status"] == "success"
	assert result["total_time_min"] == 7.5*1.5
	assert result["traffic_multiplier"] == 1.5
	assert result["stops"] == 2
	assert result["route"][0]["from_stop"]["id"] == "A"
	assert result["route"][-1]["from_stop"]["id"] == "C"

@patch("core.graph.get_graph") # ! SHORTCUT - MID DAY (1.0 MULTIPLIER)
def test_shortcut_path_mid_day(mock_get_graph: MagicMock, mock_graph_shortcut: nx.DiGraph) -> None:
	mock_get_graph.return_value = mock_graph_shortcut

	result = find_shortest_path("A", "C", "12:00")

	assert result["status"] == "success"
	assert result["total_time_min"] == 7.5*1.0
	assert result["traffic_multiplier"] == 1.0
	assert result["stops"] == 2
	assert result["route"][0]["from_stop"]["id"] == "A"
	assert result["route"][-1]["from_stop"]["id"] == "C"

@patch("core.graph.get_graph") # ! SHORTCUT - LATE TRAFFIC (1.5 MULTIPLIER)
def test_shortcut_path_success_late_traffic(mock_get_graph: MagicMock, mock_graph_shortcut: nx.DiGraph) -> None:
	mock_get_graph.return_value = mock_graph_shortcut

	result = find_shortest_path("A", "C", "18:00")

	assert result["status"] == "success"
	assert result["total_time_min"] == (7.5*1.5)
	assert result["traffic_multiplier"] == 1.5
	assert result["stops"] == 2
	assert result["route"][0]["from_stop"]["id"] == "A"
	assert result["route"][-1]["from_stop"]["id"] == "C"

@patch("core.graph.get_graph") # ! SHORTCUT - INSTANTANEOUS TRAFFIC
def test_shortcut_instantaneous_traffic(mock_get_graph: MagicMock, mock_graph_shortcut: nx.DiGraph) -> None:
	mock_get_graph.return_value = mock_graph_shortcut

	result = find_shortest_path("A", "C")

	assert result["status"] == "success"
	assert result["total_time_min"] == (7.5 * predictor.predict_delay_factor(datetime.now().hour))
	assert result["traffic_multiplier"] == predictor.predict_delay_factor(datetime.now().hour)
	assert result["stops"] == 2
	assert result["route"][0]["from_stop"]["id"] == "A"
	assert result["route"][-1]["from_stop"]["id"] == "C"

@patch("core.graph.get_graph") # ! IMPOSSIBLE
def test_path_not_found(mock_get_graph: MagicMock, mock_graph_linear: nx.DiGraph) -> None:
	mock_get_graph.return_value = mock_graph_linear

	# Try to go C -> A (Impossible, it's a one-way street)
	result = find_shortest_path("C", "A")

	assert "error" in result['status']
	assert "No route possible between these stops." in result["message"]

