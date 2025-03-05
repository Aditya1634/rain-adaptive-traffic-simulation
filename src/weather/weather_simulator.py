#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Weather Simulator Module

This module provides functionality for generating synthetic weather data
for use in traffic simulations when real weather data is not available.
"""

import os
import pandas as pd
import numpy as np
import datetime
from typing import Dict, List, Tuple, Optional, Union
import matplotlib.pyplot as plt
from pathlib import Path
import random


class WeatherSimulator:
    """
    Class for generating synthetic weather data for traffic simulations.
    """
    
    def __init__(self, seed: Optional[int] = None):
        """
        Initialize the weather simulator.
        
        Args:
            seed (int, optional): Random seed for reproducibility
        """
        if seed is not None:
            np.random.seed(seed)
            random.seed(seed)
            
        self.rain_thresholds = {
            'light': 0.5,      # mm/h
            'moderate': 4.0,   # mm/h
            'heavy': 8.0,      # mm/h
            'extreme': 50.0    # mm/h
        }
        
    def generate_constant_weather(self, duration_minutes: int, 
                                 timestep_seconds: int = 60,
                                 precipitation_mm: float = 0.0) -> pd.DataFrame:
        """
        Generate constant weather conditions.
        
        Args:
            duration_minutes (int): Duration of the simulation
            timestep_seconds (int): Time step between records
            precipitation_mm (float): Constant precipitation value
            
        Returns:
            pd.DataFrame: Generated weather data
        """
        # Calculate number of time steps
        num_steps = int((duration_minutes * 60) / timestep_seconds)
        
        # Generate timestamps
        start_time = datetime.datetime.now().replace(microsecond=0)
        timestamps = [start_time + datetime.timedelta(seconds=i*timestep_seconds) 
                     for i in range(num_steps)]
                     
        # Create DataFrame with constant precipitation
        df = pd.DataFrame({
            'timestamp': timestamps,
            'precipitation_mm': [precipitation_mm] * num_steps
        })
        
        # Add rain categories and intensity
        self._add_rain_categories(df)
        
        print(f"Generated constant weather data with {num_steps} time steps")
        return df
        
    def generate_rain_event(self, duration_minutes: int, 
                           timestep_seconds: int = 60, 
                           max_intensity: float = 10.0,
                           event_pattern: str = 'ramp') -> pd.DataFrame:
        """
        Generate a synthetic rain event.
        
        Args:
            duration_minutes (int): Duration of the simulation
            timestep_seconds (int): Time step between records
            max_intensity (float): Maximum precipitation intensity
            event_pattern (str): Pattern of the rain event ('ramp', 'peak', 'random')
            
        Returns:
            pd.DataFrame: Generated weather data
        """
        # Calculate number of time steps
        num_steps = int((duration_minutes * 60) / timestep_seconds)
        
        # Generate timestamps
        start_time = datetime.datetime.now().replace(microsecond=0)
        timestamps = [start_time + datetime.timedelta(seconds=i*timestep_seconds) 
                     for i in range(num_steps)]
        
        # Generate precipitation values based on pattern
        precipitation = np.zeros(num_steps)
        
        if event_pattern == 'ramp':
            # Linearly increasing then decreasing
            ramp_up = np.linspace(0, max_intensity, num_steps // 2)
            ramp_down = np.linspace(max_intensity, 0, num_steps - len(ramp_up))
            precipitation = np.concatenate([ramp_up, ramp_down])
            
        elif event_pattern == 'peak':
            # Normal distribution around the middle
            x = np.linspace(-3, 3, num_steps)
            precipitation = max_intensity * np.exp(-x**2)
            
        elif event_pattern == 'random':
            # Random fluctuations with an overall bell curve
            x = np.linspace(-3, 3, num_steps)
            base_curve = max_intensity * np.exp(-x**2)
            random_noise = np.random.normal(0, max_intensity * 0.2, num_steps)
            precipitation = np.maximum(0, base_curve + random_noise)
            
        else:
            raise ValueError(f"Unknown event pattern: {event_pattern}")
            
        # Create DataFrame
        df = pd.DataFrame({
            'timestamp': timestamps,
            'precipitation_mm': precipitation
        })
        
        # Add rain categories and intensity
        self._add_rain_categories(df)
        
        print(f"Generated {event_pattern} rain event with {num_steps} time steps")
        return df
    
    def generate_realistic_day(self, start_time: Optional[datetime.datetime] = None,
                              rain_probability: float = 0.3,
                              max_events: int = 2) -> pd.DataFrame:
        """
        Generate a realistic day of weather with potential rain events.
        
        Args:
            start_time (datetime.datetime, optional): Start time for the simulation
            rain_probability (float): Probability of rain on this day
            max_events (int): Maximum number of rain events to generate
            
        Returns:
            pd.DataFrame: Generated weather data for a full day
        """
        # Set start time to beginning of day if not provided
        if start_time is None:
            start_time = datetime.datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0)
                
        # Generate timestamps for the full day (minute resolution)
        minutes_in_day = 24 * 60
        timestamps = [start_time + datetime.timedelta(minutes=i) 
                     for i in range(minutes_in_day)]
        
        # Initialize with no precipitation
        precipitation = np.zeros(minutes_in_day)
        
        # Determine if it will rain today
        if random.random() < rain_probability:
            # Decide number of rain events
            num_events = random.randint(1, max_events)
            
            for _ in range(num_events):
                # Determine event parameters
                event_duration = random.randint(30, 180)  # 30 minutes to 3 hours
                event_start = random.randint(0, minutes_in_day - event_duration)
                event_max_intensity = random.uniform(0.5, 20.0)  # 0.5 to 20 mm/h
                
                # Create event pattern - randomly choose
                event_pattern = random.choice(['ramp', 'peak', 'random'])
                
                # Generate event precipitation
                event_steps = event_duration
                
                if event_pattern == 'ramp':
                    ramp_up = np.linspace(0, event_max_intensity, event_steps // 2)
                    ramp_down = np.linspace(event_max_intensity, 0, event_steps - len(ramp_up))
                    event_precip = np.concatenate([ramp_up, ramp_down])
                    
                elif event_pattern == 'peak':
                    x = np.linspace(-3, 3, event_steps)
                    event_precip = event_max_intensity * np.exp(-x**2)
                    
                else:  # random
                    x = np.linspace(-3, 3, event_steps)
                    base_curve = event_max_intensity * np.exp(-x**2)
                    random_noise = np.random.normal(0, event_max_intensity * 0.2, event_steps)
                    event_precip = np.maximum(0, base_curve + random_noise)
                
                # Add event precipitation to the day
                precipitation[event_start:event_start + event_duration] = event_precip
        
        # Create DataFrame
        df = pd.DataFrame({
            'timestamp': timestamps,
            'precipitation_mm': precipitation
        })
        
        # Add rain categories and intensity
        self._add_rain_categories(df)
        
        print(f"Generated realistic day weather with {sum(precipitation > 0)} minutes of rain")
        return df
    
    def _add_rain_categories(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add rain category and intensity columns to the DataFrame.
        
        Args:
            df (pd.DataFrame): Weather DataFrame with precipitation_mm column
            
        Returns:
            pd.DataFrame: Updated DataFrame
        """
        # Create a new column for rainfall category
        def categorize(rain_value):
            if rain_value < self.rain_thresholds['light']:
                return 'normal'
            elif rain_value < self.rain_thresholds['moderate']:
                return 'light'
            elif rain_value < self.rain_thresholds['heavy']:
                return 'moderate'
            elif rain_value < self.rain_thresholds['extreme']:
                return 'heavy'
            else:
                return 'extreme'
                
        df['rain_category'] = df['precipitation_mm'].apply(categorize)
        
        # Add a numerical intensity column (0.0-1.0 scale) for models
        max_rain = max(self.rain_thresholds['extreme'] * 1.5, df['precipitation_mm'].max())
        df['rain_intensity'] = df['precipitation_mm'].apply(
            lambda x: min(x / max_rain, 1.0) if max_rain > 0 else 0.0
        )
        
        return df
        
    def plot_weather(self, weather_data: pd.DataFrame, output_file: Optional[str] = None):
        """
        Plot the weather data.
        
        Args:
            weather_data (pd.DataFrame): Weather data to plot
            output_file (str, optional): File path to save the plot
        """
        # Create figure with two subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
        
        # Plot precipitation
        ax1.plot(weather_data['timestamp'], weather_data['precipitation_mm'], 'b-')
        ax1.set_ylabel('Precipitation (mm/h)')
        ax1.set_title('Simulated Weather Data')
        ax1.grid(True)
        
        # Add thresholds for rain categories
        for category, threshold in self.rain_thresholds.items():
            ax1.axhline(y=threshold, color='r', linestyle='--', alpha=0.5)
            ax1.text(weather_data['timestamp'].iloc[-1], threshold, f' {category}', 
                    verticalalignment='bottom', horizontalalignment='right')
                    
        # Plot rain categories
        if 'rain_category' in weather_data.columns:
            # Create a categorical type for proper ordering
            cat_type = pd.CategoricalDtype(
                categories=['normal', 'light', 'moderate', 'heavy', 'extreme'],
                ordered=True
            )
            weather_data['rain_category'] = weather_data['rain_category'].astype(cat_type)
            
            # Plot rain categories
            categories = weather_data['rain_category'].unique()
            colors = {'normal': 'green', 'light': 'blue', 'moderate': 'orange', 
                     'heavy': 'red', 'extreme': 'purple'}
                     
            for i, category in enumerate(sorted(categories)):
                category_data = weather_data[weather_data['rain_category'] == category]
                ax2.scatter(category_data['timestamp'], [i] * len(category_data), 
                           label=category, alpha=0.5, color=colors.get(category, 'gray'))
                           
            ax2.set_yticks(range(len(categories)))
            ax2.set_yticklabels(sorted(categories))
            ax2.set_ylabel('Rain Category')
            ax2.grid(True)
            ax2.legend()
            
        # Format the x-axis
        fig.autofmt_xdate()
        
        plt.tight_layout()
        
        # Save or display the plot
        if output_file:
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            plt.savefig(output_file)
            print(f"Saved weather plot to {output_file}")
        else:
            plt.show()
            
    def export_weather_data(self, weather_data: pd.DataFrame, output_file: str):
        """
        Export weather data to a CSV file.
        
        Args:
            weather_data (pd.DataFrame): Weather data to export
            output_file (str): Output file path
        """
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Export to CSV
        weather_data.to_csv(output_file, index=False)
        print(f"Exported simulated weather data to {output_file}")
        
    def generate_scenarios(self, output_dir: str, num_scenarios: int = 5):
        """
        Generate multiple weather scenarios for simulation testing.
        
        Args:
            output_dir (str): Directory to save scenario files
            num_scenarios (int): Number of scenarios to generate
        """
        # Ensure directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate different types of scenarios
        scenarios = []
        
        # Scenario 1: No rain (baseline)
        no_rain = self.generate_constant_weather(
            duration_minutes=240,  # 4-hour simulation
            precipitation_mm=0.0
        )
        no_rain.to_csv(os.path.join(output_dir, 'scenario_no_rain.csv'), index=False)
        scenarios.append(('No Rain', no_rain))
        
        # Scenario 2: Light constant rain
        light_rain = self.generate_constant_weather(
            duration_minutes=240,
            precipitation_mm=1.0  # Light constant rain
        )
        light_rain.to_csv(os.path.join(output_dir, 'scenario_light_constant.csv'), index=False)
        scenarios.append(('Light Constant', light_rain))
        
        # Scenario 3: Moderate constant rain
        moderate_rain = self.generate_constant_weather(
            duration_minutes=240,
            precipitation_mm=5.0  # Moderate constant rain
        )
        moderate_rain.to_csv(os.path.join(output_dir, 'scenario_moderate_constant.csv'), index=False)
        scenarios.append(('Moderate Constant', moderate_rain))
        
        # Generate remaining scenarios as rain events with different patterns
        patterns = ['ramp', 'peak', 'random']
        intensities = [3.0, 7.0, 15.0, 25.0]  # Light to extreme
        
        scenario_count = 4  # Starting after the constant scenarios
        while scenario_count <= num_scenarios:
            pattern = random.choice(patterns)
            intensity = random.choice(intensities)
            
            scenario = self.generate_rain_event(
                duration_minutes=240,
                max_intensity=intensity,
                event_pattern=pattern
            )
            
            name = f"scenario_{pattern}_{int(intensity)}.csv"
            scenario.to_csv(os.path.join(output_dir, name), index=False)
            scenarios.append((f"{pattern.capitalize()} {intensity}mm/h", scenario))
            
            scenario_count += 1
            
        # Create a comparison plot
        self._plot_scenario_comparison(scenarios, os.path.join(output_dir, 'scenarios_comparison.png'))
        
        print(f"Generated {num_scenarios} weather scenarios in {output_dir}")
        
    def _plot_scenario_comparison(self, scenarios: List[Tuple[str, pd.DataFrame]], output_file: str):
        """
        Create a comparison plot of multiple scenarios.
        
        Args:
            scenarios (List[Tuple[str, pd.DataFrame]]): List of scenario name and data
            output_file (str): Output file path for the plot
        """
        plt.figure(figsize=(12, 8))
        
        for name, data in scenarios:
            plt.plot(data['timestamp'], data['precipitation_mm'], label=name)
            
        plt.xlabel('Time')
        plt.ylabel('Precipitation (mm/h)')
        plt.title('Weather Scenarios Comparison')
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        
        # Format the x-axis
        plt.gcf().autofmt_xdate()
        
        # Save the plot
        plt.savefig(output_file)
        print(f"Saved scenario comparison plot to {output_file}")