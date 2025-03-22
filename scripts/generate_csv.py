import csv
from datetime import datetime, timedelta
import random

# Generate historical rain data with timestamps and rainfall intensity (mm/h)
def generate_rain_data(filename, entries=100):
    start_date = datetime(2023, 1, 1, 0, 0, 0)  # Start date
    data = []
    
    for i in range(entries):
        # Increment time by 2 hours for each entry
        timestamp = start_date + timedelta(hours=i*2)
        
        # Simulate rainfall intensity (0-30 mm/h)
        day = (timestamp - start_date).days
        
        if day < 2:  # Days 1-2: No rain
            rainfall = 0.0
        elif day < 4:  # Days 3-4: Light rain (0.1-5.0 mm/h)
            rainfall = round(random.uniform(0.1, 5.0), 1)
        elif day < 6:  # Days 5-6: Moderate rain (5.1-15.0 mm/h)
            rainfall = round(random.uniform(5.1, 15.0), 1)
        elif day < 8:  # Days 7-8: Heavy rain (15.1-30.0 mm/h)
            rainfall = round(random.uniform(15.1, 30.0), 1)
        else:  # Days 9-10: Mixed (random)
            rainfall = round(random.choice([0.0, random.uniform(0.1, 30.0)]), 1)
        
        data.append([timestamp.strftime("%Y-%m-%d %H:%M:%S"), rainfall])
    
    # Save to CSV
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "Rainfall (mm/h)"])
        writer.writerows(data)

# Generate the CSV file
generate_rain_data("historical_rain_data.csv")