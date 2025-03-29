import xml.etree.ElementTree as ET

# Load vehicle routes file
vehicle_file = r"C:\Users\athar\OneDrive\Documents\Sapan's Project\SUMO\scenarios\rain\vehicles.rou.xml"
tree = ET.parse(vehicle_file)
root = tree.getroot()

# Modify vehicle speeds and add stops at pedestrian crossings
for vehicle in root.findall("vehicle"):
    vehicle.set("departSpeed", "3")  # Slow down all vehicles
    route = vehicle.find("route")
    if route is not None:
        # Add a stop at a pedestrian crossing (example edge)
        stop = ET.SubElement(vehicle, "stop", attrib={
            "edge": "23715305#0",  # Example pedestrian crossing edge
            "duration": "10"  # Stop for 10 seconds
        })

# Save modified vehicles file
tree.write("modified_vehicles.rou.xml")


# Load pedestrian routes file
pedestrian_file = r"C:\Users\athar\OneDrive\Documents\Sapan's Project\SUMO\scenarios\rain\pedestrians.rou.xml"
tree = ET.parse(pedestrian_file)
root = tree.getroot()

# Increase pedestrian traffic by duplicating persons with varied depart times
new_pedestrians = []
for person in root.findall("person"):
    for i in range(3):  # Create 3x more pedestrians
        new_person = ET.Element("person", attrib={
            "id": str(int(person.get("id")) * 10 + i),
            "depart": str(float(person.get("depart")) + i * 2)  # Slightly stagger departures
        })
        walk = person.find("walk")
        if walk is not None:
            new_walk = ET.SubElement(new_person, "walk", attrib=walk.attrib)
        new_pedestrians.append(new_person)

# Append new pedestrians to the root
for new_person in new_pedestrians:
    root.append(new_person)

# Save modified pedestrians file
tree.write("modified_pedestrians.rou.xml")

print("Simulation files modified: Vehicles are slower, pedestrians increased, and crossings prioritized.")
