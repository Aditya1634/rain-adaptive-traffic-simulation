import os
import csv
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import random

# ==============================================================
# UPDATE THESE PATHS TO MATCH YOUR PROJECT STRUCTURE
# ==============================================================
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Go up one level from scripts/
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
BASELINE_SCENARIO = os.path.join(PROJECT_ROOT, "scenarios", "baseline")
RAIN_SCENARIO = os.path.join(PROJECT_ROOT, "scenarios", "rain")
HISTORICAL_RAIN_DATA = os.path.join(DATA_DIR, "weather", "historical_rain_data.csv")

# Rain intensity thresholds
RAIN_INTENSITY = {
    "none": {"ped_duration": 30, "veh_speed": 13.89},
    "light": {"ped_duration": 45, "veh_speed": 10.0},
    "moderate": {"ped_duration": 60, "veh_speed": 8.0},
    "heavy": {"ped_duration": 90, "veh_speed": 5.0}
}

def get_rain_intensity(rainfall):
    if rainfall < 0.1:
        return "none"
    elif 0.1 <= rainfall < 5.0:
        return "light"
    elif 5.0 <= rainfall < 15.0:
        return "moderate"
    else:
        return "heavy"

def generate_rain_scenario_routes():
    # Check if paths exist
    if not os.path.exists(HISTORICAL_RAIN_DATA):
        raise FileNotFoundError(f"Rain data file not found at: {HISTORICAL_RAIN_DATA}")
    if not os.path.exists(BASELINE_SCENARIO):
        raise FileNotFoundError(f"Baseline scenario folder not found at: {BASELINE_SCENARIO}")
    os.makedirs(RAIN_SCENARIO, exist_ok=True)  # Create rain scenario folder if missing

    # Read historical rain data
    max_rainfall = 0.0
    with open(HISTORICAL_RAIN_DATA, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rainfall = float(row["Rainfall (mm/h)"])
            if rainfall > max_rainfall:
                max_rainfall = rainfall

    # Determine worst-case intensity
    intensity = get_rain_intensity(max_rainfall)
    ped_duration = RAIN_INTENSITY[intensity]["ped_duration"]
    veh_speed = RAIN_INTENSITY[intensity]["veh_speed"]

    # Modify vehicle routes
    veh_baseline = os.path.join(BASELINE_SCENARIO, "vehicles.rou.xml")
    veh_rain = os.path.join(RAIN_SCENARIO, "vehicles.rou.xml")
    veh_tree = ET.parse(veh_baseline)
    for vType in veh_tree.findall(".//vType"):
        vType.set("maxSpeed", str(veh_speed))
    veh_tree.write(veh_rain)

    # Modify pedestrian routes
    ped_baseline = os.path.join(BASELINE_SCENARIO, "pedestrians.rou.xml")
    ped_rain = os.path.join(RAIN_SCENARIO, "pedestrians.rou.xml")
    ped_tree = ET.parse(ped_baseline)
    for person in ped_tree.findall(".//person"):
        walk_elem = person.find(".//walk")
        if walk_elem is not None:
            walk_elem.set("duration", str(ped_duration))
    ped_tree.write(ped_rain)

    print(f"Rain scenario files generated in: {RAIN_SCENARIO}")

if __name__ == "__main__":
    generate_rain_scenario_routes()