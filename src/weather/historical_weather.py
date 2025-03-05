# # historical_weather.py
# import pandas as pd
# import numpy as np
# import matplotlib.pyplot as plt

# def load_historical_weather_data(file_path):
#     """Load and process historical weather data"""
#     # Load data
#     data = pd.read_csv(file_path)
    
#     # Clean and process data
#     data['date'] = pd.to_datetime(data['date'])
#     data = data.fillna(0)  # Replace NaN with 0 for rainfall
    
#     return data

# def analyze_rain_patterns(data):
#     """Analyze rain patterns from historical data"""
#     # Group by month and calculate average rainfall
#     monthly_avg = data.groupby(data['date'].dt.month)['precipitation_mm'].mean()
    
#     # Calculate frequency of different rain intensities
#     rain_categories = {
#         'no_rain': len(data[data['precipitation_mm'] == 0]),
#         'light_rain': len(data[(data['precipitation_mm'] > 0) & (data['precipitation_mm'] < 2.5)]),
#         'moderate_rain': len(data[(data['precipitation_mm'] >= 2.5) & (data['precipitation_mm'] < 7.6)]),
#         'heavy_rain': len(data[data['precipitation_mm'] >= 7.6])
#     }
    
#     return monthly_avg, rain_categories

# def plot_rain_distributions(data):
#     """Create visualizations of rain distributions"""
#     monthly_avg, categories = analyze_rain_patterns(data)
    
#     # Plot monthly averages
#     plt.figure(figsize=(12, 6))
#     monthly_avg.plot(kind='bar')
#     plt.title('Average Monthly Rainfall')
#     plt.xlabel('Month')
#     plt.ylabel('Precipitation (mm)')
#     plt.savefig('monthly_rainfall.png')
    
#     # Plot rain categories
#     plt.figure(figsize=(10, 6))
#     labels = list(categories.keys())
#     sizes = list(categories.values())
#     plt.pie(sizes, labels=labels, autopct='%1.1f%%')
#     plt.title('Distribution of Rainfall Intensity')
#     plt.savefig('rain_distribution.png')

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Historical Weather Data Processing Module

