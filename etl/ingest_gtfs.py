import os
import pickle
import networkx as nx
import pandas as pd
import math
from typing import List, Tuple

# --- CONFIGURATION ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
GTFS_PATH = os.path.join(PROJECT_ROOT, 'data', 'raw')
OUTPUT_PATH = os.path.join(PROJECT_ROOT, 'data', 'processed', 'istanbul_graph.pkl')
turkish_encoding = 'iso-8859-9'

# GTFS Route Type Mapping
# Source: Official GTFS Reference
ROUTE_TYPE_MAP = {
	0: 'tram',          # Tram / Streetcar
	1: 'metro',         # Subway
	2: 'rail',          # Marmaray / Intercity
	3: 'bus',           # Standard IETT Bus
	4: 'ferry',         # Vapur / Sea Taxi
	5: 'cable_tram',    # (Rare in Istanbul)
	6: 'gondola',       # Aerial lift (e.g., Macka-Taskisla)
	7: 'funicular',     # Tünel / Kabatas-Taksim
	9: 'minibus',       # Dolmus (If in data)
	10: 'taxi_minibus',
	11: 'trolleybus',   # Sometimes used for Metrobus
	12: 'monorail'      # (Rare)
}

# HELPER -> Parses time
def parse_gtfs_time(time_str : str) -> int:
	"""
	Converts the GTFS time (HH:MM:SS) to seconds from midnight.
	Handles time past 24:00. (e.g., 25:30:00)

	Arguments: time_str -> string

	Returns -> integer value to the midnight
	"""

	if pd.isna(time_str): return None

	h, m, s = map(int, time_str.split(":"))
	return h * 3600 + m * 60 + s

# HELPER -> Calculates a circular distance with given R.
def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
	"""
	Calculate the great circle distance between two points on earth (specified in decimal degrees).
	Returns distance in meters.
	"""

	R = 6371000
	phi1, phi2 = math.radians(lat1), math.radians(lat2)
	dphi = math.radians(lat2-lat1)
	dlambda = math.radians(lon2-lon1)

	a = math.sin(dphi / 2)**2 + \
		math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
	c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

	return R * c

def add_walking_transfers(G: nx.DiGraph, stops_df: pd.DataFrame, max_dist_meters: int = 300, walk_speed_mps = 1.2) -> None:
	"""
	Finds stops close to each other and adds bi-directional walking edges.
	"""

	print(f"5. Generating Walking transfers (< {max_dist_meters} m)...")

	# Create a list of tuples to iterate faster than DataFrame rows
	# format: (id, lat, lon)
	stop_nodes: List[Tuple[any, float, float]] = list(zip(stops_df['stop_id'], stops_df['stop_lat'], stops_df['stop_lon']))

	transfers_added = 0
	total_stops = len(stop_nodes)

	for i in range(total_stops):
		id_a, lat_a, lon_a = stop_nodes[i]

		# Check for i+1 to avoid dupes
		for j in range(i + 1, total_stops):
			id_b, lat_b, lon_b = stop_nodes[j]

			# Check if the diffrence is huge, if so skip entirely.
			# Measure for better performance.

			if abs(lat_a - lat_b) > 0.01 or abs(lon_a - lon_b) > 0.01:
				continue

			dist = haversine(lat1=lat_a, lon1=lon_a, lat2=lat_b, lon2=lon_b)

			if dist <= max_dist_meters:
				walk_time = int(dist / walk_speed_mps)

				# Walking works both ways.
				G.add_edge(str(id_a), str(id_b), weight=walk_time, type='walk')
				G.add_edge(str(id_b), str(id_a), weight=walk_time, type='walk')

				transfers_added += 1
		if i % 500 == 0:
			print(f"Scanned {i}/{total_stops} stops...")

	print(f"   > Added {transfers_added * 2} walking connections.")

