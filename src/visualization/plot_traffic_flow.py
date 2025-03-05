#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Traffic flow visualization for rain-adaptive traffic simulation.
This script generates visualizations of traffic flow metrics based on simulation results.
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import json
import sys

# Add the parent directory to the system path to import project modules
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from src.analysis.traffic_metrics import calculate_flow_rate

def load_traffic_data(file_path):
    """
    Load traffic data from simulation output file.
    
    Args:
        file_path (str): Path to the traffic data file
        
    Returns:
        pandas.DataFrame: Loaded traffic data
    """
    try:
        if file_path.endswith('.csv'):
            return pd.read_csv(file_path)
        elif file_path.endswith('.json'):
            with open(file_path, 'r') as f:
                return pd.DataFrame(json.load(f))
        else:
            raise ValueError(f"Unsupported file format: {file_path}")
    except Exception as e:
        print(f"Error loading traffic data: {e}")
        return None

def plot_flow_over_time(df, weather_data=None, output_path=None):
    """
    Plot traffic flow over time with optional weather overlay.
    
    Args:
        df (pandas.DataFrame): Traffic data with 'time' and 'flow_rate' columns
        weather_data (pandas.DataFrame, optional): Weather data with 'time' and 'rainfall' columns
        output_path (str, optional): Path to save the plot
    """
    plt.figure(figsize=(12, 6))
    
    # Plot traffic flow
    plt.plot(df['time'], df['flow_rate'], label='Traffic Flow (vehicles/hour)', color='blue')
    
    # Add weather data if available
    if weather_data is not None:
        ax2 = plt.twinx()
        ax2.plot(weather_data['time'], weather_data['rainfall'], label='Rainfall (mm/h)', 
                 color='darkblue', linestyle='--', alpha=0.7)
        ax2.set_ylabel('Rainfall (mm/h)', color='darkblue')
        ax2.tick_params(axis='y', labelcolor='darkblue')
        ax2.fill_between(weather_data['time'], weather_data['rainfall'], 
                         alpha=0.2, color='lightblue')
    
    plt.xlabel('Time')
    plt.ylabel('Flow Rate (vehicles/hour)')
    plt.title('Traffic Flow Over Time')
    plt.grid(True, linestyle='--', alpha=0.7)
    
    # Handle legend for both y-axes if weather data is included
    if weather_data is not None:
        lines1, labels1 = plt.gca().get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        plt.legend(lines1 + lines2, labels1 + labels2, loc='upper right')
    else:
        plt.legend()
    
    plt.tight_layout()
    
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path, dpi=300)
        print(f"Plot saved to {output_path}")
    else:
        plt.show()
    
    plt.close()

def plot_flow_comparison(baseline_df, adaptive_df, output_path=None):
    """
    Plot comparison of traffic flow between baseline and adaptive strategies.
    
    Args:
        baseline_df (pandas.DataFrame): Baseline simulation data
        adaptive_df (pandas.DataFrame): Adaptive simulation data
        output_path (str, optional): Path to save the plot
    """
    plt.figure(figsize=(12, 6))
    
    plt.plot(baseline_df['time'], baseline_df['flow_rate'], 
             label='Baseline Strategy', color='red', alpha=0.8)
    plt.plot(adaptive_df['time'], adaptive_df['flow_rate'], 
             label='Rain-Adaptive Strategy', color='green', alpha=0.8)
    
    # Calculate and display improvement percentage
    avg_baseline = baseline_df['flow_rate'].mean()
    avg_adaptive = adaptive_df['flow_rate'].mean()
    improvement = ((avg_adaptive - avg_baseline) / avg_baseline) * 100
    
    plt.axhline(y=avg_baseline, color='red', linestyle='--', alpha=0.5)
    plt.axhline(y=avg_adaptive, color='green', linestyle='--', alpha=0.5)
    
    plt.xlabel('Time')
    plt.ylabel('Flow Rate (vehicles/hour)')
    plt.title(f'Traffic Flow Comparison\nAverage Improvement: {improvement:.2f}%')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()
    
    # Add annotation for mean values
    plt.annotate(f'Avg: {avg_baseline:.1f}', xy=(baseline_df['time'].iloc[-10], avg_baseline),
                 xytext=(5, 5), textcoords='offset points', color='red')
    plt.annotate(f'Avg: {avg_adaptive:.1f}', xy=(adaptive_df['time'].iloc[-10], avg_adaptive),
                 xytext=(5, 5), textcoords='offset points', color='green')
    
    plt.tight_layout()
    
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path, dpi=300)
        print(f"Comparison plot saved to {output_path}")
    else:
        plt.show()
    
    plt.close()

