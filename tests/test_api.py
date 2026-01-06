from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from api.index import app

client = TestClient(app=app)

def test_home_endpoint() -> None:
	response = client.get("/")

	assert response.status_code == 200
	assert "Istanbul GTFS Router" in response.json()["message"]

@patch("api.index.find_shortest_path")
def test_get_route_success(mock_find_path : MagicMock) -> None:
	# Setup fake answer from the core logic

	mock_response = {
		"status": "success",
		"total_time_min": 25.5,
		"stops": 5,
		"route": []
	}

	mock_find_path.return_value = mock_response

	response = client.get("/api/route?start=100&end=200")

	assert response.status_code == 200
	assert response.json()["total_time_min"] == 25.5

@patch("api.index.find_shortest_path")
def test_get_route_404(mock_find_path : MagicMock) -> None:
	# Simulate error from core
	mock_find_path.return_value = {"error": "Stop not found"}

	# Request
	response = client.get("/api/route?start=999&end=888")

	assert response.status_code == 404
	assert response.json()["detail"] == "Stop not found"