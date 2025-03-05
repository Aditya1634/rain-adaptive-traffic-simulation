"""
Statistical Tests Module

This module provides statistical validation of simulation results,
ensuring that observed differences between baseline and rain-adaptive
traffic management approaches are statistically significant.
"""

import numpy as np
import pandas as pd
import scipy.stats as stats
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple, Optional, Union
from pathlib import Path
import os
import xml.etree.ElementTree as ET

from .performance_metrics import PerformanceMetrics


class StatisticalTests:
    """
    Statistical analysis and hypothesis testing for traffic simulation results.
    """
    
    def __init__(self, output_dir: Union[str, Path]):
        """
        Initialize with path to simulation output directory.
        
        Args:
            output_dir: Directory containing simulation output files
        """
        self.output_dir = Path(output_dir)
        self.metrics = PerformanceMetrics(output_dir)
    
    def extract_vehicle_data(self, simulation_id: str) -> pd.DataFrame:
        """
        Extract individual vehicle data from tripinfo files for statistical tests.
        
        Args:
            simulation_id: Simulation identifier
            
        Returns:
            DataFrame with vehicle-level data
        """
        tripinfo_file = self.output_dir / f"{simulation_id}_tripinfo.xml"
        
        if not tripinfo_file.exists():
            raise FileNotFoundError(f"Trip information file not found: {tripinfo_file}")
        
        # Parse XML
        tree = ET.parse(tripinfo_file)
        root = tree.getroot()
        
        # Extract vehicle data
        vehicles = []
        for vehicle in root.findall('tripinfo'):
            vehicle_data = vehicle.attrib
            
            # Convert string values to appropriate types
            vehicle_dict = {
                'id': vehicle_data.get('id', ''),
                'vehicle_type': vehicle_data.get('vType', ''),
                'depart': float(vehicle_data.get('depart', 0)),
                'arrival': float(vehicle_data.get('arrival', 0)),
                'duration': float(vehicle_data.get('duration', 0)),
                'waiting_time': float(vehicle_data.get('waitingTime', 0)),
                'time_loss': float(vehicle_data.get('timeLoss', 0)),
                'distance': float(vehicle_data.get('routeLength', 0)),
                'avg_speed': float(vehicle_data.get('routeLength', 0)) / max(float(vehicle_data.get('duration', 1)), 1)
            }
            
            # Add route and edge information if available
            if 'route' in vehicle_data:
                vehicle_dict['route'] = vehicle_data['route']
                
            vehicles.append(vehicle_dict)
        
        # Create DataFrame
        df = pd.DataFrame(vehicles)
        
        # Add simulation ID for tracking
        df['simulation_id'] = simulation_id
        
        return df
    
    def t_test_travel_times(self, baseline_id: str, adaptive_id: str) -> Dict:
        """
        Perform t-test on travel times between baseline and adaptive scenarios.
        
        Args:
            baseline_id: Baseline scenario identifier
            adaptive_id: Adaptive scenario identifier
            
        Returns:
            Dictionary with t-test results
        """
        try:
            # Extract vehicle data
            baseline_data = self.extract_vehicle_data(baseline_id)
            adaptive_data = self.extract_vehicle_data(adaptive_id)
            
            # Perform t-test on travel durations
            t_stat, p_value = stats.ttest_ind(
                baseline_data['duration'],
                adaptive_data['duration'],
                equal_var=False  # Welch's t-test, doesn't assume equal variances
            )
            
            # Calculate effect size (Cohen's d)
            baseline_mean = baseline_data['duration'].mean()
            baseline_std = baseline_data['duration'].std()
            adaptive_mean = adaptive_data['duration'].mean()
            adaptive_std = adaptive_data['duration'].std()
            
            # Pooled standard deviation
            pooled_std = np.sqrt((baseline_std**2 + adaptive_std**2) / 2)
            
            # Cohen's d
            cohens_d = (baseline_mean - adaptive_mean) / pooled_std
            
            # Interpret effect size
            if abs(cohens_d) < 0.2:
                effect_interpretation = "negligible"
            elif abs(cohens_d) < 0.5:
                effect_interpretation = "small"
            elif abs(cohens_d) < 0.8:
                effect_interpretation = "medium"
            else:
                effect_interpretation = "large"
                
            # Determine if difference is significant at 0.05
            # Determine if difference is significant at 0.05
            is_significant = p_value < 0.05
            
            # Prepare results
            results = {
                'test_type': "Welch's t-test",
                'metric': 'travel_time',
                'baseline_n': len(baseline_data),
                'adaptive_n': len(adaptive_data),
                'baseline_mean': baseline_mean,
                'adaptive_mean': adaptive_mean,
                'baseline_std': baseline_std,
                'adaptive_std': adaptive_std,
                'mean_difference': baseline_mean - adaptive_mean,
                'percent_improvement': ((baseline_mean - adaptive_mean) / baseline_mean) * 100,
                't_statistic': t_stat,
                'p_value': p_value,
                'cohens_d': cohens_d,
                'effect_size': effect_interpretation,
                'is_significant': is_significant
            }
            
            return results
            
        except Exception as e:
            print(f"Error performing t-test: {e}")
            return {
                'error': str(e),
                'test_type': "Welch's t-test",
                'metric': 'travel_time',
                'is_significant': False
            }
    
    def anova_compare_multiple(self, simulation_ids: List[str], metric: str = 'duration') -> Dict:
        """
        Perform one-way ANOVA to compare multiple simulation scenarios.
        
        Args:
            simulation_ids: List of simulation identifiers to compare
            metric: Vehicle metric to compare (duration, waiting_time, etc.)
            
        Returns:
            Dictionary with ANOVA results
        """
        try:
            # Extract vehicle data for all simulations
            data_frames = []
            for sim_id in simulation_ids:
                df = self.extract_vehicle_data(sim_id)
                df['scenario'] = sim_id  # Add scenario label
                data_frames.append(df)
            
            # Combine data
            combined_data = pd.concat(data_frames)
            
            # Check if selected metric exists
            if metric not in combined_data.columns:
                raise ValueError(f"Metric '{metric}' not found in vehicle data")
            
            # Group data by scenario
            groups = [combined_data[combined_data['scenario'] == scenario][metric] 
                     for scenario in simulation_ids]
            
            # Perform ANOVA
            f_stat, p_value = stats.f_oneway(*groups)
            
            # Calculate means and standard deviations for each group
            group_stats = {}
            for i, scenario in enumerate(simulation_ids):
                group_stats[scenario] = {
                    'n': len(groups[i]),
                    'mean': groups[i].mean(),
                    'std': groups[i].std()
                }
            
            # Calculate effect size (Eta-squared)
            # Sum of squares between groups
            ss_between = sum(len(group) * (group.mean() - combined_data[metric].mean())**2 
                             for group in groups)
            # Sum of squares total
            ss_total = sum((combined_data[metric] - combined_data[metric].mean())**2)
            
            eta_squared = ss_between / ss_total if ss_total > 0 else 0
            
            # Interpret effect size
            if eta_squared < 0.01:
                effect_interpretation = "negligible"
            elif eta_squared < 0.06:
                effect_interpretation = "small"
            elif eta_squared < 0.14:
                effect_interpretation = "medium"
            else:
                effect_interpretation = "large"
            
            # Prepare results
            results = {
                'test_type': 'One-way ANOVA',
                'metric': metric,
                'scenarios': simulation_ids,
                'group_stats': group_stats,
                'f_statistic': f_stat,
                'p_value': p_value,
                'eta_squared': eta_squared,
                'effect_size': effect_interpretation,
                'is_significant': p_value < 0.05
            }
            
            return results
            
        except Exception as e:
            print(f"Error performing ANOVA: {e}")
            return {
                'error': str(e),
                'test_type': 'One-way ANOVA',
                'metric': metric,
                'is_significant': False
            }
    
    def mann_whitney_test(self, baseline_id: str, adaptive_id: str, metric: str = 'duration') -> Dict:
        """
        Perform Mann-Whitney U test (non-parametric) for comparing two independent samples.
        Useful when assumptions of t-test are not met.
        
        Args:
            baseline_id: Baseline scenario identifier
            adaptive_id: Adaptive scenario identifier
            metric: Vehicle metric to compare
            
        Returns:
            Dictionary with test results
        """
        try:
            # Extract vehicle data
            baseline_data = self.extract_vehicle_data(baseline_id)
            adaptive_data = self.extract_vehicle_data(adaptive_id)
            
            # Check if selected metric exists
            if metric not in baseline_data.columns or metric not in adaptive_data.columns:
                raise ValueError(f"Metric '{metric}' not found in vehicle data")
            
            # Perform Mann-Whitney U test
            u_stat, p_value = stats.mannwhitneyu(
                baseline_data[metric],
                adaptive_data[metric],
                alternative='two-sided'
            )
            
            # Calculate medians for reporting
            baseline_median = baseline_data[metric].median()
            adaptive_median = adaptive_data[metric].median()
            
            # Calculate effect size (r) - standardized measure
            n1 = len(baseline_data)
            n2 = len(adaptive_data)
            
            # r = Z / sqrt(N)
            z_score = stats.norm.ppf(1 - p_value/2) * (1 if p_value < 0.5 else -1)
            r_effect = abs(z_score / np.sqrt(n1 + n2))
            
            # Interpret effect size
            if r_effect < 0.1:
                effect_interpretation = "negligible"
            elif r_effect < 0.3:
                effect_interpretation = "small"
            elif r_effect < 0.5:
                effect_interpretation = "medium"
            else:
                effect_interpretation = "large"
            
            # Prepare results
            results = {
                'test_type': 'Mann-Whitney U test',
                'metric': metric,
                'baseline_n': n1,
                'adaptive_n': n2,
                'baseline_median': baseline_median,
                'adaptive_median': adaptive_median,
                'median_difference': baseline_median - adaptive_median,
                'percent_improvement': ((baseline_median - adaptive_median) / baseline_median) * 100,
                'u_statistic': u_stat,
                'p_value': p_value,
                'effect_size_r': r_effect,
                'effect_size': effect_interpretation,
                'is_significant': p_value < 0.05
            }
            
            return results
            
        except Exception as e:
            print(f"Error performing Mann-Whitney U test: {e}")
            return {
                'error': str(e),
                'test_type': 'Mann-Whitney U test',
                'metric': metric,
                'is_significant': False
            }
    
    def visualize_comparative_boxplot(self, simulation_ids: List[str], 
                                    metric: str = 'duration', 
                                    title: Optional[str] = None,
                                    save_path: Optional[str] = None) -> None:
        """
        Create boxplot visualization comparing distributions across multiple scenarios.
        
        Args:
            simulation_ids: List of simulation identifiers to compare
            metric: Vehicle metric to visualize
            title: Plot title (optional)
            save_path: Path to save visualization (optional)
        """
        try:
            # Extract and combine data
            data_frames = []
            for sim_id in simulation_ids:
                df = self.extract_vehicle_data(sim_id)
                df['scenario'] = sim_id  # Add scenario label
                data_frames.append(df)
            
            combined_data = pd.concat(data_frames)
            
            # Check if selected metric exists
            if metric not in combined_data.columns:
                raise ValueError(f"Metric '{metric}' not found in vehicle data")
                
            # Set up plotting
            plt.figure(figsize=(10, 6))
            
            # Create boxplot
            ax = sns.boxplot(x='scenario', y=metric, data=combined_data)
            
            # Add swarmplot for better visualization of data points (if not too many)
            if len(combined_data) < 500:
                sns.swarmplot(x='scenario', y=metric, data=combined_data, 
                             color='0.25', size=3, alpha=0.5)
            
            # Add title and labels
            metric_name = metric.replace('_', ' ').title()
            if title:
                plt.title(title)
            else:
                plt.title(f'Comparison of {metric_name} Across Scenarios')
                
            plt.xlabel('Simulation Scenario')
            plt.ylabel(metric_name)
            
            # Add statistical annotation if only two scenarios
            if len(simulation_ids) == 2:
                # Perform t-test
                t_stat, p_value = stats.ttest_ind(
                    combined_data[combined_data['scenario'] == simulation_ids[0]][metric],
                    combined_data[combined_data['scenario'] == simulation_ids[1]][metric],
                    equal_var=False
                )
                
                # Add p-value annotation
                p_text = f"p = {p_value:.4f}" + (" *" if p_value < 0.05 else "")
                plt.annotate(p_text, xy=(0.5, 0.95), xycoords='axes fraction', 
                            ha='center', va='center', fontsize=12)
            
            plt.tight_layout()
            
            # Save plot if path provided
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                print(f"Plot saved to {save_path}")
                
            plt.show()
            
        except Exception as e:
            print(f"Error creating boxplot visualization: {e}")
    
    def compare_precipitation_impact(self, scenario_pairs: List[Tuple[str, str, float]],
                                   metric: str = 'duration') -> Dict:
        """
        Analyze how different precipitation levels impact the effectiveness of the adaptive system.
        
        Args:
            scenario_pairs: List of tuples (baseline_id, adaptive_id, precipitation_mm)
            metric: Vehicle metric to compare
            
        Returns:
            Dictionary with results for each precipitation level
        """
        try:
            results = {}
            
            for baseline_id, adaptive_id, precip_mm in scenario_pairs:
                # Get t-test results
                t_test_results = self.t_test_travel_times(baseline_id, adaptive_id)
                
                # Extract key metrics
                improvement = t_test_results.get('percent_improvement', 0)
                p_value = t_test_results.get('p_value', 1.0)
                effect_size = t_test_results.get('cohens_d', 0)
                
                # Store results keyed by precipitation level
                results[precip_mm] = {
                    'baseline_id': baseline_id,
                    'adaptive_id': adaptive_id,
                    'precipitation_mm': precip_mm,
                    'percent_improvement': improvement,
                    'p_value': p_value,
                    'effect_size': effect_size,
                    'is_significant': p_value < 0.05
                }
            
            # Sort results by precipitation level
            sorted_results = {k: results[k] for k in sorted(results.keys())}
            
            return sorted_results
            
        except Exception as e:
            print(f"Error analyzing precipitation impact: {e}")
            return {'error': str(e)}
    
    def visualize_precipitation_impact(self, scenario_pairs: List[Tuple[str, str, float]],
                                     metric: str = 'duration',
                                     save_path: Optional[str] = None) -> None:
        """
        Create visualization showing how improvement varies with precipitation intensity.
        
        Args:
            scenario_pairs: List of tuples (baseline_id, adaptive_id, precipitation_mm)
            metric: Vehicle metric to visualize
            save_path: Path to save visualization (optional)
        """
        try:
            # Get comparison results
            results = self.compare_precipitation_impact(scenario_pairs, metric)
            
            # Extract data for plotting
            precip_levels = []
            improvements = []
            significance = []
            
            for precip, data in sorted(results.items()):
                if isinstance(precip, (int, float)) and 'percent_improvement' in data:
                    precip_levels.append(precip)
                    improvements.append(data['percent_improvement'])
                    significance.append(data['is_significant'])
            
            # Set up plotting
            plt.figure(figsize=(10, 6))
            
            # Create scatter plot
            colors = ['green' if sig else 'gray' for sig in significance]
            plt.scatter(precip_levels, improvements, color=colors, s=100, alpha=0.7)
            
            # Add connecting line
            plt.plot(precip_levels, improvements, 'b--', alpha=0.5)
            
            # Add labels and title
            metric_name = metric.replace('_', ' ').title()
            plt.title(f'Impact of Precipitation on {metric_name} Improvement')
            plt.xlabel('Precipitation Intensity (mm/h)')
            plt.ylabel(f'Improvement in {metric_name} (%)')
            
            # Add zero line
            plt.axhline(y=0, color='r', linestyle='-', alpha=0.3)
            
            # Add significance legend
            plt.scatter([], [], color='green', s=100, label='Statistically Significant')
            plt.scatter([], [], color='gray', s=100, label='Not Significant')
            plt.legend()
            
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            
            # Save plot if path provided
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                print(f"Plot saved to {save_path}")
                
            plt.show()
            
        except Exception as e:
            print(f"Error visualizing precipitation impact: {e}")
    
    def generate_statistical_report(self, baseline_id: str, adaptive_id: str, 
                                  output_file: Optional[str] = None) -> Dict:
        """
        Generate comprehensive statistical report comparing baseline and adaptive scenarios.
        
        Args:
            baseline_id: Baseline scenario identifier
            adaptive_id: Adaptive scenario identifier
            output_file: Path to save report as markdown (optional)
            
        Returns:
            Dictionary with comprehensive results
        """
        try:
            # Collect metrics
            metrics = ['duration', 'waiting_time', 'time_loss', 'avg_speed']
            results = {}
            
            # Run t-tests for each metric
            for metric in metrics:
                if metric == 'duration':
                    # Use existing method for travel times
                    results[metric] = self.t_test_travel_times(baseline_id, adaptive_id)
                else:
                    # Extract vehicle data
                    baseline_data = self.extract_vehicle_data(baseline_id)
                    adaptive_data = self.extract_vehicle_data(adaptive_id)
                    
                    # Perform t-test
                    t_stat, p_value = stats.ttest_ind(
                        baseline_data[metric],
                        adaptive_data[metric],
                        equal_var=False
                    )
                    
                    # Calculate means and effect size
                    baseline_mean = baseline_data[metric].mean()
                    baseline_std = baseline_data[metric].std()
                    adaptive_mean = adaptive_data[metric].mean()
                    adaptive_std = adaptive_data[metric].std()
                    
                    # Pooled standard deviation
                    pooled_std = np.sqrt((baseline_std**2 + adaptive_std**2) / 2)
                    
                    # Cohen's d
                    cohens_d = (baseline_mean - adaptive_mean) / pooled_std
                    
                    # Store results
                    results[metric] = {
                        'test_type': "Welch's t-test",
                        'metric': metric,
                        'baseline_mean': baseline_mean,
                        'adaptive_mean': adaptive_mean,
                        'mean_difference': baseline_mean - adaptive_mean,
                        'percent_improvement': ((baseline_mean - adaptive_mean) / baseline_mean) * 100,
                        't_statistic': t_stat,
                        'p_value': p_value,
                        'cohens_d': cohens_d,
                        'is_significant': p_value < 0.05
                    }
            
            # If output file requested, generate markdown report
            if output_file:
                with open(output_file, 'w') as f:
                    f.write(f"# Statistical Analysis Report\n\n")
                    f.write(f"Comparison between baseline scenario '{baseline_id}' and adaptive scenario '{adaptive_id}'.\n\n")
                    
                    f.write("## Summary of Findings\n\n")
                    significant_metrics = [m for m, r in results.items() if r.get('is_significant', False)]
                    
                    if significant_metrics:
                        f.write("The rain-adaptive traffic management system shows statistically significant improvements in:\n")
                        for metric in significant_metrics:
                            improvement = results[metric]['percent_improvement']
                            f.write(f"- {metric.replace('_', ' ').title()}: {improvement:.2f}% improvement (p={results[metric]['p_value']:.4f})\n")
                    else:
                        f.write("No statistically significant improvements were observed in the analyzed metrics.\n")
                    
                    f.write("\n## Detailed Results\n\n")
                    
                    for metric, result in results.items():
                        f.write(f"### {metric.replace('_', ' ').title()}\n\n")
                        f.write(f"- Baseline mean: {result['baseline_mean']:.2f}\n")
                        f.write(f"- Adaptive mean: {result['adaptive_mean']:.2f}\n")
                        f.write(f"- Absolute difference: {result['mean_difference']:.2f}\n")
                        f.write(f"- Percent improvement: {result['percent_improvement']:.2f}%\n")
                        f.write(f"- t-statistic: {result['t_statistic']:.4f}\n")
                        f.write(f"- p-value: {result['p_value']:.4f}\n")
                        f.write(f"- Effect size (Cohen's d): {result['cohens_d']:.4f}\n")
                        f.write(f"- Statistical significance: {'Yes' if result['is_significant'] else 'No'}\n\n")
                
                print(f"Statistical report generated and saved to {output_file}")
            
            return {
                'scenarios': {
                    'baseline': baseline_id,
                    'adaptive': adaptive_id
                },
                'metric_results': results,
                'summary': {
                    'significant_metrics': [m for m, r in results.items() if r.get('is_significant', False)],
                    'overall_conclusion': "Statistically significant improvements observed" 
                                        if any(r.get('is_significant', False) for r in results.values()) 
                                        else "No statistically significant improvements observed"
                }
            }
            
        except Exception as e:
            print(f"Error generating statistical report: {e}")
            return {'error': str(e)}  