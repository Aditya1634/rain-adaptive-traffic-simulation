"""
Comparative Analysis Module

This module provides functionality to compare different traffic management
approaches (baseline vs. rain-adaptive) under various weather conditions.
It analyzes simulation results and quantifies the benefits of adaptive strategies.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union
import json
import os
import re

from .performance_metrics import PerformanceMetrics


class ComparativeAnalysis:
    """
    Class for comparing baseline and adaptive traffic management approaches
    across different weather scenarios.
    """
    
    def __init__(self, output_dir: Union[str, Path]):
        """
        Initialize with the path to simulation output directory.
        
        Args:
            output_dir: Directory containing simulation output files
        """
        self.output_dir = Path(output_dir)
        self.metrics = PerformanceMetrics(output_dir)
        self.results_cache = {}  # Cache for analyzed results
    
    def identify_scenario_pairs(self) -> List[Dict[str, str]]:
        """
        Automatically identify baseline-adaptive scenario pairs from output files.
        
        Returns:
            List of dictionaries with baseline and adaptive scenario IDs
        """
        # Get all tripinfo files
        tripinfo_files = list(self.output_dir.glob("*_tripinfo.xml"))
        scenario_ids = [f.stem.replace("_tripinfo", "") for f in tripinfo_files]
        
        # Extract rainfall amounts and scenario types using regex
        scenario_info = []
        
        for scenario_id in scenario_ids:
            # Look for patterns like "baseline_rain_10mm" or "adaptive_rain_10mm"
            rain_match = re.search(r'(baseline|adaptive)_rain_(\d+)mm', scenario_id)
            
            if rain_match:
                scenario_type = rain_match.group(1)  # baseline or adaptive
                rain_amount = int(rain_match.group(2))  # rainfall in mm
                
                scenario_info.append({
                    'id': scenario_id,
                    'type': scenario_type,
                    'rain_mm': rain_amount
                })
            elif "baseline" in scenario_id.lower():
                scenario_info.append({
                    'id': scenario_id,
                    'type': 'baseline',
                    'rain_mm': 0  # Assume dry conditions if not specified
                })
            elif "adaptive" in scenario_id.lower():
                scenario_info.append({
                    'id': scenario_id,
                    'type': 'adaptive',
                    'rain_mm': 0  # Assume dry conditions if not specified
                })
        
        # Match baseline-adaptive pairs with same rainfall amount
        pairs = []
        
        for adaptive in [s for s in scenario_info if s['type'] == 'adaptive']:
            matching_baselines = [
                b for b in scenario_info 
                if b['type'] == 'baseline' and b['rain_mm'] == adaptive['rain_mm']
            ]
            
            if matching_baselines:
                # If multiple matches, prefer exact name matches
                best_match = None
                
                for baseline in matching_baselines:
                    # Replace "adaptive" with "baseline" in the adaptive ID
                    expected_baseline_id = adaptive['id'].replace('adaptive', 'baseline')
                    
                    if baseline['id'] == expected_baseline_id:
                        best_match = baseline
                        break
                
                # If no exact match, take the first matching baseline
                if best_match is None and matching_baselines:
                    best_match = matching_baselines[0]
                
                if best_match:
                    pairs.append({
                        'baseline_id': best_match['id'],
                        'adaptive_id': adaptive['id'],
                        'rain_mm': adaptive['rain_mm']
                    })
        
        return pairs
    
    def load_simulation_metadata(self, simulation_id: str) -> Dict:
        """
        Load metadata for a simulation run.
        
        Args:
            simulation_id: Simulation identifier
            
        Returns:
            Dictionary with simulation metadata
        """
        metadata_file = self.output_dir / f"{simulation_id}_metadata.json"
        
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                return json.load(f)
        else:
            # Try to infer metadata from filename
            metadata = {'id': simulation_id}
            
            if 'baseline' in simulation_id:
                metadata['type'] = 'baseline'
            elif 'adaptive' in simulation_id:
                metadata['type'] = 'adaptive'
                
            rain_match = re.search(r'rain_(\d+)mm', simulation_id)
            if rain_match:
                metadata['rain_mm'] = int(rain_match.group(1))
            else:
                metadata['rain_mm'] = 0
                
            return metadata
    
    def compare_single_pair(self, baseline_id: str, adaptive_id: str) -> Dict:
        """
        Compare a single baseline-adaptive scenario pair.
        
        Args:
            baseline_id: Baseline scenario identifier
            adaptive_id: Adaptive scenario identifier
            
        Returns:
            Dictionary with comparative analysis results
        """
        # Check cache first
        cache_key = f"{baseline_id}_{adaptive_id}"
        if cache_key in self.results_cache:
            return self.results_cache[cache_key]
        
        # Load metadata
        baseline_meta = self.load_simulation_metadata(baseline_id)
        adaptive_meta = self.load_simulation_metadata(adaptive_id)
        
        # Compute performance metrics comparison
        metrics_comparison = self.metrics.compare_scenarios(baseline_id, adaptive_id)
        
        # Create result dictionary
        result = {
            'baseline': baseline_meta,
            'adaptive': adaptive_meta,
            'metrics': metrics_comparison,
            'key_improvements': {}
        }
        
        # Extract key improvements for quick reference
        key_metrics = [
            'avg_travel_time',
            'avg_waiting_time', 
            'throughput',
            'avg_speed',
            'total_time_loss'
        ]
        
        for metric in key_metrics:
            pct_change_key = f'{metric}_pct_change'
            if pct_change_key in metrics_comparison:
                result['key_improvements'][metric] = metrics_comparison[pct_change_key]
        
        # Calculate overall effectiveness score (custom weighted score)
        weights = {
            'avg_travel_time': -0.3,     # Negative because lower is better
            'avg_waiting_time': -0.3,    # Negative because lower is better
            'throughput': 0.15,          # Positive because higher is better
            'avg_speed': 0.15,           # Positive because higher is better
            'total_time_loss': -0.1      # Negative because lower is better
        }
        
        effectiveness_score = 0
        weight_sum = 0
        
        for metric, weight in weights.items():
            pct_change_key = f'{metric}_pct_change'
            if pct_change_key in metrics_comparison:
                effectiveness_score += metrics_comparison[pct_change_key] * weight
                weight_sum += abs(weight)
        
        if weight_sum > 0:
            result['effectiveness_score'] = effectiveness_score / weight_sum
        else:
            result['effectiveness_score'] = 0
            
        # Cache the result
        self.results_cache[cache_key] = result
        
        return result
    
    def analyze_all_pairs(self) -> pd.DataFrame:
        """
        Analyze all baseline-adaptive scenario pairs.
        
        Returns:
            DataFrame with analysis results for all scenario pairs
        """
        # Identify scenario pairs
        pairs = self.identify_scenario_pairs()
        
        if not pairs:
            print("No baseline-adaptive scenario pairs found!")
            return pd.DataFrame()
        
        # Compare each pair
        results = []
        
        for pair in pairs:
            try:
                comparison = self.compare_single_pair(pair['baseline_id'], pair['adaptive_id'])
                
                # Extract key metrics for DataFrame
                row = {
                    'baseline_id': pair['baseline_id'],
                    'adaptive_id': pair['adaptive_id'],
                    'rain_mm': pair['rain_mm'],
                    'effectiveness_score': comparison.get('effectiveness_score', 0)
                }
                
                # Add key metric improvements
                for metric, value in comparison.get('key_improvements', {}).items():
                    row[f'{metric}_improvement'] = value
                
                results.append(row)
                
            except Exception as e:
                print(f"Error analyzing pair {pair['baseline_id']} vs {pair['adaptive_id']}: {e}")
        
        # Create DataFrame
        return pd.DataFrame(results)
    
    def analyze_by_rainfall(self) -> pd.DataFrame:
        """
        Analyze the effectiveness of adaptive strategies across different rainfall intensities.
        
        Returns:
            DataFrame with effectiveness scores at different rainfall levels
        """
        # Get all pairs and their analysis
        all_pairs = self.analyze_all_pairs()
        
        if all_pairs.empty:
            return pd.DataFrame()
            
        # Group by rainfall amount
        rainfall_analysis = all_pairs.groupby('rain_mm').agg({
            'effectiveness_score': ['mean', 'std', 'count'],
            'avg_travel_time_improvement': ['mean', 'std'],
            'avg_waiting_time_improvement': ['mean', 'std'],
            'throughput_improvement': ['mean', 'std'],
            'baseline_id': 'first',
            'adaptive_id': 'first'
        })
        
        # Flatten multi-index columns
        rainfall_analysis.columns = [f'{col[0]}_{col[1]}' if col[1] else col[0] 
                                   for col in rainfall_analysis.columns]
        
        # Reset index for easier plotting
        rainfall_analysis = rainfall_analysis.reset_index()
        
        return rainfall_analysis
    
    def plot_effectiveness_by_rainfall(self, save_path: Optional[str] = None):
        """
        Plot the effectiveness of adaptive strategies vs rainfall intensity.
        
        Args:
            save_path: Optional path to save the plot
        """
        rainfall_analysis = self.analyze_by_rainfall()
        
        if rainfall_analysis.empty:
            print("No data available for plotting!")
            return
            
        plt.figure(figsize=(10, 6))
        
        # Plot effectiveness score vs rainfall
        plt.errorbar(
            rainfall_analysis['rain_mm'],
            rainfall_analysis['effectiveness_score_mean'],
            yerr=rainfall_analysis['effectiveness_score_std'],
            marker='o',
            capsize=5,
            linestyle='-',
            linewidth=2
        )
        
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.xlabel('Rainfall Intensity (mm/h)')
        plt.ylabel('Effectiveness Score')
        plt.title('Effectiveness of Adaptive Traffic Management vs Rainfall Intensity')
        
        # Add count annotations
        for i, row in rainfall_analysis.iterrows():
            plt.annotate(
                f"n={int(row['effectiveness_score_count'])}",
                (row['rain_mm'], row['effectiveness_score_mean']),
                textcoords="offset points",
                xytext=(0, 10),
                ha='center'
            )
            
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path)
            print(f"Plot saved to {save_path}")
            
        plt.show()
    
    def plot_metric_improvements(self, 
                               metrics: Optional[List[str]] = None,
                               save_path: Optional[str] = None):
        """
        Plot the improvement of key metrics across different rainfall intensities.
        
        Args:
            metrics: List of metrics to plot (defaults to key metrics)
            save_path: Optional path to save the plot
        """
        if metrics is None:
            metrics = [
                'avg_travel_time',
                'avg_waiting_time',
                'throughput',
                'avg_speed'
            ]
            
        rainfall_analysis = self.analyze_by_rainfall()
        
        if rainfall_analysis.empty:
            print("No data available for plotting!")
            return
            
        plt.figure(figsize=(12, 8))
        
        for metric in metrics:
            improvement_col = f'{metric}_improvement_mean'
            std_col = f'{metric}_improvement_std'
            
            if improvement_col in rainfall_analysis.columns:
                plt.errorbar(
                    rainfall_analysis['rain_mm'],
                    rainfall_analysis[improvement_col],
                    yerr=rainfall_analysis[std_col] if std_col in rainfall_analysis.columns else None,
                    marker='o',
                    capsize=5,
                    label=metric.replace('_', ' ').title()
                )
        
        plt.axhline(y=0, color='k', linestyle='-', alpha=0.3)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.xlabel('Rainfall Intensity (mm/h)')
        plt.ylabel('Improvement (%)')
        plt.title('Performance Metrics Improvement vs Rainfall Intensity')
        plt.legend()
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path)
            print(f"Plot saved to {save_path}")
            
        plt.show()
    
    def create_effectiveness_heatmap(self, 
                                   metrics: Optional[List[str]] = None,
                                   save_path: Optional[str] = None):
        """
        Create a heatmap showing the effectiveness of adaptive strategies
        for different metrics across rainfall intensities.
        
        Args:
            metrics: List of metrics to include (defaults to key metrics)
            save_path: Optional path to save the plot
        """
        if metrics is None:
            metrics = [
                'avg_travel_time',
                'avg_waiting_time', 
                'throughput',
                'avg_speed',
                'total_time_loss'
            ]
            
        rainfall_analysis = self.analyze_by_rainfall()
        
        if rainfall_analysis.empty:
            print("No data available for heatmap!")
            return
            
        # Create matrix for heatmap
        heatmap_data = []
        metric_labels = []
        
        for metric in metrics:
            improvement_col = f'{metric}_improvement_mean'
            
            if improvement_col in rainfall_analysis.columns:
                heatmap_data.append(rainfall_analysis[improvement_col].values)
                metric_labels.append(metric.replace('_', ' ').title())
        
        if not heatmap_data:
            print("No metric improvement data available for heatmap!")
            return
            
        # Convert to numpy array
        heatmap_array = np.array(heatmap_data)
        
        # Create heatmap
        plt.figure(figsize=(10, 8))
        ax = sns.heatmap(
            heatmap_array,
            annot=True,
            fmt=".1f",
            cmap="RdYlGn",
            center=0,
            cbar_kws={'label': 'Improvement (%)'},
            xticklabels=rainfall_analysis['rain_mm'].values,
            yticklabels=metric_labels
        )
        
        plt.title('Effectiveness of Adaptive Strategies by Rainfall Intensity')
        plt.xlabel('Rainfall Intensity (mm/h)')
        plt.ylabel('Metrics')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path)
            print(f"Heatmap saved to {save_path}")
            
        plt.show()
    
    def generate_summary_report(self, output_file: Optional[str] = None) -> pd.DataFrame:
        """
        Generate a comprehensive summary report of all comparative analyses.
        
        Args:
            output_file: Optional path to save the report as CSV
            
        Returns:
            DataFrame with summary report
        """
        # Get all pairs analysis
        all_pairs = self.analyze_all_pairs()
        
        if all_pairs.empty:
            print("No data available for summary report!")
            return pd.DataFrame()
            
        # Get rainfall analysis
        rainfall_analysis = self.analyze_by_rainfall()
        
        # Create detailed report
        report = all_pairs.copy()
        
        # Add columns indicating whether metrics improved
        for metric in ['avg_travel_time', 'avg_waiting_time', 'throughput', 'avg_speed']:
            improvement_col = f'{metric}_improvement'
            if improvement_col in report.columns:
                # For travel time and waiting time, negative is good
                if metric in ['avg_travel_time', 'avg_waiting_time']:
                    report[f'{metric}_improved'] = report[improvement_col] < 0
                else:
                    report[f'{metric}_improved'] = report[improvement_col] > 0
        
        # Calculate success rate (percentage of improved metrics)
        improved_columns = [col for col in report.columns if col.endswith('_improved')]
        if improved_columns:
            report['success_rate'] = report[improved_columns].mean(axis=1) * 100
        
        # Save report if output file is specified
        if output_file:
            report.to_csv(output_file, index=False)
            print(f"Summary report saved to {output_file}")
            
        return report
    
    def plot_comparative_boxplots(self, 
                                metrics: Optional[List[str]] = None,
                                save_path: Optional[str] = None):
        """
        Plot boxplots comparing metric improvements across different rainfall intensities.
        
        Args:
            metrics: List of metrics to plot (defaults to key metrics)
            save_path: Optional path to save the plot
        """
        if metrics is None:
            metrics = [
                'avg_travel_time_improvement',
                'avg_waiting_time_improvement', 
                'throughput_improvement',
                'avg_speed_improvement'
            ]
            
        # Get all pairs analysis
        all_pairs = self.analyze_all_pairs()
        
        if all_pairs.empty or not all(metric in all_pairs.columns for metric in metrics):
            print("Required metrics not available for boxplot!")
            return
            
        # Create boxplot
        plt.figure(figsize=(12, 6))
        
        # Convert rainfall to categorical for boxplot
        all_pairs['rain_category'] = all_pairs['rain_mm'].astype(str) + ' mm/h'
        
        # Melt DataFrame for seaborn
        plot_data = pd.melt(
            all_pairs,
            id_vars=['rain_category'],
            value_vars=metrics,
            var_name='Metric',
            value_name='Improvement (%)'
        )
        
        # Clean metric names for display
        plot_data['Metric'] = plot_data['Metric'].str.replace('_improvement', '').str.replace('_', ' ').str.title()
        
        # Create boxplot
        sns.boxplot(
            x='rain_category',
            y='Improvement (%)',
            hue='Metric',
            data=plot_data
        )
        
        plt.axhline(y=0, color='k', linestyle='-', alpha=0.3)
        plt.grid(True, axis='y', linestyle='--', alpha=0.7)
        plt.title('Distribution of Performance Improvements by Rainfall Intensity')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path)
            print(f"Boxplot saved to {save_path}")
            
        plt.show()


if __name__ == "__main__":
    # Example usage
    analyzer = ComparativeAnalysis("data/output")
    
    # Identify and analyze all baseline-adaptive pairs
    pairs = analyzer.identify_scenario_pairs()
    
    if pairs:
        print(f"Found {len(pairs)} baseline-adaptive scenario pairs:")
        
        for i, pair in enumerate(pairs, 1):
            print(f"{i}. Baseline: {pair['baseline_id']} vs Adaptive: {pair['adaptive_id']} (Rain: {pair['rain_mm']} mm)")
            
        # Analyze first pair in detail
        first_pair = pairs[0]
        comparison = analyzer.compare_single_pair(first_pair['baseline_id'], first_pair['adaptive_id'])
        
        print("\nDetailed comparison for first pair:")
        print(f"Effectiveness score: {comparison['effectiveness_score']:.2f}")
        
        print("\nKey improvements:")
        for metric, value in comparison['key_improvements'].items():
            print(f"  {metric}: {value:.2f}%")
            
        # Generate plots
        print("\nGenerating analysis plots...")
        analyzer.plot_effectiveness_by_rainfall()
        analyzer.plot_metric_improvements()
        analyzer.create_effectiveness_heatmap()
    else:
        print("No scenario pairs found. Check output directory.")