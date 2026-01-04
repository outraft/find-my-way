from fastapi import FastAPI, HTTPException
from core.graph import find_shortest_path
from typing import Dict, Any

app = FastAPI()

@app.get("/")
def home() -> Dict[str, str]:
	return {"message": "Istanbul GTFS Router is online. Use \'/api/route\' to search."}

@app.get("/api/route")
def get_route(start: str, end: str) -> Dict[str, Any]:
	"""
	Endpoint: /api/route?start=STOP_ID_A&end=STOP_ID_B
	"""

	result = find_shortest_path(start, end)

	if "error" in result:
		raise HTTPException(status_code=404, detail=result["error"])

	return result