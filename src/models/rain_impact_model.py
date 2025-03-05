"""
Rain Impact Model for Traffic Simulation

This module provides models to calculate the impact of rain on various
traffic parameters including:
- Speed reduction
- Headway increase
- Lane capacity decrease
- Driver behavior changes

The models are calibrated based on empirical studies of rainfall effects
on traffic conditions.
"""

import numpy as np
import pandas as pd
from enum import Enum
from typing import Dict, Tuple, Optional, Union, List


class RainIntensity(Enum):
    """Enum for categorizing rain intensity levels based on mm/h."""
    NONE = 0       # 0 mm/h
    LIGHT = 1      # 0.1-2.5 mm/h
    MODERATE = 2   # 2.5-10 mm/h
    HEAVY = 3      # 10-50 mm/h
    SEVERE = 4     # >50 mm/h


class RainImpactModel:
    """Model for calculating the impact of rain on traffic parameters."""
    
    # Default impact coefficients based on literature
    # Values represent multiplicative factors for each parameter
    DEFAULT_COEFFICIENTS = {
        # Speed reduction factors for each rain intensity level
        "speed": {
            RainIntensity.NONE: 1.0,      # No reduction
            RainIntensity.LIGHT: 0.95,    # 5% reduction
            RainIntensity.MODERATE: 0.90, # 10% reduction
            RainIntensity.HEAVY: 0.82,    # 18% reduction
            RainIntensity.SEVERE: 0.75,   # 25% reduction
        },
        # Headway increase factors
        "headway": {
            RainIntensity.NONE: 1.0,      # No increase
            RainIntensity.LIGHT: 1.10,    # 10% increase
            RainIntensity.MODERATE: 1.25, # 25% increase
            RainIntensity.HEAVY: 1.40,    # 40% increase
            RainIntensity.SEVERE: 1.60,   # 60% increase
        },
        # Lane capacity reduction factors
        "capacity": {
            RainIntensity.NONE: 1.0,      # No reduction
            RainIntensity.LIGHT: 0.93,    # 7% reduction
            RainIntensity.MODERATE: 0.85, # 15% reduction
            RainIntensity.HEAVY: 0.76,    # 24% reduction
            RainIntensity.SEVERE: 0.65,   # 35% reduction
        },
        # Driver behavior parameters (e.g., aggressiveness reduction)
        "driver_behavior": {
            RainIntensity.NONE: 1.0,      # No change
            RainIntensity.LIGHT: 0.90,    # 10% reduction in aggressiveness
            RainIntensity.MODERATE: 0.82, # 18% reduction
            RainIntensity.HEAVY: 0.70,    # 30% reduction
            RainIntensity.SEVERE: 0.60,   # 40% reduction
        }
    }
    
    def __init__(self, custom_coefficients: Optional[Dict] = None):
        """
        Initialize the rain impact model with default or custom coefficients.
        
        Args:
            custom_coefficients: Optional dictionary to override default coefficients
        """
        self.coefficients = self.DEFAULT_COEFFICIENTS.copy()
        
        # Update with any custom coefficients
        if custom_coefficients:
            for param, values in custom_coefficients.items():
                if param in self.coefficients:
                    self.coefficients[param].update(values)
    
    @staticmethod
    def categorize_rainfall(rainfall_mm_h: float) -> RainIntensity:
        """
        Categorize rainfall into intensity levels based on mm/h.
        
        Args:
            rainfall_mm_h: Rainfall intensity in mm/h
            
        Returns:
            RainIntensity enum value
        """
        if rainfall_mm_h <= 0:
            return RainIntensity.NONE
        elif rainfall_mm_h <= 2.5:
            return RainIntensity.LIGHT
        elif rainfall_mm_h <= 10:
            return RainIntensity.MODERATE
        elif rainfall_mm_h <= 50:
            return RainIntensity.HEAVY
        else:
            return RainIntensity.SEVERE
    
    def get_parameter_adjustment(self, 
                                parameter: str, 
                                rainfall_mm_h: float) -> float:
        """
        Get the adjustment factor for a specific traffic parameter based on rainfall.
        
        Args:
            parameter: Traffic parameter ('speed', 'headway', 'capacity', 'driver_behavior')
            rainfall_mm_h: Rainfall intensity in mm/h
            
        Returns:
            Adjustment factor as a float
        
        Raises:
            ValueError: If parameter is not supported
        """
        if parameter not in self.coefficients:
            valid_params = list(self.coefficients.keys())
            raise ValueError(f"Parameter '{parameter}' not supported. Valid parameters: {valid_params}")
            
        intensity = self.categorize_rainfall(rainfall_mm_h)
        return self.coefficients[parameter][intensity]
    
    def get_all_adjustments(self, rainfall_mm_h: float) -> Dict[str, float]:
        """
        Get adjustment factors for all traffic parameters based on rainfall.
        
        Args:
            rainfall_mm_h: Rainfall intensity in mm/h
            
        Returns:
            Dictionary of parameter adjustments
        """
        intensity = self.categorize_rainfall(rainfall_mm_h)
        return {
            param: values[intensity] 
            for param, values in self.coefficients.items()
        }
    
    def apply_adjustments(self, 
                         traffic_params: Dict[str, float], 
                         rainfall_mm_h: float) -> Dict[str, float]:
        """
        Apply rain adjustments to a set of traffic parameters.
        
        Args:
            traffic_params: Dictionary of traffic parameters
            rainfall_mm_h: Rainfall intensity in mm/h
            
        Returns:
            Dictionary of adjusted traffic parameters
        """
        adjustments = self.get_all_adjustments(rainfall_mm_h)
        adjusted_params = {}
        
        for param, value in traffic_params.items():
            if param in adjustments:
                adjusted_params[param] = value * adjustments[param]
            else:
                adjusted_params[param] = value
                
        return adjusted_params
    
    def generate_temporal_adjustments(self, 
                                     rainfall_series: pd.Series,
                                     parameters: List[str]) -> pd.DataFrame:
        """
        Generate time series of adjustment factors based on rainfall time series.
        
        Args:
            rainfall_series: Pandas Series with rainfall data (mm/h) and datetime index
            parameters: List of traffic parameters to generate adjustments for
            
        Returns:
            DataFrame with adjustment factors for each parameter over time
        """
        # Validate parameters
        invalid_params = [p for p in parameters if p not in self.coefficients]
        if invalid_params:
            valid_params = list(self.coefficients.keys())
            raise ValueError(f"Parameters {invalid_params} not supported. Valid parameters: {valid_params}")
        
        # Initialize result DataFrame with same index as rainfall series
        adjustments = pd.DataFrame(index=rainfall_series.index)
        
        # Calculate adjustments for each parameter
        for param in parameters:
            adjustments[param] = rainfall_series.apply(
                lambda x: self.get_parameter_adjustment(param, x)
            )
            
        return adjustments
    
    def calibrate_from_data(self, 
                           traffic_data: pd.DataFrame,
                           rainfall_data: pd.DataFrame,
                           parameters: List[str]) -> None:
        """
        Calibrate model coefficients from observed traffic and rainfall data.
        
        This method adjusts the coefficients to better match observed impacts
        of rainfall on traffic parameters.
        
        Args:
            traffic_data: DataFrame with traffic parameters
            rainfall_data: DataFrame with rainfall measurements
            parameters: List of parameters to calibrate
            
        Note:
            Both DataFrames must share a common time index for alignment
        """
        # This is a placeholder for actual calibration logic
        # In a real implementation, this would use statistical methods to derive
        # new coefficients from the observed relationship between rainfall and
        # traffic parameters
        
        print("Model calibration from empirical data not yet implemented")
        # TODO: Implement coefficient calibration from data
        pass


