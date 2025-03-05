#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wait time visualization for rain-adaptive traffic simulation.
This script generates visualizations of waiting times at intersections.
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

def load_wait_time_data(file_path):
    """
    Load wait time data from simulation output file.
    
    Args:
        file_path (str): Path to the wait time data file
        
    Returns:
        pandas.DataFrame: Loaded wait time data
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
        print(f"Error loading wait time data: {e}")
        return None

def plot_wait_times_over_time(df, weather_data=None, output_path=None):
    """
    Plot average wait times over time with optional weather overlay.
    
    Args:
        df (pandas.DataFrame): Wait time data with 'time' and 'avg_wait_time' columns
        weather_data (pandas.DataFrame, optional): Weather data with 'time' and 'rainfall' columns
        output_path (str, optional): Path to save the plot
    """
    plt.figure(figsize=(12, 6))
    
    # Plot wait times
    plt.plot(df['time'], df['avg_wait_time'], label='Average Wait Time (seconds)', color='purple')
    
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
    plt.ylabel('Wait Time (seconds)')
    plt.title('Average Wait Times Over Time')
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

def plot_wait_time_comparison(baseline_df, adaptive_df, output_path=None):
    """
    Plot comparison of wait times between baseline and adaptive strategies.
    
    Args:
        baseline_df (pandas.DataFrame): Baseline simulation data
        adaptive_df (pandas.DataFrame): Adaptive simulation data
        output_path (str, optional): Path to save the plot
    """
    plt.figure(figsize=(12, 6))
    
    plt.plot(baseline_df['time'], baseline_df['avg_wait_time'], 
             label='Baseline Strategy', color='red', alpha=0.8)
    plt.plot(adaptive_df['time'], adaptive_df['avg_wait_time'], 
             label='Rain-Adaptive Strategy', color='green', alpha=0.8)
    
    # Calculate and display improvement percentage
    avg_baseline = baseline_df['avg_wait_time'].mean()
    avg_adaptive = adaptive_df['avg_wait_time'].mean()
    improvement = ((avg_baseline - avg_adaptive) / avg_baseline) * 100
    
    plt.axhline(y=avg_baseline, color='red', linestyle='--', alpha=0.5)
    plt.axhline(y=avg_adaptive, color='green', linestyle='--', alpha=0.5)
    
    plt.xlabel('Time')
    plt.ylabel('Wait Time (seconds)')
    plt.title(f'Wait Time Comparison\nAverage Improvement: {improvement:.2f}%')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()
    
    # Add annotation for mean values
    plt.annotate(f'Avg: {avg_baseline:.1f}s', xy=(baseline_df['time'].iloc[-10], avg_baseline),
                 xytext=(5, 5), textcoords='offset points', color='red')
    plt.annotate(f'Avg: {avg_adaptive:.1f}s', xy=(adaptive_df['time'].iloc[-10], avg_adaptive),
                 xytext=(5, 5), textcoords='offset points', color='green')
    
    plt.tight_layout()
    
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path, dpi=300)
        print(f"Comparison plot saved to {output_path}")
    else:
        plt.show()
    
    plt.close()

def plot_intersection_wait_times(df, output_path=None):
    """
    Plot wait times by intersection.
    
    Args:
        df (pandas.DataFrame): DataFrame with 'intersection_id' and 'avg_wait_time' columns
        output_path (str, optional): Path to save the plot
    """
    # Group by intersection_id and calculate average wait time
    intersection_wait = df.groupby('intersection_id')['avg_wait_time'].mean().sort_values(ascending=False)
    
    # Only show top 15 intersections if there are many
    if len(intersection_wait) > 15:
        intersection_wait = intersection_wait.head(15)
        title_suffix = " (Top 15)"
    else:
        title_suffix = ""
    
    plt.figure(figsize=(12, 8))
    
    # Create horizontal bar chart
    bars = plt.barh(intersection_wait.index, intersection_wait.values, color=sns.color_palette("Purples_r", len(intersection_wait)))
    
    # Add value labels
    for bar in bars:
        width = bar.get_width()
        plt.text(width + 1, bar.get_y() + bar.get_height()/2.,
                 f'{width:.1f}s', ha='left', va='center')
    
    plt.xlabel('Average Wait Time (seconds)')
    plt.ylabel('Intersection ID')
    plt.title(f'Average Wait Times by Intersection{title_suffix}')
    plt.grid(axis='x', linestyle='--', alpha=0.7)
    plt.tight_layout()
    
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path, dpi=300)
        print(f"Intersection wait time plot saved to {output_path}")
    else:
        plt.show()
    
    plt.close()

def plot_wait_time_distribution(baseline_df, adaptive_df, output_path=None):
    """
    Plot distribution of wait times for baseline and adaptive strategies.
    
    Args:
        baseline_df (pandas.DataFrame): Baseline simulation data
        adaptive_df (pandas.DataFrame): Adaptive simulation data
        output_path (str, optional): Path to save the plot
    """
    plt.figure(figsize=(10, 6))
    
    # Create KDE plots
    sns.kdeplot(baseline_df['avg_wait_time'], label='Baseline Strategy', 
                color='red', fill=True, alpha=0.3)
    sns.kdeplot(adaptive_df['avg_wait_time'], label='Rain-Adaptive Strategy', 
                color='green', fill=True, alpha=0.3)
    
    # Add vertical lines for medians
    plt.axvline(baseline_df['avg_wait_time'].median(), color='red', linestyle='--')
    plt.axvline(adaptive_df['avg_wait_time'].median(), color='green', linestyle='--')
    
    # Calculate median improvement
    baseline_median = baseline_df['avg_wait_time'].median()
    adaptive_median = adaptive_df['avg_wait_time'].median()
    median_improvement = ((baseline_median - adaptive_median) / baseline_median) * 100
    
    plt.xlabel('Wait Time (seconds)')
    plt.ylabel('Density')
    plt.title(f'Wait Time Distribution\nMedian Improvement: {median_improvement:.2f}%')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()
    
    # Add annotation for median values
    plt.annotate(f'Median: {baseline_median:.1f}s', xy=(baseline_median, 0),
                 xytext=(0, 10), textcoords='offset points', color='red',
                 arrowprops=dict(arrowstyle='->', color='red'))
    plt.annotate(f'Median: {adaptive_median:.1f}s', xy=(adaptive_median, 0),
                 xytext=(0, 10), textcoords='offset points', color='green',
                 arrowprops=dict(arrowstyle='->', color='green'))
    
    plt.tight_layout()
    
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path, dpi=300)
        print(f"Wait time distribution plot saved to {output_path}")
    else:
        plt.show()
    
    plt.close()

def main():
    """Main function to generate wait time visualizations."""
    # Set paths
    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    output_dir = data_dir / "output"
    
    # Example usage
    baseline_file = output_dir / "baseline_simulation" / "wait_times.csv"
    adaptive_file = output_dir / "adaptive_simulation" / "wait_times.csv"
    weather_file = output_dir / "weather" / "rainfall_data.csv"
    
    # Create visualization output directory
    vis_dir = output_dir / "visualizations"
    os.makedirs(vis_dir, exist_ok=True)
    
    # Load data
    if baseline_file.exists() and adaptive_file.exists():
        baseline_data = load_wait_time_data(str(baseline_file))
        adaptive_data = load_wait_time_data(str(adaptive_file))
        
        # Load weather data if available
        weather_data = None
        if weather_file.exists():
            weather_data = pd.read_csv(weather_file)
        
        # Generate visualizations
        if baseline_data is not None and adaptive_data is not None:
            # Plot wait times over time for adaptive strategy
            plot_wait_times_over_time(
                adaptive_data, 
                weather_data, 
                output_path=str(vis_dir / "wait_times_over_time.png")
            )
            
            # Plot comparison between baseline and adaptive strategies
            plot_wait_time_comparison(
                baseline_data, 
                adaptive_data, 
                output_path=str(vis_dir / "wait_time_comparison.png")
            )
            
            # Plot wait time distribution
            plot_wait_time_distribution(
                baseline_data,
                adaptive_data,
                output_path=str(vis_dir / "wait_time_distribution.png")
            )
            
            # If we have intersection-specific data
            if 'intersection_id' in adaptive_data.columns:
                plot_intersection_wait_times(
                    adaptive_data,
                    output_path=str(vis_dir / "intersection_wait_times.png")
                )
            else:
                print("Intersection data not available in the dataset")
        else:
            print("Failed to load wait time data")
    else:
        print(f"Input files not found. Please run the simulation first.")

if __name__ == "__main__":
    main()