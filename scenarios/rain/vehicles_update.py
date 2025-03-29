import xml.etree.ElementTree as ET

# Load vehicle routes file
vehicle_file = r"C:\Users\athar\OneDrive\Documents\Sapan's Project\SUMO\scenarios\rain\vehicles.rou.xml"

# Parse XML
tree = ET.parse(vehicle_file)
root = tree.getroot()

# Get all existing vehicle elements
vehicles = root.findall("vehicle")

# Set batch configuration
batch_size = 5
batch_gap = 60  # 60 seconds between batches
num_batches = 10  # Number of batches to generate (50 -> 100 vehicles)

# Duplicate vehicles to increase count
new_vehicles = []
for batch_number in range(num_batches):
    for i in range(batch_size):
        index = (batch_number * batch_size + i) % len(vehicles)  # Cycle through available vehicles
        original_vehicle = vehicles[index]

        # Create a new vehicle element
        new_vehicle = ET.Element("vehicle", attrib=original_vehicle.attrib)

        # Update ID and departure time
        new_vehicle.set("id", f"{batch_number * batch_size + i}")  # Unique ID
        new_vehicle.set("depart", str(batch_number * batch_gap))  # Batch departure time

        # Copy the route
        route = original_vehicle.find("route")
        if route is not None:
            new_route = ET.SubElement(new_vehicle, "route", attrib=route.attrib)

        new_vehicles.append(new_vehicle)

# Remove old vehicles and add new ones
for vehicle in vehicles:
    root.remove(vehicle)

root.extend(new_vehicles)

# Save changes directly to the same file
tree.write(vehicle_file)

print(f"Updated {vehicle_file} with {num_batches * batch_size} vehicles departing in batches of 5 every 60 seconds.")