def build_graph():
	print("Loading the GTFS data...")
	# 1. Load the stops, also can be told as nodes.
	stops = pd.read_csv(
		os.path.join(GTFS_PATH, 'stops.csv'),
		encoding=turkish_encoding,
		dtype={'stop_id': str}
	)
	# Keeping only the required identifier for MVP product, might add more later.
	stops = stops[['stop_id', 'stop_name', 'stop_lat', 'stop_lon']]

	# NEW STEP: LOAD ROUTES AND TRIPS
	print("   > Loading Routes and Trips to identify transport types...")

	routes = pd.read_csv(
		os.path.join(GTFS_PATH, 'routes.csv'),
		encoding=turkish_encoding,
		dtype={'route_id': str}
	)
	routes = routes[['route_id', 'route_short_name', 'route_type']]

	trips = pd.read_csv(
		os.path.join(GTFS_PATH, 'trips.csv'),
		encoding=turkish_encoding,
		dtype={'trip_id': str, 'route_id': str}
	)

	trips = trips[['trip_id', 'route_id']]
	# END NEW STEP 1


	# 2. Load the stop times, also known as edges.
	# (THIS FILE IS HUUUUUGE. might need optimization, will see later. -ersin).
	stop_times = pd.read_csv(
		os.path.join(GTFS_PATH, 'stop_times.csv'),
		encoding=turkish_encoding,
		dtype={'trip_id': str, 'stop_id': str}
		)
	stop_times = stop_times[['trip_id', 'stop_id', 'arrival_time', 'departure_time', 'stop_sequence']]
	# ! WARNING: 'stop_sequence' has a specefic condition, where the number will always go up but will not be consecutive.
	# ? e.g., first station might be stop_sequence = 1, but the second station might be stop_sequence = 40. do add them in a list to show queue of stops upcoming.
	# NEW SECTION 2: MERGE TABLES
	print("   > Merging tables...")

	# 1. Attach route_id to every stop_time row
	stop_times = stop_times.merge(trips, on='trip_id', how="left")

	# 2. Attach route_type and name to every row
	stop_times = stop_times.merge(routes, on='route_id', how='left')

	print("   > Processing edges (this may take a moment)...")

	# Sorting to see the main queue of stops.
	stop_times = stop_times.sort_values(by=['trip_id', 'stop_sequence'])

	# Calculate travel time in seconds.
	stop_times['seconds_arr'] = stop_times['arrival_time'].apply(parse_gtfs_time)
	stop_times['seconds_dep'] = stop_times['departure_time'].apply(parse_gtfs_time)

	# Create the graph

	G = nx.DiGraph()

	# Adding the nodes (stops) w.r.t their positions into the graph.
	for _, row in stops.iterrows():
		G.add_node(
			row['stop_id'],
			name=row['stop_name'],
			pos=(row['stop_lat'], row['stop_lon'])
		)

	# Add edges (Trip Segments)
	# We create a "Next Stop" column to link current stop to the next one in the same trip
	stop_times['next_stop_id'] = stop_times.groupby('trip_id')['stop_id'].shift(-1)
	stop_times['next_arr_seconds'] = stop_times.groupby('trip_id')['seconds_arr'].shift(-1)

	# Drop the last stop of every trip (no "next stop" for last stop)
	edges_df = stop_times.dropna(subset=['next_stop_id'])

	# --- DEBUG STATEMENTS ---
	print(f"DEBUG: Total rows in stop_times: {len(stop_times)}")
	print(f"DEBUG: Rows with valid next stops (edges): {len(edges_df)}")

	if not edges_df.empty:
		print("DEBUG: Sample Edge Data:")
		print(edges_df[['trip_id', 'stop_id', 'next_stop_id', 'seconds_dep', 'next_arr_seconds']].head(3))

	stops_set = set(stops['stop_id'].astype(str))
	times_set = set(stop_times['stop_id'].astype(str))
	common = stops_set.intersection(times_set)
	print(f"DEBUG: Stops in 'stops.txt': {len(stops_set)}")
	print(f"DEBUG: Stops in 'stop_times.txt': {len(times_set)}")
	print(f"DEBUG: Overlapping Stops (Matching IDs): {len(common)}")

	if len(common) == 0:
		print("CRITICAL ERROR: No stop IDs match! Check for whitespace or type format.")
		print(f"Example Stop ID from stops.txt: '{list(stops_set)[0]}'")
		print(f"Example Stop ID from stop_times.txt: '{list(times_set)[0]}'")

	# --- DEBUG ENDED ---

	print("   > Building Graph Edges...")
	# Iterate and add edges to the graph
	# Weight: Travel time between stops
	for _, row in edges_df.iterrows():
		travel_time = row['next_arr_seconds'] - row['seconds_dep']
		if travel_time < 0: continue

		# We use 'min' to keep only the fastest trip between two stops if multiple exist
		u, v = str(row['stop_id']), str(row['next_stop_id'])

		if v.endswith('.0'):
			v = v[:-2]

		raw_type = row.get('route_type', 3) # Default to 3 (Bus)
		mode = ROUTE_TYPE_MAP.get(raw_type, 'bus')
		# 2. Get Route Name (e.g., "500T", "M2")
		route_name = row.get('route_short_name', 'nil')

		travel_time = row['next_arr_seconds'] - row['seconds_dep']


		if G.has_edge(u, v):
			if travel_time < G[u][v]['weight']:
				G[u][v]['weight'] = travel_time
				G[u][v]['type'] = mode # <--- Save Type
				G[u][v]['route_name'] = route_name # <--- Save Name
		else:
			G.add_edge(u, v, weight=travel_time, type=mode, route_name=route_name)

	add_walking_transfers(G, stops, max_dist_meters=300)

	print(f"--- DONE ---")
	print(f"Graph Statistics:")
	print(f"Nodes (Stops): {G.number_of_nodes()}")
	print(f"Edges (Routes): {G.number_of_edges()}")

	os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
	with open(OUTPUT_PATH, 'wb') as f:
		pickle.dump(G, f)

	print(f"Graph saved to {OUTPUT_PATH}!")

if __name__ == "__main__":
	build_graph()



