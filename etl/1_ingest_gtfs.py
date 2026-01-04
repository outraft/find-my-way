import os
import pickle
import networkx as nx
import pandas as pd

# --- CONFIGURATION ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
GTFS_PATH = os.path.join(PROJECT_ROOT, 'data', 'raw')
OUTPUT_PATH = os.path.join(PROJECT_ROOT, 'data', 'processed', 'istanbul_graph.pkl')
turkish_encoding = 'iso-8859-9'

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

	print("Processing edges (this may take a moment)...")

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

	# Iterate and add edges to the graph
	# Weight: Travel time between stops
	for _, row in edges_df.iterrows():
		travel_time = row['next_arr_seconds'] - row['seconds_dep']

		# We use 'min' to keep only the fastest trip between two stops if multiple exist
		u, v = str(row['stop_id']), str(row['next_stop_id'])

		if v.endswith('.0'):
			v = v[:-2]

		travel_time = row['next_arr_seconds'] - row['seconds_dep']

		if travel_time < 0: continue

		if G.has_edge(u, v):
			if travel_time < G[u][v]['weight']:
				G[u][v]['weight'] = travel_time
		else:
			G.add_edge(u, v, weight=travel_time)

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