# Utility functions
def estimate_visibility_reduction(rainfall_mm_h: float) -> float:
    """
    Estimate visibility reduction factor based on rainfall intensity.
    
    Args:
        rainfall_mm_h: Rainfall intensity in mm/h
        
    Returns:
        Visibility factor (1.0 = no reduction, 0.0 = complete reduction)
    """
    # Simple model: visibility declines exponentially with rainfall intensity
    # Based on empirical studies of rainfall vs. visibility
    if rainfall_mm_h <= 0:
        return 1.0
    
    # Parameters tuned to match typical visibility reports
    base_factor = 0.95
    decay_rate = 0.04
    
    visibility_factor = base_factor * np.exp(-decay_rate * rainfall_mm_h)
    return max(0.1, visibility_factor)  # Ensure minimum visibility of 10%


def estimate_road_friction(rainfall_mm_h: float, 
                         road_type: str = "asphalt",
                         time_since_rain_start_min: Optional[float] = None) -> float:
    """
    Estimate road friction coefficient based on rainfall, road type and duration.
    
    Args:
        rainfall_mm_h: Rainfall intensity in mm/h
        road_type: Type of road surface
        time_since_rain_start_min: Minutes since rainfall began
        
    Returns:
        Friction coefficient (lower values = more slippery)
    """
    # Base friction coefficients for different road types (dry conditions)
    base_friction = {
        "asphalt": 0.85,
        "concrete": 0.80,
        "gravel": 0.60,
        "dirt": 0.68
    }
    
    # Use asphalt as default if road_type not recognized
    if road_type not in base_friction:
        road_type = "asphalt"
        
    base = base_friction[road_type]
    
    if rainfall_mm_h <= 0:
        return base
    
    # Initial friction reduction just from wet surface
    wet_reduction = 0.15  # 15% reduction when wet
    
    # Further reduction based on rainfall intensity
    intensity_factor = 0.05 * np.log1p(rainfall_mm_h)  # logarithmic reduction
    
    # Time factor - roads are most slippery when rain first starts
    time_factor = 0.0
    if time_since_rain_start_min is not None:
        # First 10 minutes are most slippery (oil/debris being washed)
        if time_since_rain_start_min < 10:
            time_factor = 0.1 * (1 - time_since_rain_start_min / 10)
    
    # Calculate total friction, ensure it doesn't go below reasonable values
    friction = base * (1 - wet_reduction - intensity_factor - time_factor)
    return max(0.3, friction)  # Ensure friction doesn't go below 0.3


if __name__ == "__main__":
    # Example usage
    model = RainImpactModel()
    
    # Test with different rainfall intensities
    test_rainfall = [0, 1.5, 5.0, 15.0, 60.0]
    
    print("Rain Impact Model - Test Results")
    print("-" * 50)
    print(f"{'Rainfall (mm/h)':<15} {'Speed':<10} {'Headway':<10} {'Capacity':<10}")
    print("-" * 50)
    
    for rain in test_rainfall:
        adj = model.get_all_adjustments(rain)
        intensity = model.categorize_rainfall(rain)
        print(f"{rain:<15.1f} {adj['speed']:<10.2f} {adj['headway']:<10.2f} {adj['capacity']:<10.2f} ({intensity.name})")