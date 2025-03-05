"""
Performance Metrics for Traffic Simulation Analysis

This module provides functions to calculate key performance indicators (KPIs)
and evaluate the performance of traffic simulation scenarios, specifically
comparing rain-adaptive vs. baseline traffic management approaches.
"""

import numpy as np
import pandas as pd
import os
from typing import Dict, List, Tuple, Union, Optional
from pathlib import Path
import xml.etree.ElementTree as ET
import matplotlib.pyplot as plt
from ..simulation.simulation_constants import VehicleClass


class PerformanceMetrics:
    """
    Class for calculating and analyzing traffic simulation performance metrics.
    """
    
    def __init__(self, output_path: Union[str, Path]):
        """
        Initialize with path to simulation output files.
        
        Args:
            output_path: Directory containing simulation output files
        """
        self.output_path = Path(output_path)
        self.metrics_cache = {}  # Cache for computed metrics
    
    def load_tripinfo_data(self, simulation_id: str) -> pd.DataFrame:
        """
        Load trip information from SUMO tripinfo.xml file.
        
        Args:
            simulation_id: Unique identifier for the simulation run
            
        Returns:
            DataFrame containing trip information
        """
        tripinfo_file = self.output_path / f"{simulation_id}_tripinfo.xml"
        
        if not tripinfo_file.exists():
            raise FileNotFoundError(f"Trip information file not found: {tripinfo_file}")
        
        # Parse XML
        tree = ET.parse(tripinfo_file)
        root = tree.getroot()
        
        # Extract trip data
        trips = []
        for trip in root.findall('tripinfo'):
            trip_data = trip.attrib
            
            # Convert string values to appropriate types
            trip_dict = {
                'id': trip_data.get('id', ''),
                'vehicle_type': trip_data.get('vType', ''),
                'depart': float(trip_data.get('depart', 0)),
                'arrival': float(trip_data.get('arrival', 0)),
                'duration': float(trip_data.get('duration', 0)),
                'waiting_time': float(trip_data.get('waitingTime', 0)),
                'time_loss': float(trip_data.get('timeLoss', 0)),
                'distance': float(trip_data.get('routeLength', 0)),
                'avg_speed': float(trip_data.get('routeLength', 0)) / max(float(trip_data.get('duration', 1)), 1)
            }
            
            trips.append(trip_dict)
        
        return pd.DataFrame(trips)
    
    def load_detector_data(self, simulation_id: str) -> pd.DataFrame:
        """
        Load traffic detector data from SUMO detector output files.
        
        Args:
            simulation_id: Unique identifier for the simulation run
            
        Returns:
            DataFrame containing detector measurements
        """
        detector_file = self.output_path / f"{simulation_id}_detectors.xml"
        
        if not detector_file.exists():
            raise FileNotFoundError(f"Detector file not found: {detector_file}")
        
        # Parse XML
        tree = ET.parse(detector_file)
        root = tree.getroot()
        
        # Extract detector data
        detector_records = []
        
        for interval in root.findall('interval'):
            interval_begin = float(interval.get('begin', 0))
            interval_end = float(interval.get('end', 0))
            
            for detector in interval:
                detector_dict = {
                    'interval_begin': interval_begin,
                    'interval_end': interval_end,
                    'detector_id': detector.get('id', ''),
                    'vehicles': int(detector.get('nVehContrib', 0)),
                    'speed': float(detector.get('speed', 0)),
                    'occupancy': float(detector.get('occupancy', 0)),
                    'density': float(detector.get('density', 0)) if 'density' in detector.attrib else None,
                    'flow': float(detector.get('flow', 0)) if 'flow' in detector.attrib else None
                }
                
                detector_records.append(detector_dict)
        
        return pd.DataFrame(detector_records)
    
    def calculate_travel_time_metrics(self, trip_data: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate travel time related metrics from trip data.
        
        Args:
            trip_data: DataFrame containing trip information
            
        Returns:
            Dictionary with travel time metrics
        """
        metrics = {
            'avg_travel_time': trip_data['duration'].mean(),
            'median_travel_time': trip_data['duration'].median(),
            'std_travel_time': trip_data['duration'].std(),
            'avg_waiting_time': trip_data['waiting_time'].mean(),
            'total_waiting_time': trip_data['waiting_time'].sum(),
            'avg_time_loss': trip_data['time_loss'].mean(),  # Time lost due to driving below ideal speed
            'total_time_loss': trip_data['time_loss'].sum(),
        }
        
        # Calculate percentiles
        for p in [10, 25, 75, 90, 95]:
            metrics[f'travel_time_p{p}'] = trip_data['duration'].quantile(p/100)
        
        # Calculate by vehicle type if available
        if 'vehicle_type' in trip_data.columns and not trip_data['vehicle_type'].isna().all():
            vehicle_metrics = {}
            for vtype, group in trip_data.groupby('vehicle_type'):
                prefix = f'vtype_{vtype}_'
                vehicle_metrics.update({
                    f'{prefix}avg_travel_time': group['duration'].mean(),
                    f'{prefix}avg_waiting_time': group['waiting_time'].mean(),
                    f'{prefix}count': len(group)
                })
            metrics.update(vehicle_metrics)
        
        return metrics
    
    def calculate_throughput_metrics(self, trip_data: pd.DataFrame, detector_data: Optional[pd.DataFrame] = None) -> Dict[str, float]:
        """
        Calculate throughput and flow related metrics.
        
        Args:
            trip_data: DataFrame containing trip information
            detector_data: Optional DataFrame containing detector data
            
        Returns:
            Dictionary with throughput metrics
        """
        # Get simulation duration from trip data
        if len(trip_data) == 0:
            return {'completed_trips': 0, 'throughput': 0}
        
        sim_start = trip_data['depart'].min()
        sim_end = trip_data['arrival'].max()
        sim_duration_hours = (sim_end - sim_start) / 3600  # Convert seconds to hours
        
        # Basic throughput metrics
        completed_trips = len(trip_data)
        throughput = completed_trips / sim_duration_hours  # vehicles per hour
        
        metrics = {
            'completed_trips': completed_trips,
            'throughput': throughput,
            'vehicle_kilometers': trip_data['distance'].sum() / 1000,  # Convert meters to kilometers
            'vehicle_hours': trip_data['duration'].sum() / 3600,  # Convert seconds to hours
        }
        
        # Add detector-based metrics if available
        if detector_data is not None and not detector_data.empty:
            # Average flow rate across all detectors
            if 'flow' in detector_data.columns:
                metrics['avg_flow_rate'] = detector_data['flow'].mean()
            elif 'vehicles' in detector_data.columns:
                # Calculate flow from vehicle count and interval duration
                detector_data['interval_duration'] = detector_data['interval_end'] - detector_data['interval_begin']
                detector_data['calculated_flow'] = detector_data['vehicles'] / (detector_data['interval_duration'] / 3600)
                metrics['avg_flow_rate'] = detector_data['calculated_flow'].mean()
            
            # Density metrics if available
            if 'density' in detector_data.columns:
                metrics['avg_density'] = detector_data['density'].mean()
                metrics['max_density'] = detector_data['density'].max()
        
        return metrics
    
    def calculate_efficiency_metrics(self, trip_data: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate efficiency metrics related to travel time and distance.
        
        Args:
            trip_data: DataFrame containing trip information
            
        Returns:
            Dictionary with efficiency metrics
        """
        # Calculate speed metrics
        metrics = {
            'avg_speed': trip_data['avg_speed'].mean(),  # km/h
            'median_speed': trip_data['avg_speed'].median(),
            'min_speed': trip_data['avg_speed'].min(),
            'max_speed': trip_data['avg_speed'].max(),
        }
        
        # Time loss ratio (ratio of time loss to total travel time)
        if 'time_loss' in trip_data.columns and 'duration' in trip_data.columns:
            metrics['avg_time_loss_ratio'] = (trip_data['time_loss'] / trip_data['duration']).mean()
        
        # Calculate total system travel time and distance
        total_travel_time = trip_data['duration'].sum()  # seconds
        total_travel_distance = trip_data['distance'].sum()  # meters
        
        # System efficiency (distance per time)
        if total_travel_time > 0:
            metrics['system_efficiency'] = total_travel_distance / total_travel_time  # meters per second
        
        return metrics
    
    def calculate_network_metrics(self, detector_data: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate network-wide metrics from detector data.
        
        Args:
            detector_data: DataFrame containing detector measurements
            
        Returns:
            Dictionary with network metrics
        """
        if detector_data.empty:
            return {}
        
        metrics = {}
        
        # Calculate average speed, occupancy, and density across the network
        if 'speed' in detector_data.columns:
            metrics['network_avg_speed'] = detector_data['speed'].mean()
        
        if 'occupancy' in detector_data.columns:
            metrics['network_avg_occupancy'] = detector_data['occupancy'].mean()
            metrics['network_max_occupancy'] = detector_data['occupancy'].max()
        
        if 'density' in detector_data.columns:
            metrics['network_avg_density'] = detector_data['density'].mean()
            metrics['network_max_density'] = detector_data['density'].max()
        
        # Calculate temporal metrics if we have interval data
        if 'interval_begin' in detector_data.columns and 'interval_end' in detector_data.columns:
            # Group by time intervals to see how network performance changes over time
            detector_data['interval_middle'] = (detector_data['interval_begin'] + detector_data['interval_end']) / 2
            time_metrics = detector_data.groupby(pd.cut(detector_data['interval_middle'], 
                                                      bins=10)).agg({
                'speed': 'mean',
                'occupancy': 'mean' if 'occupancy' in detector_data.columns else 'count',
                'vehicles': 'sum'
            })
            
            # Calculate time-based variation metrics
            if 'speed' in time_metrics.columns:
                metrics['speed_temporal_variation'] = time_metrics['speed'].std() / time_metrics['speed'].mean() \
                                                    if time_metrics['speed'].mean() > 0 else 0
            
            if 'vehicles' in time_metrics.columns:
                metrics['flow_temporal_variation'] = time_metrics['vehicles'].std() / time_metrics['vehicles'].mean() \
                                                   if time_metrics['vehicles'].mean() > 0 else 0
        
        return metrics
    
    def calculate_environmental_metrics(self, trip_data: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate estimated environmental metrics based on trip data.
        
        Args:
            trip_data: DataFrame containing trip information
            
        Returns:
            Dictionary with environmental metrics
        """
        # Simple estimation of emissions based on distance and duration
        # A more accurate model would use actual vehicle emissions data
        
        # Constants for emission estimation (simplified)
        AVG_CO2_EMISSION_RATE = 2.3  # kg per vehicle-km (average)
        AVG_FUEL_CONSUMPTION = 0.08  # liters per vehicle-km (average)
        
        total_distance_km = trip_data['distance'].sum() / 1000  # Convert meters to kilometers
        
        metrics = {
            'estimated_co2_emissions': total_distance_km * AVG_CO2_EMISSION_RATE,  # kg
            'estimated_fuel_consumption': total_distance_km * AVG_FUEL_CONSUMPTION,  # liters
        }
        
        # If we have vehicle types, we could make this more accurate
        if 'vehicle_type' in trip_data.columns:
            # This would be expanded with actual emission factors per vehicle type
            vehicle_type_counts = trip_data['vehicle_type'].value_counts()
            metrics['vehicle_type_distribution'] = vehicle_type_counts.to_dict()
        
        return metrics
    
    def calculate_all_metrics(self, simulation_id: str) -> Dict[str, float]:
        """
        Calculate all performance metrics for a simulation run.
        
        Args:
            simulation_id: Unique identifier for the simulation run
            
        Returns:
            Dictionary with all performance metrics
        """
        # Check if metrics are already cached
        if simulation_id in self.metrics_cache:
            return self.metrics_cache[simulation_id]
        
        # Load data
        try:
            trip_data = self.load_tripinfo_data(simulation_id)
            try:
                detector_data = self.load_detector_data(simulation_id)
            except FileNotFoundError:
                detector_data = pd.DataFrame()
        except FileNotFoundError as e:
            print(f"Warning: {e}")
            return {}
        
        # Calculate metrics
        all_metrics = {}
        
        # Travel time metrics
        travel_time_metrics = self.calculate_travel_time_metrics(trip_data)
        all_metrics.update(travel_time_metrics)
        
        # Throughput metrics
        throughput_metrics = self.calculate_throughput_metrics(trip_data, detector_data)
        all_metrics.update(throughput_metrics)
        
        # Efficiency metrics
        efficiency_metrics = self.calculate_efficiency_metrics(trip_data)
        all_metrics.update(efficiency_metrics)
        
        # Network metrics if detector data is available
        if not detector_data.empty:
            network_metrics = self.calculate_network_metrics(detector_data)
            all_metrics.update(network_metrics)
        
        # Environmental metrics
        environmental_metrics = self.calculate_environmental_metrics(trip_data)
        all_metrics.update(environmental_metrics)
        
        # Add metadata
        all_metrics['simulation_id'] = simulation_id
        all_metrics['vehicle_count'] = len(trip_data)
        
        # Cache results
        self.metrics_cache[simulation_id] = all_metrics
        
        return all_metrics
    
    def compare_scenarios(self, baseline_id: str, adaptive_id: str) -> Dict[str, float]:
        """
        Compare metrics between baseline and adaptive scenarios.
        
        Args:
            baseline_id: Simulation ID for baseline scenario
            adaptive_id: Simulation ID for adaptive scenario
            
        Returns:
            Dictionary with comparison metrics and improvement percentages
        """
        baseline_metrics = self.calculate_all_metrics(baseline_id)
        adaptive_metrics = self.calculate_all_metrics(adaptive_id)
        
        if not baseline_metrics or not adaptive_metrics:
            return {'error': 'Could not load metrics for one or both scenarios'}
        
        # Calculate differences and improvement percentages
        comparison = {}
        
        for key in baseline_metrics:
            if key in adaptive_metrics and isinstance(baseline_metrics[key], (int, float)) and key != 'simulation_id':
                baseline_value = baseline_metrics[key]
                adaptive_value = adaptive_metrics[key]
                
                # Calculate absolute difference
                difference = adaptive_value - baseline_value
                comparison[f'{key}_difference'] = difference
                
                # Calculate percentage change
                if baseline_value != 0:
                    percentage = (difference / baseline_value) * 100
                    comparison[f'{key}_pct_change'] = percentage
                    
                    # Determine if this is an improvement
                    # For most metrics, lower is better (travel time, waiting time, emissions)
                    # For some metrics, higher is better (speed, throughput)
                    is_improvement = False
                    
                    # Metrics where higher is better
                    higher_better = ['avg_speed', 'median_speed', 'system_efficiency', 
                                     'throughput', 'completed_trips']
                    
                    # Check if the change represents an improvement
                    if any(metric in key for metric in higher_better):
                        is_improvement = difference > 0
                    else:
                        is_improvement = difference < 0
                        
                    comparison[f'{key}_improved'] = is_improvement
        
        # Calculate overall improvement score (positive = better)
        key_metrics = [
            ('avg_travel_time', -1),  # negative weight (lower is better)
            ('avg_waiting_time', -2),  # higher weight as this is important
            ('throughput', 1),         # positive weight (higher is better)
            ('avg_speed', 0.5),        # positive weight (higher is better)
            ('total_time_loss', -1)    # negative weight (lower is better)
        ]
        
        score = 0
        valid_metrics = 0
        
        for metric, weight in key_metrics:
            if f'{metric}_pct_change' in comparison:
                score += comparison[f'{metric}_pct_change'] * weight
                valid_metrics += 1
        
        if valid_metrics > 0:
            comparison['overall_improvement_score'] = score / valid_metrics
        else:
            comparison['overall_improvement_score'] = 0
            
        # Add scenario identifiers
        comparison['baseline_id'] = baseline_id
        comparison['adaptive_id'] = adaptive_id
        
        return comparison
    
    def generate_summary_report(self, scenario_ids: List[str], output_file: Optional[str] = None) -> pd.DataFrame:
        """
        Generate a summary report comparing multiple scenarios.
        
        Args:
            scenario_ids: List of simulation IDs to include in report
            output_file: Optional path to save report as CSV
            
        Returns:
            DataFrame with metrics for all scenarios
        """
        all_metrics = []
        
        for scenario_id in scenario_ids:
            metrics = self.calculate_all_metrics(scenario_id)
            if metrics:
                all_metrics.append(metrics)
        
        if not all_metrics:
            print("No metrics found for specified scenarios")
            return pd.DataFrame()
        
        # Create DataFrame from metrics
        report_df = pd.DataFrame(all_metrics)
        
        # Save to CSV if output file is specified
        if output_file:
            report_df.to_csv(output_file, index=False)
            print(f"Report saved to {output_file}")
        
        return report_df
    
    def plot_metric_comparison(self, 
                              metric: str, 
                              scenario_ids: List[str],
                              labels: Optional[List[str]] = None,
                              title: Optional[str] = None,
                              save_path: Optional[str] = None):
        """
        Plot a comparison of a specific metric across multiple scenarios.
        
        Args:
            metric: Name of the metric to compare
            scenario_ids: List of simulation IDs to compare
            labels: Optional list of labels for scenarios (defaults to IDs)
            title: Optional title for the plot
            save_path: Optional path to save the plot
        """
        if labels is None:
            labels = scenario_ids
        
        if len(scenario_ids) != len(labels):
            raise ValueError("Number of scenario IDs must match number of labels")
        
        values = []
        for scenario_id in scenario_ids:
            metrics = self.calculate_all_metrics(scenario_id)
            if metric in metrics:
                values.append(metrics[metric])
            else:
                values.append(0)
                print(f"Warning: Metric '{metric}' not found for scenario {scenario_id}")
        
        plt.figure(figsize=(10, 6))
        bars = plt.bar(labels, values)
        
        # Add data labels on top of bars
        for bar, value in zip(bars, values):
            if isinstance(value, (int, float)):
                plt.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.01 * max(values),
                    f'{value:.2f}',
                    ha='center',
                    va='bottom'
                )
        
        plt.xlabel('Scenarios')
        plt.ylabel(metric.replace('_', ' ').title())
        
        if title:
            plt.title(title)
        else:
            plt.title(f'Comparison of {metric.replace("_", " ").title()} Across Scenarios')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path)
            print(f"Plot saved to {save_path}")
        
        plt.show()
    
    def plot_improvement_analysis(self, 
                                 baseline_id: str, 
                                 adaptive_ids: List[str],
                                 labels: Optional[List[str]] = None,
                                 metrics_to_plot: Optional[List[str]] = None,
                                 save_path: Optional[str] = None):
        """
        Plot the improvement of adaptive scenarios over a baseline.
        
        Args:
            baseline_id: Simulation ID for baseline scenario
            adaptive_ids: List of adaptive simulation IDs to compare
            labels: Optional list of labels for adaptive scenarios
            metrics_to_plot: Specific metrics to include in comparison
            save_path: Optional path to save the plot
        """
        if labels is None:
            labels = adaptive_ids
            
        if len(adaptive_ids) != len(labels):
            raise ValueError("Number of adaptive scenario IDs must match number of labels")
            
        # Default metrics to plot if not specified
        if metrics_to_plot is None:
            metrics_to_plot = [
                'avg_travel_time', 
                'avg_waiting_time', 
                'throughput',
                'avg_speed', 
                'total_time_loss'
            ]
            
        # Get comparison data for each adaptive scenario
        improvements = []
        for adaptive_id in adaptive_ids:
            comparison = self.compare_scenarios(baseline_id, adaptive_id)
            improvements.append({
                metric: comparison.get(f'{metric}_pct_change', 0)
                for metric in metrics_to_plot
            })
            
        # Create DataFrame for plotting
        df = pd.DataFrame(improvements, index=labels)
            
        # Create bar plot
        plt.figure(figsize=(12, 8))
        df.plot(kind='bar', ax=plt.gca())
        
        plt.axhline(y=0, color='k', linestyle='-', alpha=0.3)
        plt.xlabel('Adaptive Scenarios')
        plt.ylabel('Improvement Over Baseline (%)')
        plt.title(f'Performance Improvement Over Baseline ({baseline_id})')
        plt.legend(title='Metrics', bbox_to_anchor=(1.05, 1), loc='upper left')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path)
            print(f"Plot saved to {save_path}")
            
        plt.show()


if __name__ == "__main__":
    # Example usage
    metrics_analyzer = PerformanceMetrics("data/output")
    
    # Example: Compare baseline vs. rain-adaptive scenarios
    baseline_id = "baseline_dry"
    adaptive_id = "adaptive_rain_15mm"
    
    comparison = metrics_analyzer.compare_scenarios(baseline_id, adaptive_id)
    
    print("Performance Comparison:")
    print(f"Baseline: {baseline_id}")
    print(f"Adaptive: {adaptive_id}")
    print("-" * 50)
    
    for key, value in comparison.items():
        if 'pct_change' in key and 'simulation' not in key:
            metric_name = key.replace('_pct_change', '')
            improved = comparison.get(f'{metric_name}_improved', False)
            direction = "better" if improved else "worse"
            
            print(f"{metric_name}: {value:.2f}% ({direction})")
            
    print("-" * 50)
    print(f"Overall improvement score: {comparison.get('overall_improvement_score', 0):.2f}")