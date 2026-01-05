from fastapi import FastAPI, HTTPException
from core.graph import find_shortest_path
from core.graph import find_advanced_routes
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
@app.get("/api/advanced-route")
def get_advanced_route(start: str, end: str) -> Dict[str, Any]:
    """
    Mustafa'nın Gelişmiş Rota Motoru
    Kullanım: /api/advanced-route?start=DURAK_A&end=DURAK_B
    """
    result = find_advanced_routes(start, end)
    
    if result["status"] == "error":
        raise HTTPException(status_code=404, detail=result["message"])
        
    return result