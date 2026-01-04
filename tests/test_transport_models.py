import pytest
import networkx as nx
from unittest.mock import patch, MagicMock
from core.graph import find_shortest_path

@pytest.fixture
def mock_multimodal_graph() -> nx.DiGraph:
	"""
	Creates a complex graph with diffrent transport types.
	A -> B (walk)
	B -> C Metro (Fast)
	C -> D Bus (Slow)
	"""

	G = nx.DiGraph()

	G.add_node("A", name="Home", pos=(0,0))
	G.add_node("B", name="Taksim Metro", pos=(0,1))
	G.add_node("C", name="Levent Metro", pos=(0,5))
	G.add_node("D", name="Seyrantepe Metro - Bus Stop", pos=(1,5))
	G.add_node("E", name="University", pos=(4,5))

	# Edges
	# 1. Walk to station (5 mins)
	G.add_edge("A", "B", weight=300, type="walk", route_name="Walk")

	# 2.1 COULD take Metro M2 (10 mins)
	G.add_edge("B", "C", weight=600, type="metro", route_name="M2")
	# 2.2 COULD go to the metro station directly
	G.add_edge("B", "D", weight=1200, type="metro", route_name="M2")
	# 2.3 After going and getting off at levent, we could retake m2!
	G.add_edge("C", "D", weight=800, type="metro", route_name="M2")
	# 3. Seyrantepe to Uni
	G.add_edge("D", "E", weight=400, type="bus", route_name="K3")

	return G

@patch("core.graph.get_graph")
def test_multimodal_route_details(mock_get_graph: MagicMock, mock_multimodal_graph: nx.DiGraph) -> None:
	mock_get_graph.return_value = mock_multimodal_graph

	result = find_shortest_path("A", "E", "15:00")

	assert result["status"] == "success"

	segments = result["route"]

	assert segments[0]["from_stop"]["name"] == "Home"
	assert segments[0]["transport"]["type"] == "walk"

	assert segments[1]["from_stop"]["name"] == "Taksim Metro"
	assert segments[1]["transport"]["type"] == "metro"
	assert segments[1]["transport"]["route_name"] == "M2"

	assert segments[2]["from_stop"]["name"] == "Seyrantepe Metro - Bus Stop"
	assert segments[2]["transport"]["type"] == "bus"
	assert segments[2]["transport"]["route_name"] == "K3"

	assert segments[3]["transport"] == "ARRIVED"
	assert segments[3]["from_stop"]["name"] == "University"

