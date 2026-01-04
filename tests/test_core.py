import pytest
import networkx as nx
from unittest.mock import patch, MagicMock
from core.graph import find_shortest_path

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

@patch("core.graph.get_graph") # ! LINEAR
def test_linear_path(mock_get_graph: MagicMock, mock_graph_linear: nx.DiGraph) -> None:
	mock_get_graph.return_value = mock_graph_linear

	result = find_shortest_path("A", "C")

	assert result["status"] == "success"
	assert result["total_time_min"] == 15.0
	assert result["stops"] == 3
	assert result["route"][0]["id"] == "A"
	assert result["route"][-1]["id"] == "C"

@patch("core.graph.get_graph") # ! SHORTCUT
def test_shortcut_path_success(mock_get_graph: MagicMock, mock_graph_shortcut: nx.DiGraph) -> None:
	mock_get_graph.return_value = mock_graph_shortcut


	result = find_shortest_path("A", "C")

	assert result["status"] == "success"
	assert result["total_time_min"] == 7.5
	assert result["stops"] == 2
	assert result["route"][0]["id"] == "A"
	assert result["route"][-1]["id"] == "C"

@patch("core.graph.get_graph") # ! IMPOSSIBLE
def test_path_not_found(mock_get_graph: MagicMock, mock_graph_linear: nx.DiGraph) -> None:
	mock_get_graph.return_value = mock_graph_linear

	# Try to go C -> A (Impossible, it's a one-way street)
	result = find_shortest_path("C", "A")

	assert "error" in result
	assert "No route possible" in result["error"]

