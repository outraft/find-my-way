<h1 align="center">Find My Way</h1>

<p align="center">
	<b>The ultimate navigation companion for Istanbul.</b>
</p>

# What is this app?

This app helps foreigners and/or tourists with transportation through Istanbul. The app has every possible vehicle and route imaginable, from <strong>stop A</strong> to <strong>stop B</strong>.

# Techstack

Frontend: React.js

Backend: Python

Data Processing: ETL (Exact, Transform, Load) pipelines for transit data

Routing Engine: Custom implementation using KD-Trees and Multi-Graph algorithms.

# Getting Started
Prerequisites:
* Node.js & npm
* Python 3.8+
	

# Installation

1. Clone the repo

```
git clone github.com/outraft/temp-project-3/
```


2. Install Frontend dependencies

```
npm install
```

3. Run the data pipeline

```
python etl/ingest_gtfs
```

4. Start the app

```
npm start
```

# Data Files

**WARNING**: The data is **very, very old**, such that most stops on the map (e.g. Atlas University Stop, Yildiz Technical University), some types of vehicles (e.g. Metrobus) and the roads given (e.g. Algorithm suggests going back to Besiktas is more viable than using a bus to go to Seyrantepe station) are not accurate. As the [data given by IETT](https://data.ibb.gov.tr/dataset/public-transport-gtfs-data) progresses, the app will also progress.


# File Structure

```
find-my-way/
|___ api/
|___ core/
|___ data/
|    |___ processed/
|    |___ raw/
|___ etl/
|___ front_end/
|___ map_project/
|___ public/
|___ src/
|___ tests/
|___ .gitignore
|___ README.md
|___ debug.py
|___ package-lock.json
|___ package.json
```


> Made by Commitment Issues, with upmost love for the final project ❤️
