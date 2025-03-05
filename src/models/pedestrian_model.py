# # pedestrian_model.py
# import numpy as np
# from scipy.stats import norm

# class RainAdaptivePedestrianModel:
#     """Model for simulating how pedestrian behavior changes in rain"""
    
#     def __init__(self):
#         # Walking speed parameters (m/s)
#         self.base_walking_speed = 1.4  # Average walking speed in normal conditions
        
#         # Speed reduction factors by rain intensity
#         self.walking_speed_factors = {
#             'no_rain': 1.0,
#             'light_rain': 0.9,  # 10% reduction
#             'moderate_rain': 0.75,  # 25% reduction
#             'heavy_rain': 0.6   # 40% reduction
#         }
        
#         # Crossing decision threshold adjustments
#         # (how much gap pedestrians need to decide to cross)
#         self.crossing_threshold_factors = {
#             'no_rain': 1.0,
#             'light_rain': 1.2,  # Need 20% more gap
#             'moderate_rain': 1.5,  # Need 50% more gap
#             'heavy_rain': 1.8   # Need 80% more gap
#         }
        
#         # Volume adjustment (fewer pedestrians in rain)
#         self.pedestrian_volume_factors = {
#             'no_rain': 1.0,
#             'light_rain': 0.8,  # 20% fewer pedestrians
#             'moderate_rain': 0.6,  # 40% fewer pedestrians
#             'heavy_rain': 0.4   # 60% fewer pedestrians
#         }
    
#     def get_walking_speed(self, rain_category, age_factor=1.0):
#         """Calculate walking speed based on rain and pedestrian age"""
#         base_speed = self.base_walking_speed * age_factor
#         return base_speed * self.walking_speed_factors[rain_category]
    
#     def get_crossing_threshold(self, rain_category, risk_aversion=1.0):
#         """Calculate gap acceptance threshold based on rain and risk aversion"""
#         # Base threshold in seconds (minimum gap needed to cross)
#         base_threshold = 5.0 * risk_aversion
#         return base_threshold * self.crossing_threshold_factors[rain_category]
    
#     def adjust_pedestrian_demand(self, base_demand, rain_category):
#         """Adjust pedestrian demand/volume based on rain intensity"""
#         return base_demand * self.pedestrian_volume_factors[rain_category]
    
#     def generate_pedestrian_population(self, count, rain_category):
#         """Generate a population of pedestrians with varying attributes"""
#         # Age distribution (mean=35, std=15)
#         ages = np.clip(np.random.normal(35, 15, count), 10, 80)
        
#         # Convert age to speed factor (younger = faster, older = slower)
#         age_factors = 1.0 - (ages - 35) * 0.005  # Roughly ±0.5% per year from age 35
        
#         # Risk aversion (higher = more cautious)
#         risk_factors = np.clip(np.random.normal(1.0, 0.2, count), 0.6, 1.4)
        
#         # Calculate actual walking speeds and crossing thresholds
#         walking_speeds = [self.get_walking_speed(rain_category, age_factor) 
#                           for age_factor in age_factors]
        
#         crossing_thresholds = [self.get_crossing_threshold(rain_category, risk_factor)
#                                for risk_factor in risk_factors]
        
#         # Return as a list of dictionaries
#         pedestrians = []
#         for i in range(count):
#             pedestrians.append({
#                 'id': i,
#                 'age': ages[i],
#                 'walking_speed': walking_speeds[i],
#                 'crossing_threshold': crossing_thresholds[i],
#                 'risk_aversion': risk_factors[i]
#             })
        
#         return pedestrians

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pedestrian Behavior Model

