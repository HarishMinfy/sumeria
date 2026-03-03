# main.py

import json
from datetime import datetime
from pathlib import Path
from selection_engine import SelectionEngine

# Load stations JSON (relative to this file)
stations_path = Path(__file__).resolve().parent / "ground_stations.json"
with open(stations_path, "r", encoding="utf-8") as f:
    stations = json.load(f)["stations"]

engine = SelectionEngine()

request = {
    "tle_line1": "1 25544U 98067A   26050.82880434  .00062824  00000+0  11723-2 0  9997",
    "tle_line2": "2 25544  51.6323 160.6397 0008552 112.9938 247.1953 15.48149648553685",
    # Shared-pass day (UTC) where both GS-OPT-001 and the 5 USA test stations have >=20deg passes
    "start_time": datetime(2026, 2, 25, 0, 0, 0),
    "end_time": datetime(2026, 2, 26, 0, 0, 0),
    "required_standard": "CCSDS-OPTICAL-1.0",
    "required_wavelength_nm": 1550,
    "min_elevation_deg": 10
}

results = engine.run_selection(stations, request)

print("\nBest Stations:\n")
for r in results[:10]:
    print(r)
