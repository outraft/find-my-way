import React, { useState } from 'react';
import { MapContainer, TileLayer, Popup, Polyline, CircleMarker } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

import graphData from './veri.json'; 

// Fix Leaflet icons
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
  iconUrl: require('leaflet/dist/images/marker-icon.png'),
  shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
});

function App() {
  const [startStop, setStartStop] = useState(null);
  const [endStop, setEndStop] = useState(null);
  const [routePath, setRoutePath] = useState([]); 
  const [routeInfo, setRouteInfo] = useState(null); // Stores duration info
  const [isLoading, setIsLoading] = useState(false);

  // Helper: Get icon
  const getTransportIcon = (type) => {
    if (!type) return '📍';
    const t = type.toLowerCase();
    if (t.includes('walk')) return '🚶';
    if (t.includes('metro') || t.includes('rail')) return '🚇';
    if (t.includes('tram')) return '🚋';
    if (t.includes('ferry') || t.includes('sea')) return '⛴️';
    if (t.includes('bus') || t.includes('minibus')) return '🚌';
    if (t.includes('finish')) return '🏁';
    return '🚌';
  };

  const getStopByIdOrName = (identifier) => {
    if (!identifier) return null;
    let found = graphData.nodes.find(node => String(node.id) === String(identifier));
    if (!found) found = graphData.nodes.find(node => node.name === identifier);
    return found;
  };

  const handleStopClick = (stop) => {
    // Reset route on new click
    if (routePath.length > 0) {
        setRoutePath([]);
        setRouteInfo(null);
    }

    if (!startStop) setStartStop(stop);
    else if (!endStop) setEndStop(stop);
    else {
      setStartStop(stop);
      setEndStop(null);
    }
  };

  const handleFindRoute = async () => {
    if (!startStop || !endStop) {
        alert("Please select Start and End points.");
        return;
    }

    setIsLoading(true);

    try {
        const response = await fetch(`http://127.0.0.1:5001/api/calculate?start=${startStop.id}&end=${endStop.id}`);
        const data = await response.json();

        if (data.error) {
            alert("Error: " + data.error);
        } else {
            // Process the single route response
            const visualPath = [];
            data.segments.forEach(step => {
                const stopInfo = getStopByIdOrName(step.stop_id);
                if (stopInfo) {
                    visualPath.push({ 
                        ...stopInfo, 
                        transType: step.type, 
                        route: step.line,
                        dist: step.distance_m // Calculated meters from backend
                    });
                }
            });

            setRoutePath(visualPath);
            setRouteInfo({ duration: data.total_duration });
        }

    } catch (error) {
        console.error("Connection Error:", error);
        alert("Cannot connect to Python backend.");
    } finally {
        setIsLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.headerInfo}>
          <h3 style={{margin: 0}}>Istanbul Route Planner</h3>
          <small style={{color: '#bdc3c7'}}>
             Start: <span style={{color: '#2ecc71'}}>{startStop ? startStop.name : '-'}</span> | 
             End: <span style={{color: '#e74c3c'}}>{endStop ? endStop.name : '-'}</span>
          </small>
        </div>
        
        <button onClick={handleFindRoute} style={styles.mainButton} disabled={isLoading}>
           {isLoading ? "CALCULATING..." : "FIND ROUTE"}
        </button>
      </div>

      {/* Map */}
      <div style={styles.mapContainer}>
        <MapContainer center={[41.0082, 28.9784]} zoom={12} style={{ height: '100%', width: '100%' }}>
          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="OSM" />
          
          {graphData.nodes.filter(n => n.pos && n.pos[0] != null).slice(0, 500).map((stop) => (
             <CircleMarker 
                key={stop.id}
                center={stop.pos}
                radius={5}
                pathOptions={{ 
                  color: startStop?.id === stop.id ? '#2ecc71' : endStop?.id === stop.id ? '#e74c3c' : '#3498db',
                  fillOpacity: 0.8 
                }}
                eventHandlers={{ click: () => handleStopClick(stop) }}
             >
               <Popup><strong>{stop.name}</strong><br/><small>ID: {stop.id}</small></Popup>
             </CircleMarker>
          ))}
          
          {routePath.length > 0 && (
            <Polyline 
              positions={routePath.map(p => p.pos)} 
              pathOptions={{ color: '#9b59b6', weight: 6 }} 
            />
          )}
        </MapContainer>
      </div>
      
      {/* Directions Panel */}
      {routePath.length > 0 && (
        <div style={styles.directions}>
            <h4 style={{marginTop: 0, marginBottom: '10px'}}>
                Total Time: <span style={{color: '#2ecc71'}}>{routeInfo?.duration} min</span>
            </h4>
            <ul style={styles.list}>
                {routePath.map((step, i) => (
                    <li key={i} style={styles.listItem}>
                        <span style={{fontSize: '20px', marginRight: '10px', width: '30px', textAlign: 'center'}}>
                            {getTransportIcon(step.transType)}
                        </span>
                        
                        <div style={{display: 'flex', flexDirection: 'column'}}>
                             <span>
                                {step.transType === 'walk' ? `Walk (${step.dist} m)` : 
                                 step.transType === 'finish' ? 'Arrived' : 
                                 step.transType.toUpperCase()} 
                                 
                                {step.route && step.route !== 'Arrived' && ` - ${step.route}`}
                             </span>
                             <strong style={{fontSize: '13px', color: '#555'}}>{step.name}</strong>
                        </div>
                    </li>
                ))}
            </ul>
        </div>
      )}
    </div>
  );
}

const styles = {
  container: { display: 'flex', flexDirection: 'column', height: '100vh', fontFamily: 'Segoe UI, sans-serif' },
  header: { padding: '15px 20px', background: '#2c3e50', color: 'white', display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  headerInfo: { display: 'flex', flexDirection: 'column' },
  mainButton: { padding: '10px 25px', background: '#e67e22', color: 'white', border: 'none', borderRadius: '5px', fontWeight: 'bold', cursor: 'pointer', fontSize: '14px' },
  mapContainer: { flex: 1 },
  directions: { height: '220px', background: '#f5f6fa', padding: '20px', overflowY: 'auto', borderTop: '4px solid #3498db' },
  list: { listStyle: 'none', padding: 0, margin: 0 },
  listItem: { padding: '10px 0', borderBottom: '1px solid #dcdde1', fontSize: '14px', color: '#2f3640', display: 'flex', alignItems: 'center' }
};

export default App;