This module models how pedestrian behavior changes under different
weather conditions, particularly rainfall, affecting crossing decisions,
walking speed, and route choice.
"""

import os
import sys
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Union, Callable
import random
import math


class PedestrianModel:
    """
    Model for pedestrian behavior adaptation to weather conditions, 
    particularly rain intensity.
    """
    
    def __init__(self, config: dict):
        """
        Initialize the pedestrian behavior model.
        
        Args:
            config (dict): Configuration parameters for the model
        """
        self.config = config
        
        # Default parameters if not specified in config
        self.base_walking_speed = config.get('base_walking_speed', 1.34)  # m/s, average walking speed
        self.base_crossing_wait_time = config.get('base_crossing_wait_time', 15.0)  # seconds
        self.base_detour_tolerance = config.get('base_detour_tolerance', 300)  # meters
        
        # Speed reduction factors based on rain intensity
        self.speed_reduction_factors = config.get('speed_reduction_factors', {
            'normal': 1.0,       # No reduction
            'light': 0.95,       # 5% reduction
            'moderate': 0.9,     # 10% reduction
            'heavy': 0.8,        # 20% reduction
            'extreme': 0.7       # 30% reduction
        })
        
        # Wait time reduction factors (less patient in rain)
        self.wait_time_reduction_factors = config.get('wait_time_reduction_factors', {
            'normal': 1.0,       # No reduction
            'light': 0.9,        # 10% reduction
            'moderate': 0.8,     # 20% reduction
            'heavy': 0.7,        # 30% reduction
            'extreme': 0.6       # 40% reduction
        })
        
        # Detour tolerance reduction (less willing to walk farther in rain)
        self.detour_tolerance_factors = config.get('detour_tolerance_factors', {
            'normal': 1.0,       # No reduction
            'light': 0.9,        # 10% reduction
            'moderate': 0.8,     # 20% reduction
            'heavy': 0.7,        # 30% reduction
            'extreme': 0.5       # 50% reduction
        })
        
        # Probability of seeking shelter during rainfall
        self.shelter_seeking_probability = config.get('shelter_seeking_probability', {
            'normal': 0.0,       # No shelter seeking
            'light': 0.1,        # 10% probability
            'moderate': 0.3,     # 30% probability
            'heavy': 0.6,        # 60% probability
            'extreme': 0.8       # 80% probability
        })
        
        # Trip cancellation/postponement probability
        self.trip_cancellation_probability = config.get('trip_cancellation_probability', {
            'normal': 0.0,       # No cancellation
            'light': 0.05,       # 5% probability
            'moderate': 0.15,    # 15% probability
            'heavy': 0.3,        # 30% probability
            'extreme': 0.5       # 50% probability
        })
        
        # Random seed for reproducibility
        if 'random_seed' in config:
            random.seed(config['random_seed'])
            np.random.seed(config['random_seed'])
            
        # Current weather state
        self.current_rain_category = 'normal'
        self.current_rain_intensity = 0.0
        
    def update_weather(self, rain_category: str, rain_intensity: float):
        """
        Update the current weather conditions.
        
        Args:
            rain_category (str): Rain category ('normal', 'light', 'moderate', 'heavy', 'extreme')
            rain_intensity (float): Rain intensity as a value between 0 and 1
        """
        self.current_rain_category = rain_category.lower()
        self.current_rain_intensity = rain_intensity
        
    def get_walking_speed(self, age_group: Optional[str] = None, 
                         gender: Optional[str] = None) -> float:
        """
        Calculate the adjusted walking speed based on weather and demographic factors.
        
        Args:
            age_group (str, optional): Age group of the pedestrian
            gender (str, optional): Gender of the pedestrian
            
        Returns:
            float: Adjusted walking speed in m/s
        """
        # Base speed, can be modified by age and gender if provided
        base_speed = self.base_walking_speed
        
        # Apply demographic adjustments if configured and provided
        if age_group and 'age_speed_factors' in self.config:
            age_factor = self.config['age_speed_factors'].get(age_group, 1.0)
            base_speed *= age_factor
            
        if gender and 'gender_speed_factors' in self.config:
            gender_factor = self.config['gender_speed_factors'].get(gender, 1.0)
            base_speed *= gender_factor
            
        # Apply weather-based reduction
        weather_factor = self.speed_reduction_factors.get(
            self.current_rain_category, 1.0)
            
        # Calculate final speed
        adjusted_speed = base_speed * weather_factor
        
        return adjusted_speed
        
    def get_crossing_wait_time(self) -> float:
        """
        Calculate the adjusted maximum time a pedestrian will wait to cross.
        
        Returns:
            float: Adjusted maximum crossing wait time in seconds
        """
        weather_factor = self.wait_time_reduction_factors.get(
            self.current_rain_category, 1.0)
            
        adjusted_wait_time = self.base_crossing_wait_time * weather_factor
        
        return adjusted_wait_time
        
    def get_detour_tolerance(self) -> float:
        """
        Calculate how far a pedestrian is willing to detour for shelter/better route.
        
        Returns:
            float: Adjusted detour tolerance in meters
        """
        weather_factor = self.detour_tolerance_factors.get(
            self.current_rain_category, 1.0)
            
        adjusted_tolerance = self.base_detour_tolerance * weather_factor
        
        return adjusted_tolerance
        
    def will_seek_shelter(self) -> bool:
        """
        Determine if a pedestrian will seek shelter based on current rain.
        
        Returns:
            bool: True if the pedestrian will seek shelter
        """
        probability = self.shelter_seeking_probability.get(
            self.current_rain_category, 0.0)
            
        return random.random() < probability
        
    def will_cancel_trip(self) -> bool:
        """
        Determine if a pedestrian will cancel/postpone a trip based on current rain.
        
        Returns:
            bool: True if the pedestrian will cancel the trip
        """
        probability = self.trip_cancellation_probability.get(
            self.current_rain_category, 0.0)
            
        return random.random() < probability
        
    def get_umbrella_probability(self) -> float:
        """
        Calculate the probability that a pedestrian has an umbrella.
        
        Returns:
            float: Probability (0-1) that the pedestrian has an umbrella
        """
        # Base probability - linear increase with rain intensity
        if self.current_rain_category == 'normal':
            return 0.1  # Some people carry umbrellas even when it's not raining
            
        # Probability increases with rain intensity
        return min(0.1 + (self.current_rain_intensity * 0.8), 0.9)
        
    def modify_route_choice(self, original_route: List[str], 
                           shelter_locations: List[Tuple[float, float]]) -> List[str]:
        """
        Modify a pedestrian's route choice based on weather conditions and shelter locations.
        
        Args:
            original_route (List[str]): Original planned route (list of edge IDs)
            shelter_locations (List[Tuple[float, float]]): Locations with shelter (x, y coordinates)
            
        Returns:
            List[str]: Modified route (list of edge IDs)
        """
        # If normal weather or not seeking shelter, keep original route
        if self.current_rain_category == 'normal' or not self.will_seek_shelter():
            return original_route
            
        # In a real implementation, this would calculate a new route that
        # passes by shelter locations, balancing detour distance against rain exposure
        # This is a simplified placeholder implementation
        
        # Simplified: 50% chance of modifying route if seeking shelter
        if random.random() < 0.5:
            # Placeholder for route modification algorithm
            # In a real implementation, would find nearest shelter and route through it
            print("Route would be modified to pass by shelter")
            return original_route  # Return original for now
        
        return original_route
        
    def get_crossing_compliance(self) -> float:
        """
        Calculate probability that a pedestrian will comply with crossing signals.
        
        Returns:
            float: Probability (0-1) of compliance with signals
        """
        # Base compliance probability - decreases with rain intensity
        base_compliance = self.config.get('base_crossing_compliance', 0.9)  # 90% compliance in normal weather
        
        if self.current_rain_category == 'normal':
            return base_compliance
            
        # Compliance decreases with rain intensity (less patient in rain)
        rain_factor = 1.0 - (self.current_rain_intensity * 0.3)  # Up to 30% reduction
        
        return max(base_compliance * rain_factor, 0.6)  # Minimum 60% compliance
        
    def get_pedestrian_flow_adjustment(self) -> float:
        """
        Calculate adjustment factor for pedestrian flow based on weather.
        
        Returns:
            float: Adjustment factor for pedestrian flow generation
        """
        # Base adjustment - pedestrian volume decreases with rain intensity
        if self.current_rain_category == 'normal':
            return 1.0  # No adjustment in normal weather
            
        # Calculate reduction based on both cancellation and intensity
        cancellation_prob = self.trip_cancellation_probability.get(
            self.current_rain_category, 0.0)
            
        # Flow adjustment (reduction) increases with rain intensity
        flow_adjustment = 1.0 - cancellation_prob
        
        return flow_adjustment
        
    def get_flow_distribution_adjustment(self) -> Dict[str, float]:
        """
        Get adjustments for pedestrian flow distribution among different routes.
        
        Returns:
            Dict[str, float]: Adjustment factors for different route types
        """
        # Default distribution adjustment factors
        adjustments = {
            'uncovered': 1.0,   # Outdoor routes with no coverage
            'partially_covered': 1.0,  # Routes with some coverage
            'covered': 1.0,     # Routes with full coverage (e.g., tunnels)
            'indoor': 1.0       # Indoor routes
        }
        
        # No adjustments needed in normal weather
        if self.current_rain_category == 'normal':
            return adjustments
            
        # Calculate adjustment factors based on rain intensity
        # Reduce uncovered routes, increase covered ones
        uncovered_factor = 1.0 - (self.current_rain_intensity * 0.5)  # Up to 50% reduction
        partially_covered_factor = 1.0 - (self.current_rain_intensity * 0.25)  # Up to 25% reduction
        covered_factor = 1.0 + (self.current_rain_intensity * 0.3)  # Up to 30% increase
        indoor_factor = 1.0 + (self.current_rain_intensity * 0.5)  # Up to 50% increase
        
        adjustments['uncovered'] = uncovered_factor
        adjustments['partially_covered'] = partially_covered_factor
        adjustments['covered'] = covered_factor
        adjustments['indoor'] = indoor_factor
        
        return adjustments
        
    def get_sumo_parameters(self) -> Dict[str, float]:
        """
        Get parameters for SUMO pedestrian simulation based on current weather.
        
        Returns:
            Dict[str, float]: SUMO parameters for pedestrian simulation
        """
        # Default SUMO pedestrian parameters
        walking_speed = self.get_walking_speed()
        
        params = {
            'speed': walking_speed,  # Adjusted walking speed
            'mingap': 0.25,  # Minimum gap between pedestrians (m)
            'sigma': 0.75,  # Speed deviation
            'random_stop_threshold': 0.0  # Probability to randomly stop
        }
        
        # Adjust parameters based on weather
        if self.current_rain_category != 'normal':
            # Increase minimum gap in rain (people give each other more space with umbrellas)
            params['mingap'] = 0.25 + (self.current_rain_intensity * 0.3)  # Up to 0.55m
            
            # Increase sigma (more variation in speeds) during rain
            params['sigma'] = 0.75 + (self.current_rain_intensity * 0.25)  # Up to 1.0
            
            # Probability to stop increases with rain (seeking temporary shelter)
            params['random_stop_threshold'] = self.current_rain_intensity * 0.1  # Up to 0.1
            
        return params
        
    def simulate_pedestrian_demand(self, base_demand: float, 
                                  time_of_day: str) -> float:
        """
        Simulate adjusted pedestrian demand based on weather and time.
        
        Args:
            base_demand (float): Base pedestrian demand (pedestrians/hour)
            time_of_day (str): Time of day (morning, afternoon, evening, night)
            
        Returns:
            float: Adjusted pedestrian demand
        """
        # Apply time of day factors if configured
        time_factor = 1.0
        if 'time_demand_factors' in self.config:
            time_factor = self.config['time_demand_factors'].get(time_of_day, 1.0)
            
        # Apply weather adjustment
        weather_factor = self.get_pedestrian_flow_adjustment()
        
        # Calculate final adjusted demand
        adjusted_demand = base_demand * time_factor * weather_factor
        
        return adjusted_demand