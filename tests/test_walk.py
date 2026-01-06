import pytest
import networkx as nx
from unittest.mock import patch, MagicMock
import pandas as pd
from etl.ingest_gtfs import haversine, add_walking_transfers

def test_haversine_math() -> None:
	"""
	Test distance between 2 points.
	Taksim Square -> Galata Tower is approx ~1.5km (Straight Line).
	"""

	# Taksim
	lat1, lon1 = 41.0369, 28.9850

	# Galata
	lat2, lon2 = 41.0256, 28.9741
	dist = haversine(lat1, lon1, lat2, lon2)

	assert 1200 < dist < 1800

def test_haversine_zero() -> None:
	"""Distance to self should be 0."""

	assert haversine(41.0, 29.0, 41.0, 29.0) == 0

def test_walking_edges_generated() -> None:
	"""
	We have 3 (mock) stops:
	A and B is in walking distance (100m)
	(A,B) and C is really far (10km)
	Function is supposed to link A <-> B !! BOTH WAYS !!, but NOT A <-> C
	"""

	G = nx.DiGraph()

	mock_stops = pd.DataFrame([
		{'stop_id': 'A', 'stop_lat': 41.0000, 'stop_lon': 29.0000},
		{'stop_id': 'B', 'stop_lat': 41.0001, 'stop_lon': 29.0000},
		{'stop_id': 'C', 'stop_lat': 41.1000, 'stop_lon': 29.0000}
	])

	add_walking_transfers(G, mock_stops, max_dist_meters=300)

	# 1. Check A <-> B exists
	assert G.has_edge('A', 'B')
	assert G.has_edge('B', 'A')
	assert G['A']['B']['type'] == 'walk'

	# 2. Check weight is reasonable (11m / 1.2mps ~= 9 seconds)
	assert G['A']['B']['weight'] < 20

	# 3. Check A <-> C does NOT exist
	assert not G.has_edge('A', 'C')
	assert not G.has_edge('C', 'A')




