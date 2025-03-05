#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Traffic Light Controller Module for Rain-Adaptive Traffic Simulation

This module provides functionality for managing traffic signal timing and phases
with adaptive adjustments based on weather conditions and traffic density.
"""

import os
import sys
import numpy as np
import traci
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

# Ensure SUMO_HOME environment variable is set for TraCI
if 'SUMO_HOME' in os.environ:
    sys.path.append(os.path.join(os.environ['SUMO_HOME'], 'tools'))
else:
    sys.exit("Please declare the environment variable 'SUMO_HOME'")


class TrafficLightController:
    """
    Controller for managing traffic lights in the SUMO simulation with
    adaptive capabilities for different weather conditions.
    """

    def __init__(self, config: dict):
        """
        Initialize the traffic light controller.

        Args:
            config (dict): Configuration dictionary containing controller parameters
        """
        self.config = config
        self.tls_ids = []  # Will be populated once simulation starts
        self.phase_durations = {}  # Original phase durations
        self.current_programs = {}  # Track current program for each TLS
        self.rain_adjustment_factors = self.config.get('rain_adjustment_factors', {
            'light': 1.1,    # 10% increase in green time for light rain
            'moderate': 1.2, # 20% increase for moderate rain
            'heavy': 1.3,    # 30% increase for heavy rain
            'extreme': 1.5   # 50% increase for extreme rain
        })
        self.min_green_time = self.config.get('min_green_time', 10)  # Minimum green phase time in seconds
        self.max_green_time = self.config.get('max_green_time', 120)  # Maximum green phase time in seconds
        self.congestion_thresholds = self.config.get('congestion_thresholds', {
            'low': 0.3,      # Low traffic density threshold
            'medium': 0.5,   # Medium traffic density threshold
            'high': 0.7      # High traffic density threshold
        })
        self.traffic_data = defaultdict(dict)  # Store traffic data for each intersection
        self.weather_condition = "normal"  # Default weather condition

    def initialize(self):
        """Initialize traffic light controller after simulation has started."""
        self.tls_ids = traci.trafficlight.getIDList()
        
        # Store original program data for all traffic lights
        for tls_id in self.tls_ids:
            self.current_programs[tls_id] = traci.trafficlight.getProgram(tls_id)
            
            # Get all phases for the current program
            phases = traci.trafficlight.getAllProgramLogics(tls_id)[0].getPhases()
            self.phase_durations[tls_id] = [phase.duration for phase in phases]
            
            # Initialize traffic data for this intersection
            self.traffic_data[tls_id] = {
                'queue_lengths': [],
                'wait_times': [],
                'vehicle_counts': 0
            }
            
        print(f"Initialized {len(self.tls_ids)} traffic light controllers")

    def update_weather_condition(self, condition: str):
        """
        Update the current weather condition.
        
        Args:
            condition (str): Current weather condition ('normal', 'light', 'moderate', 'heavy', 'extreme')
        """
        self.weather_condition = condition.lower()
        print(f"Weather condition updated to: {self.weather_condition}")

    def get_adjustment_factor(self) -> float:
        """
        Get the appropriate adjustment factor based on current weather.
        
        Returns:
            float: Adjustment factor for phase durations
        """
        if self.weather_condition == "normal":
            return 1.0
        return self.rain_adjustment_factors.get(self.weather_condition, 1.0)

    def collect_traffic_data(self):
        """Collect traffic data from detectors at each intersection."""
        for tls_id in self.tls_ids:
            # Get incoming lanes for this traffic light
            controlled_links = traci.trafficlight.getControlledLinks(tls_id)
            incoming_lanes = set()
            
            for links in controlled_links:
                for link in links:
                    if link:
                        incoming_lanes.add(link[0])  # Add incoming lane
            
            # Collect metrics for each lane
            queue_length = 0
            waiting_time = 0
            vehicle_count = 0
            
            for lane in incoming_lanes:
                # Get vehicle IDs on this lane
                vehicle_ids = traci.lane.getLastStepVehicleIDs(lane)
                vehicle_count += len(vehicle_ids)
                
                # Calculate queue length and waiting time
                for veh_id in vehicle_ids:
                    if traci.vehicle.getSpeed(veh_id) < 0.1:  # If vehicle is practically stopped
                        queue_length += 1
                        waiting_time += traci.vehicle.getAccumulatedWaitingTime(veh_id)
            
            # Store the collected data
            self.traffic_data[tls_id]['queue_lengths'].append(queue_length)
            self.traffic_data[tls_id]['wait_times'].append(waiting_time)
            self.traffic_data[tls_id]['vehicle_counts'] = vehicle_count

    def calculate_congestion_level(self, tls_id: str) -> float:
        """
        Calculate congestion level for a specific traffic light.
        
        Args:
            tls_id (str): Traffic light ID
            
        Returns:
            float: Congestion level between 0 and 1
        """
        if not self.traffic_data[tls_id]['queue_lengths']:
            return 0.0
            
        # Use recent queue data (last 5 cycles)
        recent_queue_lengths = self.traffic_data[tls_id]['queue_lengths'][-5:]
        avg_queue = sum(recent_queue_lengths) / len(recent_queue_lengths)
        
        # Get incoming lanes count to normalize
        controlled_links = traci.trafficlight.getControlledLinks(tls_id)
        incoming_lanes = set()
        for links in controlled_links:
            for link in links:
                if link:
                    incoming_lanes.add(link[0])
        
        # Normalize by number of incoming lanes (rough estimate of capacity)
        max_possible_queue = len(incoming_lanes) * 10  # Assumption: 10 vehicles per lane is "full"
        congestion_level = min(avg_queue / max_possible_queue, 1.0)
        
        return congestion_level

    def optimize_single_traffic_light(self, tls_id: str):
        """
        Optimize a single traffic light based on current conditions.
        
        Args:
            tls_id (str): Traffic light ID to optimize
        """
        # Get current program and phase
        current_program = traci.trafficlight.getProgram(tls_id)
        current_phase = traci.trafficlight.getPhase(tls_id)
        
        # Don't adjust if we're not in a green phase (typically even-numbered phases)
        if current_phase % 2 != 0:
            return
            
        # Get congestion level
        congestion_level = self.calculate_congestion_level(tls_id)
        
        # Get weather adjustment factor
        weather_factor = self.get_adjustment_factor()
        
        # Calculate congestion-based adjustment
        congestion_factor = 1.0
        if congestion_level > self.congestion_thresholds['high']:
            congestion_factor = 1.3  # Extend green time by 30% for high congestion
        elif congestion_level > self.congestion_thresholds['medium']:
            congestion_factor = 1.2  # Extend green time by 20% for medium congestion
        elif congestion_level > self.congestion_thresholds['low']:
            congestion_factor = 1.1  # Extend green time by 10% for low congestion
            
        # Combined adjustment factor (weather and congestion)
        combined_factor = weather_factor * congestion_factor
        
        # Get original duration and calculate new duration
        original_duration = self.phase_durations[tls_id][current_phase]
        new_duration = max(min(original_duration * combined_factor, self.max_green_time), self.min_green_time)
        
        # Set the new phase duration
        traci.trafficlight.setPhaseDuration(tls_id, new_duration)
        
        if combined_factor != 1.0:
            print(f"TL {tls_id} Phase {current_phase}: adjusted from {original_duration:.1f}s to {new_duration:.1f}s " +
                  f"(Weather: {weather_factor:.2f}, Congestion: {congestion_factor:.2f}, Level: {congestion_level:.2f})")

    def step(self):
        """Execute a single step for all traffic lights."""
        # Collect traffic data
        self.collect_traffic_data()
        
        # Optimize each traffic light
        for tls_id in self.tls_ids:
            self.optimize_single_traffic_light(tls_id)
            
    def create_custom_program(self, tls_id: str, rain_intensity: float) -> str:
        """
        Create a custom TLS program based on rain intensity.
        
        Args:
            tls_id (str): Traffic light ID
            rain_intensity (float): Rain intensity (0.0-1.0)
            
        Returns:
            str: New program ID
        """
        # Get current logic
        logic = traci.trafficlight.getAllProgramLogics(tls_id)[0]
        
        # Create new program ID
        new_program_id = f"{logic.programID}_rain_{int(rain_intensity*100)}"
        
        # Copy the logic and adjust phase durations
        new_logic = traci.trafficlight.Logic(
            programID=new_program_id,
            type=logic.type,
            currentPhaseIndex=0,
            phases=[]
        )
        
        # Adjustment based on rain intensity
        factor = 1.0 + (rain_intensity * 0.5)  # Up to 50% increase for max rain
        
        # Create adjusted phases
        for i, phase in enumerate(logic.phases):
            # Only extend green phases (typically even-numbered phases)
            if i % 2 == 0:  # Green phase
                new_duration = max(min(phase.duration * factor, self.max_green_time), self.min_green_time)
            else:  # Yellow/red phase - keep the same
                new_duration = phase.duration
                
            new_phase = traci.trafficlight.Phase(
                duration=new_duration,
                state=phase.state,
                minDur=phase.minDur,
                maxDur=phase.maxDur
            )
            new_logic.phases.append(new_phase)
            
        # Add the new logic
        traci.trafficlight.setProgramLogic(tls_id, new_logic)
        
        return new_program_id
        
    def apply_rainy_programs(self, rain_intensity: float):
        """
        Apply rain-optimized programs to all traffic lights.
        
        Args:
            rain_intensity (float): Rain intensity (0.0-1.0)
        """
        for tls_id in self.tls_ids:
            new_program_id = self.create_custom_program(tls_id, rain_intensity)
            traci.trafficlight.setProgram(tls_id, new_program_id)
            print(f"Set traffic light {tls_id} to rain-optimized program {new_program_id}")
            
    def restore_default_programs(self):
        """Restore all traffic lights to their default programs."""
        for tls_id in self.tls_ids:
            default_program = self.current_programs[tls_id]
            traci.trafficlight.setProgram(tls_id, default_program)
            print(f"Restored traffic light {tls_id} to default program {default_program}")
            
    def get_statistics(self) -> Dict[str, Dict]:
        """
        Get statistics for all controlled traffic lights.
        
        Returns:
            Dict: Dictionary with traffic light statistics
        """
        stats = {}
        for tls_id in self.tls_ids:
            if not self.traffic_data[tls_id]['wait_times']:
                continue
                
            wait_times = self.traffic_data[tls_id]['wait_times']
            queue_lengths = self.traffic_data[tls_id]['queue_lengths']
            
            stats[tls_id] = {
                'avg_wait_time': sum(wait_times) / len(wait_times) if wait_times else 0,
                'max_wait_time': max(wait_times) if wait_times else 0,
                'avg_queue_length': sum(queue_lengths) / len(queue_lengths) if queue_lengths else 0,
                'max_queue_length': max(queue_lengths) if queue_lengths else 0,
                'vehicle_count': self.traffic_data[tls_id]['vehicle_counts']
            }
            
        return stats