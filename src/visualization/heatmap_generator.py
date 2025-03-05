#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Heatmap generator for rain-adaptive traffic simulation.
This script creates spatial heatmaps showing the effectiveness of the adaptive strategy.
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import seaborn as sns
import folium
from folium.plugins import HeatMap
from pathlib import Path
import json
import sys
from matplotlib.colors import LinearSegmentedColormap

# Add the parent directory to the system path to import project modules
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

def load_spatial_data(file_path):
    """
    Load spatial simulation data from file.
    
    Args:
        file_path (str): Path to the simulation data file
        
    Returns:
        pandas.DataFrame: Loaded simulation data
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
        print(f"Error loading spatial data: {e}")
        return None

def calculate_improvement_metrics(baseline_df, adaptive_df):
    """
    Calculate improvement metrics between baseline and adaptive strategies.
    
    Args:
        baseline_df (pandas.DataFrame): Baseline simulation data
        adaptive_df (pandas.DataFrame): Adaptive simulation data
        
    Returns:
        pandas.DataFrame: DataFrame with improvement metrics
    """
    # Make sure dataframes have the same structure
    if not all(col in adaptive_df.columns for col in baseline_df.columns):
        raise ValueError("Baseline and adaptive dataframes must have the same columns")
    
    # Merge dataframes on location
    metrics = baseline_df.merge(
        adaptive_df,
        on=['intersection_id', 'lat', 'lon'],
        suffixes=('_baseline', '_adaptive')
    )
    
    # Calculate wait time improvement (percentage reduction)
    metrics['wait_time_improvement'] = (
        (metrics['avg_wait_time_baseline'] - metrics['avg_wait_time_adaptive']) / 
        metrics['avg_wait_time_baseline'] * 100
    )
    
    # Calculate throughput improvement (percentage increase)
    metrics['throughput_improvement'] = (
        (metrics['vehicles_per_hour_adaptive'] - metrics['vehicles_per_hour_baseline']) / 
        metrics['vehicles_per_hour_baseline'] * 100
    )
    
    # Calculate overall effectiveness score (custom metric)
    # This example weights wait time reduction 60% and throughput increase 40%
    metrics['effectiveness_score'] = (
        0.6 * metrics['wait_time_improvement'] + 
        0.4 * metrics['throughput_improvement']
    )
    
    return metrics

def generate_static_heatmap(df, metric_column, title, output_path=None, cmap='coolwarm'):
    """
    Generate a static heatmap visualization of a specified metric.
    
    Args:
        df (pandas.DataFrame): DataFrame with lat, lon and metric columns
        metric_column (str): Column name for the metric to visualize
        title (str): Title for the heatmap
        output_path (str, optional): Path to save the heatmap
        cmap (str, optional): Colormap name
    """
    plt.figure(figsize=(12, 10))
    
    # Create pivot table for heatmap
    if 'intersection_id' in df.columns:
        pivot_data = df.pivot_table(
            index='lat', 
            columns='lon', 
            values=metric_column,
            aggfunc='mean'
        )
    else:
        # If no intersection_id, aggregate by grid cells
        df['lat_bin'] = pd.cut(df['lat'], bins=20)
        df['lon_bin'] = pd.cut(df['lon'], bins=20)
        pivot_data = df.pivot_table(
            index='lat_bin', 
            columns='lon_bin', 
            values=metric_column,
            aggfunc='mean'
        )
    
    # Set up colormap
    if metric_column == 'effectiveness_score' or metric_column.endswith('_improvement'):
        # For improvement metrics, use diverging colormap centered at 0
        vmin = min(df[metric_column].min(), -df[metric_column].max() * 0.2)
        vmax = max(df[metric_column].max(), -df[metric_column].min() * 0.2)
        norm = colors.TwoSlopeNorm(vmin=vmin, vcenter=0, vmax=vmax)
        cmap = 'RdYlGn'  # Red-Yellow-Green: red for negative, green for positive
    else:
        # For other metrics, use standard colormap
        norm = None
    
    # Generate heatmap
    sns.heatmap(
        pivot_data, 
        cmap=cmap,
        norm=norm,
        annot=False, 
        cbar=True,
        cbar_kws={'label': metric_column.replace('_', ' ').title()}
    )
    
    plt.title(title)
    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.tight_layout()
    
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path, dpi=300)
        print(f"Heatmap saved to {output_path}")
    else:
        plt.show()
    
    plt.close()

def generate_interactive_map(df, metric_column, title, output_path=None):
    """
    Generate an interactive folium map with heatmap layer.
    
    Args:
        df (pandas.DataFrame): DataFrame with lat, lon and metric columns
        metric_column (str): Column name for the metric to visualize
        title (str): Title for the map
        output_path (str, optional): Path to save the HTML map
    """
    # Determine map center
    center_lat = df['lat'].mean()
    center_lon = df['lon'].mean()
    
    # Create base map
    m = folium.Map(location=[center_lat, center_lon], zoom_start=13)
    
    # Add title
    title_html = f'''
        <h3 align="center" style="font-size:16px"><b>{title}</b></h3>
    '''
    m.get_root().html.add_child(folium.Element(title_html))
    
    # Prepare data for heatmap
    # For improvement metrics, separate positive and negative values for different coloring
    if metric_column == 'effectiveness_score' or metric_column.endswith('_improvement'):
        # Positive values (improvements)
        positive_df = df[df[metric_column] > 0].copy()
        if not positive_df.empty:
            positive_df['weight'] = positive_df[metric_column] / positive_df[metric_column].max()
            positive_data = positive_df[['lat', 'lon', 'weight']].values.tolist()
            
            # Add positive heatmap layer (green)
            HeatMap(
                positive_data,
                name='Improvements',
                min_opacity=0.4,
                radius=15,
                gradient={0.4: 'lime', 0.65: 'green', 1: 'darkgreen'},
                overlay=True,
                control=True
            ).add_to(m)
        
        # Negative values (regressions)
        negative_df = df[df[metric_column] < 0].copy()
        if not negative_df.empty:
            negative_df['weight'] = abs(negative_df[metric_column]) / abs(negative_df[metric_column].min())
            negative_data = negative_df[['lat', 'lon', 'weight']].values.tolist()
            
            # Add negative heatmap layer (red)
            HeatMap(
                negative_data,
                name='Regressions',
                min_opacity=0.4,
                radius=15,
                gradient={0.4: 'pink', 0.65: 'red', 1: 'darkred'},
                overlay=True,
                control=True
            ).add_to(m)
    else:
        # Standard heatmap for non-improvement metrics
        heatmap_data = df[['lat', 'lon', metric_column]].values.tolist()
        HeatMap(
            heatmap_data,
            name=metric_column.replace('_', ' ').title(),
            min_opacity=0.4,
            radius=15,
            overlay=True,
            control=True
        ).add_to(m)
    
    # Add intersection markers for detailed information
    if 'intersection_id' in df.columns:
        for _, row in df.iterrows():
            popup_text = f"""
                <b>Intersection:</b> {row['intersection_id']}<br>
                <b>{metric_column.replace('_', ' ').title()}:</b> {row[metric_column]:.2f}
            """
            folium.CircleMarker(
                location=[row['lat'], row['lon']],
                radius=4,
                popup=folium.Popup(popup_text, max_width=300),
                color='black',
                fill=True,
                fill_opacity=0.7
            ).add_to(m)
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        m.save(output_path)
        print(f"Interactive map saved to {output_path}")
    
    return m

def generate_rainfall_effectiveness_matrix(df, output_path=None):
    """
    Generate a matrix showing the effectiveness of adaptive strategy vs rainfall intensity.
    
    Args:
        df (pandas.DataFrame): DataFrame with rainfall and effectiveness metrics
        output_path (str, optional): Path to save the plot
    """
    # Define rain intensity bins
    rain_bins = [0, 0.1, 2.5, 7.6, 15, 50, float('inf')]
    rain_labels = ['None', 'Very Light', 'Light', 'Moderate', 'Heavy', 'Extreme']
    
    # Create binned rainfall column
    df['rainfall_category'] = pd.cut(df['rainfall'], bins=rain_bins, labels=rain_labels)
    
    # Define time of day bins (hours)
    time_bins = [0, 6, 10, 15, 19, 24]
    time_labels = ['Night', 'Morning Rush', 'Midday', 'Evening Rush', 'Evening']
    
    # Create binned time column (if time column exists)
    if 'time' in df.columns and 'hour' not in df.columns:
        if df['time'].dtype == 'object':
            # Convert string time to hour
            df['hour'] = pd.to_datetime(df['time']).dt.hour
        else:
            # Assume numeric time is in seconds or hours
            if df['time'].max() > 24:  # Seconds
                df['hour'] = (df['time'] / 3600) % 24
            else:  # Hours
                df['hour'] = df['time'] % 24
    
    if 'hour' in df.columns:
        df['time_category'] = pd.cut(df['hour'], bins=time_bins, labels=time_labels)
    
        # Create pivot table for effectiveness score by rainfall and time of day
        if 'effectiveness_score' in df.columns:
            pivot = df.pivot_table(
                index='rainfall_category',
                columns='time_category',
                values='effectiveness_score',
                aggfunc='mean'
            )
            
            plt.figure(figsize=(10, 8))
            
            # Create heatmap with custom diverging colormap centered at 0
            cmap = sns.diverging_palette(10, 120, as_cmap=True)
            sns.heatmap(
                pivot, 
                cmap=cmap,
                center=0,
                annot=True, 
                fmt='.1f',
                cbar=True,
                cbar_kws={'label': 'Effectiveness Score (%)'}
            )
            
            plt.title('Effectiveness of Rain-Adaptive Strategy by Rainfall and Time of Day')
            plt.tight_layout()
            
            if output_path:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                plt.savefig(output_path, dpi=300)
                print(f"Rainfall-time effectiveness matrix saved to {output_path}")
            else:
                plt.show()
            
            plt.close()
    else:
        # Create simple bar chart by rainfall category only
        if 'effectiveness_score' in df.columns:
            rain_effect = df.groupby('rainfall_category')['effectiveness_score'].mean()
            
            plt.figure(figsize=(10, 6))
            
            bars = plt.bar(rain_effect.index, rain_effect.values, 
                          color=sns.color_palette("RdYlGn", len(rain_effect)))
            
            # Add value labels
            for bar in bars:
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., 
                         height + (1 if height >= 0 else -3),
                         f'{height:.1f}%', 
                         ha='center', va='bottom' if height >= 0 else 'top')
            
            plt.axhline(y=0, color='black', linestyle='-', alpha=0.7)
            plt.ylabel('Effectiveness Score (%)')
            plt.title('Effectiveness of Rain-Adaptive Strategy by Rainfall Intensity')
            plt.grid(axis='y', linestyle='--', alpha=0.7)
            
            if output_path:
                filepath = output_path.replace('.png', '_by_rainfall.png')
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                plt.savefig(filepath, dpi=300)
                print(f"Rainfall effectiveness chart saved to {filepath}")
            else:
                plt.show()
            
            plt.close()

def main():
    """Main function to generate effectiveness heatmaps."""
    # Set paths
    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    output_dir = data_dir / "output"
    
    # Example usage
    baseline_file = output_dir / "baseline_simulation" / "spatial_metrics.csv"
    adaptive_file = output_dir / "adaptive_simulation" / "spatial_metrics.csv"
    weather_file = output_dir / "weather" / "rainfall_data.csv"
    
    # Create visualization output directory
    vis_dir = output_dir / "visualizations"
    os.makedirs(vis_dir, exist_ok=True)
    
    # Load data
    if baseline_file.exists() and adaptive_file.exists():
        baseline_data = load_spatial_data(str(baseline_file))
        adaptive_data = load_spatial_data(str(adaptive_file))
        
        # Load weather data if available
        weather_data = None
        if weather_file.exists():
            weather_data = pd.read_csv(weather_file)
        
        # Generate visualizations
        if baseline_data is not None and adaptive_data is not None:
            # Calculate improvement metrics
            try:
                improvement_data = calculate_improvement_metrics(baseline_data, adaptive_data)
                
                # Generate heatmaps
                generate_static_heatmap(
                    improvement_data, 
                    'wait_time_improvement',
                    'Wait Time Improvement (%)',
                    output_path=str(vis_dir / "wait_time_improvement_heatmap.png")
                )
                
                generate_static_heatmap(
                    improvement_data, 
                    'throughput_improvement',
                    'Throughput Improvement (%)',
                    output_path=str(vis_dir / "throughput_improvement_heatmap.png")
                )
                
                generate_static_heatmap(
                    improvement_data, 
                    'effectiveness_score',
                    'Overall Effectiveness Score',
                    output_path=str(vis_dir / "effectiveness_score_heatmap.png")
                )
                
                # Generate interactive map
                generate_interactive_map(
                    improvement_data,
                    'effectiveness_score',
                    'Interactive Effectiveness Heatmap',
                    output_path=str(vis_dir / "effectiveness_interactive_map.html")
                )
                
                # If we have weather data, generate rainfall-effectiveness matrix
                if weather_data is not None:
                    # Merge weather data with improvement data
                    # Assuming weather data has 'time' column that matches with improvement data
                    if 'time' in improvement_data.columns and 'time' in weather_data.columns:
                        merged_data = improvement_data.merge(
                            weather_data[['time', 'rainfall']],
                            on='time',
                            how='left'
                        )
                        
                        generate_rainfall_effectiveness_matrix(
                            merged_data,
                            output_path=str(vis_dir / "rainfall_effectiveness_matrix.png")
                        )
            except Exception as e:
                print(f"Error generating improvement metrics: {e}")
        else:
            print("Failed to load spatial data")
    else:
        print(f"Input files not found. Please run the simulation first.")

if __name__ == "__main__":
    main()