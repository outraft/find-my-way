import os
import pickle
import networkx as nx
import pandas as pd
import math
from typing import List, Tuple
from scipy.spatial import cKDTree

# --- CONFIGURATION ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR) 

GTFS_PATH = os.path.join(PROJECT_ROOT, 'data', 'raw')
OUTPUT_PATH = os.path.join(PROJECT_ROOT, 'data', 'processed', 'istanbul_graph.pkl')
turkish_encoding = 'iso-8859-9'

ROUTE_TYPE_MAP = {
    0: 'tram', 1: 'metro', 2: 'rail', 3: 'bus', 4: 'ferry',
    5: 'cable_tram', 6: 'gondola', 7: 'funicular',
    9: 'minibus', 11: 'trolleybus'
}

def parse_gtfs_time(time_str : str) -> int:
    if pd.isna(time_str): return None
    try:
        h, m, s = map(int, time_str.split(":"))
        return h * 3600 + m * 60 + s
    except:
        return 0

def add_walking_transfers_fast(G: nx.DiGraph, stops_df: pd.DataFrame, max_dist_meters: int = 300, walk_speed_mps = 1.2) -> None:
    print(f"5. Generating Walking transfers (KD-Tree Optimized)...")
    
    # --- TEMİZLİK ADIMI 2: Koordinatları sayıya çevir ve hatalıları at ---
    stops_clean = stops_df.dropna(subset=['stop_lat', 'stop_lon']).copy()
    
    # Koordinatları al
    coords = list(zip(stops_clean['stop_lon'], stops_clean['stop_lat']))
    ids = list(stops_clean['stop_id'].astype(str))
    
    if not coords:
        print("UYARI: Hiç geçerli durak koordinatı bulunamadı!")
        return

    tree = cKDTree(coords)
    
    # 0.004 derece yakl. 300-400 metre
    pairs = tree.query_pairs(r=0.004) 
    
    count = 0
    for i, j in pairs:
        u, v = ids[i], ids[j]
        
        if u not in G.nodes or v not in G.nodes: continue

        lat1, lon1 = G.nodes[u]['pos']
        lat2, lon2 = G.nodes[v]['pos']
        
        R = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2-lat1)
        dlambda = math.radians(lon2-lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
        dist = R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        if dist <= max_dist_meters:
            walk_time = int(dist / walk_speed_mps)
            G.add_edge(u, v, weight=walk_time, type='Walking', route_name='Yurume')
            G.add_edge(v, u, weight=walk_time, type='Walking', route_name='Yurume')
            count += 1
            
    print(f"   > Added {count * 2} walking connections.")

def build_graph():
    print(f"Loading GTFS data from: {GTFS_PATH}")
    
    if not os.path.exists(os.path.join(GTFS_PATH, 'stops.csv')):
        raise FileNotFoundError(f"HATA: stops.csv bulunamadı! Aranan yer: {os.path.join(GTFS_PATH, 'stops.csv')}")

    stops = pd.read_csv(os.path.join(GTFS_PATH, 'stops.csv'), encoding=turkish_encoding, dtype={'stop_id': str})
    
    # --- TEMİZLİK ADIMI 1: Ana veriyi temizle ---
    print(f"   > Raw stops count: {len(stops)}")
    stops.dropna(subset=['stop_lat', 'stop_lon'], inplace=True)
    stops['stop_lat'] = pd.to_numeric(stops['stop_lat'], errors='coerce')
    stops['stop_lon'] = pd.to_numeric(stops['stop_lon'], errors='coerce')
    stops.dropna(subset=['stop_lat', 'stop_lon'], inplace=True)
    print(f"   > Clean stops count: {len(stops)}")

    routes = pd.read_csv(os.path.join(GTFS_PATH, 'routes.csv'), encoding=turkish_encoding, dtype={'route_id': str})
    trips = pd.read_csv(os.path.join(GTFS_PATH, 'trips.csv'), encoding=turkish_encoding, dtype={'trip_id': str, 'route_id': str})
    stop_times = pd.read_csv(os.path.join(GTFS_PATH, 'stop_times.csv'), encoding=turkish_encoding, dtype={'trip_id': str, 'stop_id': str})

    print("   > Merging tables...")
    stop_times = stop_times.merge(trips[['trip_id', 'route_id']], on='trip_id', how="left")
    stop_times = stop_times.merge(routes[['route_id', 'route_short_name', 'route_type']], on='route_id', how='left')
    
    stop_times.sort_values(by=['trip_id', 'stop_sequence'], inplace=True)
    stop_times['seconds_arr'] = stop_times['arrival_time'].apply(parse_gtfs_time)
    stop_times['seconds_dep'] = stop_times['departure_time'].apply(parse_gtfs_time)

    G = nx.DiGraph()

    # --- NODES ---
    for _, row in stops.iterrows():
        G.add_node(
            str(row['stop_id']),
            name=row['stop_name'],
            pos=(float(row['stop_lat']), float(row['stop_lon'])),
            elev=0 
        )

    # --- EDGES ---
    stop_times['next_stop_id'] = stop_times.groupby('trip_id')['stop_id'].shift(-1)
    stop_times['next_arr_seconds'] = stop_times.groupby('trip_id')['seconds_arr'].shift(-1)
    edges_df = stop_times.dropna(subset=['next_stop_id'])

    print("   > Building Graph Edges...")
    for _, row in edges_df.iterrows():
        try:
            travel_time = row['next_arr_seconds'] - row['seconds_dep']
            if travel_time <= 0: travel_time = 30 
            
            u, v = str(row['stop_id']), str(row['next_stop_id'])
            if v.endswith('.0'): v = v[:-2]
            if u.endswith('.0'): u = u[:-2]

            raw_type = row.get('route_type', 3)
            mode = ROUTE_TYPE_MAP.get(raw_type, 'bus')
            
            if mode == 'bus': mode = 'Bus'
            elif mode == 'metro': mode = 'Metro'
            elif mode == 'ferry': mode = 'Ferry'
            
            route_name = str(row.get('route_short_name', ''))

            if G.has_edge(u, v):
                if travel_time < G[u][v]['weight']:
                    G[u][v]['weight'] = travel_time
                    G[u][v]['type'] = mode
                    G[u][v]['route_name'] = route_name
            else:
                G.add_edge(u, v, weight=travel_time, type=mode, route_name=route_name)
        except Exception as e:
            continue

    add_walking_transfers_fast(G, stops, max_dist_meters=500)

    print(f"--- DONE ---")
    print(f"Nodes: {G.number_of_nodes()} | Edges: {G.number_of_edges()}")

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, 'wb') as f:
        pickle.dump(G, f)
    print(f"Graph saved to {OUTPUT_PATH}!")

if __name__ == "__main__":
    build_graph()