This module provides functionality for loading, processing, and analyzing
historical weather data for use in the traffic simulation.
"""

import os
import pandas as pd
import numpy as np
import datetime
from typing import Dict, List, Tuple, Optional, Union
import matplotlib.pyplot as plt
from pathlib import Path


class HistoricalWeatherProcessor:
    """
    Class for processing historical weather data for traffic simulations.
    """
    
    def __init__(self, data_dir: str = "data/input/weather"):
        """
        Initialize the historical weather processor.
        
        Args:
            data_dir (str): Directory containing historical weather data files
        """
        self.data_dir = data_dir
        self.weather_data = None
        self.rain_thresholds = {
            'light': 0.5,      # mm/h
            'moderate': 4.0,   # mm/h
            'heavy': 8.0,      # mm/h
            'extreme': 50.0    # mm/h
        }
        
    def load_data(self, filename: str) -> pd.DataFrame:
        """
        Load historical weather data from a file.
        
        Args:
            filename (str): Name of the file to load
            
        Returns:
            pd.DataFrame: DataFrame containing the weather data
            
        Raises:
            FileNotFoundError: If the specified file does not exist
        """
        file_path = os.path.join(self.data_dir, filename)
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Weather data file not found: {file_path}")
            
        # Determine file format from extension
        file_ext = os.path.splitext(filename)[1].lower()
        
        if file_ext == '.csv':
            df = pd.read_csv(file_path, parse_dates=['timestamp'])
        elif file_ext in ['.xls', '.xlsx']:
            df = pd.read_excel(file_path, parse_dates=['timestamp'])
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")
            
        # Basic validation
        required_columns = ['timestamp', 'precipitation_mm']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise ValueError(f"Missing required columns in weather data: {missing_columns}")
            
        self.weather_data = df
        print(f"Loaded weather data with {len(df)} records from {filename}")
        
        return df
        
    def interpolate_missing_values(self) -> pd.DataFrame:
        """
        Interpolate missing values in the weather data.
        
        Returns:
            pd.DataFrame: Weather data with interpolated values
        """
        if self.weather_data is None:
            raise ValueError("No weather data loaded. Call load_data() first.")
            
        # Check for missing values
        missing_values = self.weather_data.isnull().sum()
        
        if missing_values.any():
            print(f"Found missing values: {missing_values}")
            # Interpolate missing values (linear interpolation)
            self.weather_data = self.weather_data.interpolate(method='linear')
            # Fill any remaining NaNs (at the beginning or end)
            self.weather_data = self.weather_data.fillna(method='ffill').fillna(method='bfill')
            print("Interpolated missing values.")
            
        return self.weather_data
        
    def resample_data(self, freq: str = '1min') -> pd.DataFrame:
        """
        Resample the weather data to a consistent frequency.
        
        Args:
            freq (str): Pandas frequency string (e.g., '1min', '5min')
            
        Returns:
            pd.DataFrame: Resampled weather data
        """
        if self.weather_data is None:
            raise ValueError("No weather data loaded. Call load_data() first.")
            
        # Ensure timestamp is the index
        if 'timestamp' in self.weather_data.columns:
            self.weather_data = self.weather_data.set_index('timestamp')
            
        # Resample to the specified frequency
        resampled = self.weather_data.resample(freq).mean()
        
        # Interpolate any missing values created during resampling
        resampled = resampled.interpolate(method='linear')
        
        # Reset index to have timestamp as a column again
        resampled = resampled.reset_index()
        
        self.weather_data = resampled
        print(f"Resampled weather data to {freq} frequency, resulting in {len(resampled)} records")
        
        return resampled
        
    def categorize_rainfall(self, precipitation_col: str = 'precipitation_mm') -> pd.DataFrame:
        """
        Categorize rainfall intensity based on precipitation values.
        
        Args:
            precipitation_col (str): Column name for precipitation data
            
        Returns:
            pd.DataFrame: Weather data with added rainfall category column
        """
        if self.weather_data is None:
            raise ValueError("No weather data loaded. Call load_data() first.")
            
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
                
        self.weather_data['rain_category'] = self.weather_data[precipitation_col].apply(categorize)
        
        # Also add a numerical intensity column (0.0-1.0 scale) for models
        max_rain = max(self.rain_thresholds['extreme'] * 1.5, self.weather_data[precipitation_col].max())
        self.weather_data['rain_intensity'] = self.weather_data[precipitation_col].apply(
            lambda x: min(x / max_rain, 1.0)
        )
        
        # Count occurrences of each category
        category_counts = self.weather_data['rain_category'].value_counts()
        print("Rainfall category distribution:")
        for category, count in category_counts.items():
            print(f"  {category}: {count} records ({count/len(self.weather_data)*100:.1f}%)")
            
        return self.weather_data
        
    def get_rain_events(self, min_duration_minutes: int = 30) -> List[Dict]:
        """
        Extract significant rain events from the data.
        
        Args:
            min_duration_minutes (int): Minimum duration for a rain event
            
        Returns:
            List[Dict]: List of rain events with start time, end time, and intensity
        """
        if self.weather_data is None:
            raise ValueError("No weather data loaded. Call load_data() first.")
            
        if 'rain_category' not in self.weather_data.columns:
            self.categorize_rainfall()
            
        # Ensure timestamp is a column
        df = self.weather_data.copy()
        if 'timestamp' not in df.columns and df.index.name == 'timestamp':
            df = df.reset_index()
            
        # Find continuous rain periods
        df['is_raining'] = df['rain_category'] != 'normal'
        
        # Add a group column to identify continuous rain events
        df['rain_change'] = df['is_raining'].astype(int).diff().fillna(0)
        df['rain_event_id'] = df['rain_change'].cumsum()
        
        rain_events = []
        
        # Process each rain event
        for event_id, group in df[df['is_raining']].groupby('rain_event_id'):
            if len(group) == 0:
                continue
                
            start_time = group['timestamp'].min()
            end_time = group['timestamp'].max()
            
            # Calculate duration in minutes
            duration = (end_time - start_time).total_seconds() / 60
            
            # Only include events that meet the minimum duration
            if duration >= min_duration_minutes:
                # Get the average rain intensity and dominant category
                avg_intensity = group['rain_intensity'].mean()
                dominant_category = group['rain_category'].mode()[0]
                
                rain_events.append({
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration_minutes': duration,
                    'avg_intensity': avg_intensity,
                    'peak_intensity': group['rain_intensity'].max(),
                    'category': dominant_category,
                    'total_precipitation': group['precipitation_mm'].sum()
                })
                
        print(f"Identified {len(rain_events)} significant rain events")
        return rain_events
        
    def plot_rainfall_data(self, output_file: Optional[str] = None):
        """
        Plot rainfall data and save to file if specified.
        
        Args:
            output_file (str, optional): File path to save the plot
        """
        if self.weather_data is None:
            raise ValueError("No weather data loaded. Call load_data() first.")
            
        # Ensure timestamp is in the DataFrame
        df = self.weather_data.copy()
        if 'timestamp' not in df.columns and df.index.name == 'timestamp':
            df = df.reset_index()
            
        # Create figure with two subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
        
        # Plot precipitation
        ax1.plot(df['timestamp'], df['precipitation_mm'], 'b-')
        ax1.set_ylabel('Precipitation (mm/h)')
        ax1.set_title('Historical Rainfall Data')
        ax1.grid(True)
        
        # Add thresholds for rain categories
        for category, threshold in self.rain_thresholds.items():
            ax1.axhline(y=threshold, color='r', linestyle='--', alpha=0.5)
            ax1.text(df['timestamp'].max(), threshold, f' {category}', 
                    verticalalignment='bottom', horizontalalignment='right')
                    
        # Plot rain categories/intensity if available
        if 'rain_category' in df.columns:
            # Create a categorical type for proper ordering
            cat_type = pd.CategoricalDtype(
                categories=['normal', 'light', 'moderate', 'heavy', 'extreme'],
                ordered=True
            )
            df['rain_category'] = df['rain_category'].astype(cat_type)
            
            # Plot rain categories
            categories = df['rain_category'].unique()
            colors = {'normal': 'green', 'light': 'blue', 'moderate': 'orange', 
                     'heavy': 'red', 'extreme': 'purple'}
                     
            for i, category in enumerate(categories):
                category_data = df[df['rain_category'] == category]
                ax2.scatter(category_data['timestamp'], [i] * len(category_data), 
                           label=category, alpha=0.5, color=colors.get(category, 'gray'))
                           
            ax2.set_yticks(range(len(categories)))
            ax2.set_yticklabels(categories)
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
            print(f"Saved rainfall plot to {output_file}")
        else:
            plt.show()
            
    def get_simulation_weather_profile(self, start_date: datetime.datetime, 
                                      duration_hours: float) -> pd.DataFrame:
        """
        Extract a weather profile for a specific time period for simulation.
        
        Args:
            start_date (datetime.datetime): Start date and time
            duration_hours (float): Duration of the simulation in hours
            
        Returns:
            pd.DataFrame: Weather data for the simulation period
        """
        if self.weather_data is None:
            raise ValueError("No weather data loaded. Call load_data() first.")
            
        # Ensure timestamp is in the DataFrame
        df = self.weather_data.copy()
        if 'timestamp' not in df.columns and df.index.name == 'timestamp':
            df = df.reset_index()
            
        # Calculate end date
        end_date = start_date + datetime.timedelta(hours=duration_hours)
        
        # Filter data for the simulation period
        sim_weather = df[(df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)]
        
        if len(sim_weather) == 0:
            raise ValueError(f"No weather data available for the period {start_date} to {end_date}")
            
        print(f"Extracted weather profile with {len(sim_weather)} records for simulation period")
        return sim_weather
        
    def export_for_simulation(self, output_file: str, 
                             start_date: Optional[datetime.datetime] = None,
                             duration_hours: Optional[float] = None):
        """
        Export weather data for use in simulation.
        
        Args:
            output_file (str): Output file path
            start_date (datetime.datetime, optional): Start date for filtering
            duration_hours (float, optional): Duration in hours for filtering
        """
        if self.weather_data is None:
            raise ValueError("No weather data loaded. Call load_data() first.")
            
        # Get data for simulation period if specified
        if start_date is not None and duration_hours is not None:
            df = self.get_simulation_weather_profile(start_date, duration_hours)
        else:
            df = self.weather_data.copy()
            
        # Ensure required columns exist
        if 'rain_category' not in df.columns:
            self.categorize_rainfall()
            df = self.weather_data.copy()
            
        # Prepare export data
        export_df = df[['timestamp', 'precipitation_mm', 'rain_category', 'rain_intensity']]
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Export to CSV
        export_df.to_csv(output_file, index=False)
        print(f"Exported weather data for simulation to {output_file}")