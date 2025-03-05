# analyze_results.py
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

def load_simulation_results(baseline_file, adaptive_file):
    """Load results from both simulation runs"""
    baseline = pd.read_csv(baseline_file)
    adaptive = pd.read_csv(adaptive_file)
    
    # Add simulation type column
    baseline['simulation'] = 'Baseline'
    adaptive['simulation'] = 'Rain-Adaptive'
    
    # Combine datasets
    combined = pd.concat([baseline, adaptive], ignore_index=True)
    return baseline, adaptive, combined

def calculate_improvement_metrics(baseline, adaptive):
    """Calculate improvement metrics between baseline and adaptive approaches"""
    metrics = {}
    
    # Vehicle wait time improvement
    metrics['vehicle_wait_time_change'] = (
        np.mean(adaptive['vehicle_wait_times']) - np.mean(baseline['vehicle_wait_times'])
    ) / np.mean(baseline['vehicle_wait_times']) * 100
    
    # Pedestrian wait time improvement
    metrics['pedestrian_wait_time_change'] = (
        np.mean(adaptive['pedestrian_wait_times']) - np.mean(baseline['pedestrian_wait_times'])
    ) / np.mean(baseline['pedestrian_wait_times']) * 100
    
    # Traffic flow improvement
    metrics['traffic_flow_change'] = (
        np.sum(adaptive['traffic_flow']) - np.sum(baseline['traffic_flow'])
    ) / np.sum(baseline['traffic_flow']) * 100
    
    return metrics

def plot_wait_time_comparisons(combined):
    """Create wait time comparison plots"""
    # Set style
    sns.set(style="whitegrid")
    
    # Create figure with multiple subplots
    fig, axs = plt.subplots(2, 1, figsize=(12, 10))
    
    # Vehicle wait times by rain intensity
    sns.boxplot(x='rain_intensity', y='vehicle_wait_times', hue='simulation', 
                data=combined, ax=axs[0])
    axs[0].set_title('Vehicle Wait Times by Rain Intensity')
    axs[0].set_ylabel('Wait Time (seconds)')
    axs[0].set_xlabel('Rain Intensity')
    
    # Pedestrian wait times by rain intensity
    sns.boxplot(x='rain_intensity', y='pedestrian_wait_times', hue='simulation', 
                data=combined, ax=axs[1])
    axs[1].set_title('Pedestrian Wait Times by Rain Intensity')
    axs[1].set_ylabel('Wait Time (seconds)')
    axs[1].set_xlabel('Rain Intensity')
    
    plt.tight_layout()
    plt.savefig('wait_time_comparison.png')
    plt.close()

def plot_traffic_flow(combined):
    """Plot traffic flow comparisons"""
    # Group by rain intensity and simulation type
    flow_by_rain = combined.groupby(['rain_intensity', 'simulation'])['traffic_flow'].sum().reset_index()
    
    plt.figure(figsize=(10, 6))
    sns.barplot(x='rain_intensity', y='traffic_flow', hue='simulation', data=flow_by_rain)
    plt.title('Traffic Flow by Rain Intensity')
    plt.ylabel('Vehicles per Hour')
    plt.xlabel('Rain Intensity')
    plt.savefig('traffic_flow_comparison.png')
    plt.close()

def create_heatmap(combined):
    """Create a heatmap showing the effectiveness of rain adaptation by intensity"""
    # Calculate effectiveness ratio (adaptive/baseline) for different metrics
    pivot_data = {}
    
    # For vehicle wait times (lower is better)
    vwt = combined.pivot_table(
        values='vehicle_wait_times', 
        index='rain_intensity',
        columns='simulation'
    )
    pivot_data['vehicle_wait_times'] = vwt['Baseline'] / vwt['Rain-Adaptive']
    
    # For pedestrian wait times (lower is better)
    pwt = combined.pivot_table(
        values='pedestrian_wait_times', 
        index='rain_intensity',
        columns='simulation'
    )
    pivot_data['pedestrian_wait_times'] = pwt['Baseline'] / pwt['Rain-Adaptive']
    
    # For traffic flow (higher is better)
    tf = combined.pivot_table(
        values='traffic_flow', 
        index='rain_intensity',
        columns='simulation',
        aggfunc='sum'
    )
    pivot_data['traffic_flow'] = tf['Rain-Adaptive'] / tf['Baseline']
    
    # Convert to DataFrame
    heatmap_data = pd.DataFrame(pivot_data)
    
    # Create heatmap
    plt.figure(figsize=(10, 8))
    sns.heatmap(heatmap_data, annot=True, cmap='YlGnBu', linewidths=.5)
    plt.title('Effectiveness Ratio of Rain-Adaptive vs. Baseline')
    plt.savefig('effectiveness_heatmap.png')
    plt.close()

def main():
    # Load results
    baseline, adaptive, combined = load_simulation_results(
        'baseline_results.csv',
        'adaptive_results.csv'
    )
    
    # Calculate improvement metrics
    metrics = calculate_improvement_metrics(baseline, adaptive)
    print("Improvement Metrics:")
    for metric, value in metrics.items():
        print(f"  {metric}: {value:.2f}%")
    
    # Create visualizations
    plot_wait_time_comparisons(combined)
    plot_traffic_flow(combined)
    create_heatmap(combined)
    
    print("Analysis complete! Visualizations saved to current directory.")

if __name__ == "__main__":
    main()