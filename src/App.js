import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Popup, Polyline, CircleMarker } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import graphData from './veri.json'; // Importing our data file

// Fix for Leaflet's default icon issue
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
  iconUrl: require('leaflet/dist/images/marker-icon.png'),
  shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
});

function App() {
  // --- STATE MANAGEMENT ---
  // Storing the selected start and end stops
  const [startNode, setStartNode] = useState(null);
  const [endNode, setEndNode] = useState(null);
  
  // Storing the calculated route
  const [routePath, setRoutePath] = useState([]);

  // --- EVENT HANDLERS ---
  
  // Function to handle clicks on stops (markers)
  const handleStopClick = (node) => {
    if (!startNode) {
      setStartNode(node); // First click: Set Start
    } else if (!endNode) {
      setEndNode(node);   // Second click: Set Destination
    } else {
      // Third click: Reset everything and start over
      setStartNode(node);
      setEndNode(null);
      setRoutePath([]); 
    }
  };

  // Main function to calculate the route when the button is clicked
  const handleCalculateRoute = () => {
    if (!startNode || !endNode) {
      alert("Please select both a Start and a Destination point on the map.");
      return;
    }

    // Get links/edges from data (handling different naming conventions)
    const links = graphData.links || graphData.edges || [];

    if (links.length === 0) {
      alert("Error: No route data found in the file!");
      return;
    }

    console.log(`Calculating route from ${startNode.name} to ${endNode.name}...`);

    // Run the algorithm
    const result = findShortestPath(graphData.nodes, links, startNode.id, endNode.id);
    
    if (result && result.length > 0) {
      setRoutePath(result);
    } else {
      alert("No suitable path found between these two locations.");
      setRoutePath([]);
    }
  };

  return (
    <div style={styles.container}>
      
      {/* CONTROL PANEL */}
      <div style={styles.panel}>
        <div>
          <h3>🗺️ Istanbul City Guide</h3>
          <div style={{ fontSize: '14px' }}>
            <span style={{ color: '#4CAF50', fontWeight: 'bold' }}>Start: </span> 
            {startNode ? startNode.name : 'Not Selected'}
            <br />
            <span style={{ color: '#FF5252', fontWeight: 'bold' }}>Destination: </span> 
            {endNode ? endNode.name : 'Not Selected'}
          </div>
        </div>
        
        <button onClick={handleCalculateRoute} style={styles.button}>
          FIND ROUTE 🚀
        </button>
      </div>

      {/* MAP SECTION */}
      <div style={styles.mapContainer}>
        <MapContainer center={[41.0082, 28.9784]} zoom={12} style={{ height: '100%', width: '100%' }}>
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='&copy; OpenStreetMap contributors'
          />

          {/* DRAW STOPS (NODES) */}
          {/* Performance Note: Filtering invalid coordinates and showing limited nodes */}
          {graphData.nodes
            .filter(n => n.pos && n.pos[0] != null && n.pos[1] != null) 
            .slice(0, 500) 
            .map((node) => (
             <CircleMarker 
                key={node.id}
                center={node.pos}
                radius={6}
                // Dynamic styling based on selection
                pathOptions={{ 
                  color: startNode?.id === node.id ? '#4CAF50' : endNode?.id === node.id ? '#FF5252' : '#2196F3',
                  fillOpacity: 0.8 
                }}
                eventHandlers={{ click: () => handleStopClick(node) }}
             >
               <Popup>{node.name}</Popup>
             </CircleMarker>
          ))}

          {/* DRAW ROUTE (Purple Line) */}
          {routePath.length > 0 && (
            <Polyline 
              positions={routePath.map(point => point.pos)} 
              pathOptions={{ color: '#9C27B0', weight: 5, dashArray: '10, 10' }} 
            />
          )}

        </MapContainer>
      </div>

      {/* DIRECTIONS PANEL */}
      {routePath.length > 0 && (
        <div style={styles.directionsBox}>
          <h4>📍 Directions:</h4>
          <ul style={{ listStyleType: 'none', padding: 0 }}>
            {routePath.map((step, index) => (
              <li key={index} style={styles.listItem}>
                {index === 0 ? "🏁 Start Point: " : 
                 step.transType === 'walk' ? `🚶 Walk (${step.weight}m) ➔ ` :
                 step.transType === 'ferry' ? `⛴️ Take Ferry (${step.route || 'Line'}) ➔ ` :
                 `🚌 Take Bus (${step.route || step.transType}) ➔ `}
                <strong>{step.name}</strong>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// --- CSS STYLES ---
const styles = {
  container: { display: 'flex', flexDirection: 'column', height: '100vh', fontFamily: 'Arial, sans-serif' },
  panel: { padding: '15px', background: '#333', color: '#fff', display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  button: { padding: '10px 20px', background: '#ff9800', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold', color: '#fff' },
  mapContainer: { flex: 1 },
  directionsBox: { height: '180px', overflowY: 'auto', background: '#f5f5f5', padding: '15px', borderTop: '2px solid #ddd' },
  listItem: { padding: '5px 0', borderBottom: '1px solid #eee' }
};

// --- ALGORITHM: Dijkstra (Enhanced with Transfer Penalty) ---
const findShortestPath = (nodes, links, startId, endId) => {
  const adjacencyList = {};
  
  // 1. Build the Graph
  links.forEach(link => {
    if (!adjacencyList[link.source]) adjacencyList[link.source] = [];
    adjacencyList[link.source].push({ 
      target: link.target, 
      weight: link.weight, 
      type: link.type, 
      route: link.route_name 
    });
  });

  const distances = {}; 
  const previous = {};  
  const queue = [];     

  // Initialize
  nodes.forEach(n => {
    distances[n.id] = Infinity;
    previous[n.id] = null;
  });
  
  distances[startId] = 0;
  queue.push({ id: startId, dist: 0, currentType: 'start', currentRoute: null });

  while (queue.length > 0) {
    // Sort to find the node with the smallest distance
    queue.sort((a, b) => a.dist - b.dist);
    const { id: currentId, currentType: prevType, currentRoute: prevRoute } = queue.shift();

    if (currentId === endId) break;

    const neighbors = adjacencyList[currentId] || [];
    
    neighbors.forEach(neighbor => {
      // --- PENALTY LOGIC ---
      // We add a penalty cost to prevent unnecessary transfers.
      let penalty = 0;

      // If switching from walking to a vehicle, add wait time penalty (e.g., equivalent to 1000m)
      if (neighbor.type !== 'walk' && (prevType === 'walk' || prevType === 'start' || prevRoute !== neighbor.route)) {
         penalty = 1000; 
      }

      // Small penalty for switching from vehicle to walking
      if (prevType !== 'walk' && prevType !== 'start' && neighbor.type === 'walk') {
         penalty = 50; 
      }

      const newDist = distances[currentId] + neighbor.weight + penalty;
      
      if (newDist < distances[neighbor.target]) {
        distances[neighbor.target] = newDist;
        previous[neighbor.target] = { id: currentId, type: neighbor.type, route: neighbor.route };
        queue.push({ 
            id: neighbor.target, 
            dist: newDist, 
            currentType: neighbor.type, 
            currentRoute: neighbor.route 
        });
      }
    });
  }

  // Reconstruct path backwards
  const path = [];
  let current = endId;
  
  if (distances[current] === Infinity) return null;

  while (current) {
    const nodeInfo = nodes.find(n => n.id === current);
    const prevInfo = previous[current];
    
    if(nodeInfo) {
        path.unshift({
            ...nodeInfo,
            transType: prevInfo ? prevInfo.type : 'start',
            route: prevInfo ? prevInfo.route : ''
        });
    }
    current = previous[current] ? previous[current].id : null;
  }
  
  return path;
};

export default App;