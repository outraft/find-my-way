from fastapi import FastAPI, HTTPException
from core.graph import find_shortest_path
from core.router_engine import find_advanced_path
from typing import Dict, Any, Optional

app = FastAPI()

@app.get("/")
def home() -> Dict[str, str]:
	return {"message": "Istanbul GTFS Router is online. Use \'/api/route\' to search."}

@app.get("/api/route")
def get_route(start: str, end: str, time: Optional[str] = None) -> Dict[str, Any]:
	"""
	Endpoint: /api/route?start=STOP_ID_A&end=STOP_ID_B
	"""

	result = find_shortest_path(start, end, time)

	if "error" in result:
		raise HTTPException(status_code=404, detail=result["error"])

	return result
@app.get("/api/v2/route")
def get_advanced_route(
    start: str, 
    end: str, 
    time: Optional[str] = None, 
    strategy: str = "fastest" # fastest, comfort, economic
) -> Dict[str, Any]:
    """
    Advanced route using A* Algorithm and Strategy.
    """
    result = find_advanced_path(start, end, time, strategy)

    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("message"))

    return result