def plot_flow_by_rain_intensity(df, output_path=None):
    """
    Plot traffic flow by rain intensity categories.
    
    Args:
        df (pandas.DataFrame): DataFrame with 'flow_rate' and 'rain_intensity' columns
        output_path (str, optional): Path to save the plot
    """
    # Define rain intensity categories
    rain_categories = {
        'No Rain': (0, 0.1),
        'Light Rain': (0.1, 2.5),
        'Moderate Rain': (2.5, 7.6),
        'Heavy Rain': (7.6, 50),
        'Extreme Rain': (50, float('inf'))
    }
    
    # Create a new column for rain categories
    df['rain_category'] = 'Unknown'
    for category, (lower, upper) in rain_categories.items():
        mask = (df['rain_intensity'] >= lower) & (df['rain_intensity'] < upper)
        df.loc[mask, 'rain_category'] = category
    
    # Group by rain category and calculate average flow rate
    category_flow = df.groupby('rain_category')['flow_rate'].mean().reindex(rain_categories.keys())
    
    plt.figure(figsize=(10, 6))
    
    # Create bar chart
    bars = plt.bar(category_flow.index, category_flow.values, color=sns.color_palette("Blues_r", len(category_flow)))
    
    # Add value labels on top of bars
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 5,
                 f'{height:.1f}', ha='center', va='bottom')
    
    plt.xlabel('Rain Intensity Category')
    plt.ylabel('Average Flow Rate (vehicles/hour)')
    plt.title('Traffic Flow by Rain Intensity')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.ylim(0, max(category_flow.values) * 1.15)  # Add space for text labels
    
    plt.tight_layout()
    
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path, dpi=300)
        print(f"Rain intensity plot saved to {output_path}")
    else:
        plt.show()
    
    plt.close()

def main():
    """Main function to generate traffic flow visualizations."""
    # Set paths
    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    output_dir = data_dir / "output"
    
    # Example usage
    baseline_file = output_dir / "baseline_simulation" / "traffic_flow.csv"
    adaptive_file = output_dir / "adaptive_simulation" / "traffic_flow.csv"
    weather_file = output_dir / "weather" / "rainfall_data.csv"
    
    # Create visualization output directory
    vis_dir = output_dir / "visualizations"
    os.makedirs(vis_dir, exist_ok=True)
    
    # Load data
    if baseline_file.exists() and adaptive_file.exists():
        baseline_data = load_traffic_data(str(baseline_file))
        adaptive_data = load_traffic_data(str(adaptive_file))
        
        # Load weather data if available
        weather_data = None
        if weather_file.exists():
            weather_data = pd.read_csv(weather_file)
        
        # Generate visualizations
        if baseline_data is not None and adaptive_data is not None:
            # Plot traffic flow over time for adaptive strategy
            plot_flow_over_time(
                adaptive_data, 
                weather_data, 
                output_path=str(vis_dir / "traffic_flow_time.png")
            )
            
            # Plot comparison between baseline and adaptive strategies
            plot_flow_comparison(
                baseline_data, 
                adaptive_data, 
                output_path=str(vis_dir / "traffic_flow_comparison.png")
            )
            
            # If we have rain intensity data
            if 'rain_intensity' in adaptive_data.columns:
                plot_flow_by_rain_intensity(
                    adaptive_data,
                    output_path=str(vis_dir / "traffic_flow_by_rain.png")
                )
            else:
                print("Rain intensity data not available in the dataset")
        else:
            print("Failed to load traffic data")
    else:
        print(f"Input files not found. Please run the simulation first.")

if __name__ == "__main__":
    main()