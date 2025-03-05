# visualize_rain_impact.py
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

def create_rain_impact_visualization(results_file):
    """Create visualizations showing the impact of rain on traffic parameters"""
    # Load simulation results
    data = pd.read_csv(results_file)
    
    # Ensure rain intensity is treated as categorical
    data['rain_intensity'] = pd.Categorical(
        data['rain_intensity'],
        categories=['no_rain', 'light_rain', 'moderate_rain', 'heavy_rain'],
        ordered=True
    )
    
    # Create figure with multiple subplots
    fig, axs = plt.subplots(3, 1, figsize=(12, 15))
    
    # 1. Vehicle Speed vs Rain Intensity
    # We'll calculate this from the data if available, or use approximation
    if 'vehicle_speed' in data.columns:
        vehicle_speed = data.groupby('rain_intensity')['vehicle_speed'].mean()
    else:
        # Approximate based on wait times (inverse relationship)
        wait_by_rain = data.groupby('rain_intensity')['vehicle_wait_times'].mean()
        baseline = wait_by_rain['no_rain']
        vehicle_speed = pd.Series({
            'no_rain': 50,  # km/h baseline
            'light_rain': 50 * (baseline / wait_by_rain['light_rain']),
            'moderate_rain': 50 * (baseline / wait_by_rain['moderate_rain']),
            'heavy_rain': 50 * (baseline / wait_by_rain['heavy_rain'])
        })
    
    sns.barplot(x=vehicle_speed.index, y=vehicle_speed.values, ax=axs[0], palette='Blues_r')
    axs[0].set_title('Average Vehicle Speed by Rain Intensity')
    axs[0].set_ylabel('Speed (km/h)')
    axs[0].set_xlabel('Rain Intensity')
    
    # 2. Pedestrian Wait Times vs Rain Intensity
    ped_wait = data.groupby('rain_intensity')['pedestrian_wait_times'].mean()
    sns.barplot(x=ped_wait.index, y=ped_wait.values, ax=axs[1], palette='Reds')
    axs[1].set_title('Average Pedestrian Wait Time by Rain Intensity')
    axs[1].set_ylabel('Wait Time (seconds)')
    axs[1].set_xlabel('Rain Intensity')
    
    # 3. Traffic Flow vs Rain Intensity
    traffic_flow = data.groupby('rain_intensity')['traffic_flow'].sum()
    sns.barplot(x=traffic_flow.index, y=traffic_flow.values, ax=axs[2], palette='Greens')
    axs[2].set_title('Total Traffic Flow by Rain Intensity')
    axs[2].set_ylabel('Vehicles per Hour')
    axs[2].set_xlabel('Rain Intensity')
    
    plt.tight_layout()
    plt.savefig('rain_impact_visualization.png')
    plt.close()
    
    print("Rain impact visualization created!")

if __name__ == "__main__":
    create_rain_impact_visualization('adaptive_results.csv')