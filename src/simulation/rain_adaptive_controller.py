# rain_adaptive_controller.py
import os
import sys
import traci
import random
import pandas as pd
import numpy as np
from src.weather.weather_api import WeatherAPI

# Add SUMO python tools to path
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare environment variable 'SUMO_HOME'")

class RainAdaptiveController:
    def __init__(self, config_file, weather_api_key, city):
        self.config_file = config_file
        self.weather_api = WeatherAPI(weather_api_key, city)
        self.current_rain_category = "no_rain"
        self.stats = {
            'vehicle_wait_times': [],
            'pedestrian_wait_times': [],
            'traffic_flow': [],
            'rain_intensity': []
        }
        
        # Rain adaptation parameters
        self.rain_speed_adjustments = {
            "no_rain": 1.0,      # No adjustment
            "light_rain": 0.9,    # 10% speed reduction
            "moderate_rain": 0.8, # 20% speed reduction
            "heavy_rain": 0.7     # 30% speed reduction
        }
        
        # Pedestrian crossing time adjustments (multipliers)
        self.rain_pedestrian_adjustments = {
            "no_rain": 1.0,       # No adjustment
            "light_rain": 1.2,     # 20% more crossing time
            "moderate_rain": 1.5,  # 50% more crossing time
            "heavy_rain": 1.8      # 80% more crossing time
        }
    
    def start_simulation(self, use_gui=True):
        """Start the SUMO simulation with TraCI"""
        if use_gui:
            sumoBinary = "sumo-gui"
        else:
            sumoBinary = "sumo"
        
        sumo_cmd = [sumoBinary, "-c", self.config_file]
        traci.start(sumo_cmd)
    
    def update_weather_conditions(self, step):
        """Update weather conditions (every 5 minutes in simulation time)"""
        if step % 300 == 0:  # Update every 300 seconds (5 minutes)
            # In a real implementation, this would call the weather API
            # For simulation, we'll either use the API or simulate weather changes
            self.current_rain_category = self.weather_api.get_rain_category()
            print(f"Step {step}: Weather updated to {self.current_rain_category}")
    
    def adjust_vehicle_speeds(self):
        """Adjust vehicle speeds based on rain intensity"""
        speed_factor = self.rain_speed_adjustments[self.current_rain_category]
        
        # Get all vehicles currently in the simulation
        vehicle_ids = traci.vehicle.getIDList()
        
        for vehicle_id in vehicle_ids:
            # Get the vehicle type maximum speed
            veh_type = traci.vehicle.getTypeID(vehicle_id)
            max_speed = traci.vehicletype.getMaxSpeed(veh_type)
            
            # Apply rain-based speed adjustment
            adjusted_speed = max_speed * speed_factor
            traci.vehicle.setMaxSpeed(vehicle_id, adjusted_speed)
    
    def adjust_traffic_lights(self):
        """Adjust traffic light timings for pedestrian priority"""
        # Get all traffic lights
        tl_ids = traci.trafficlight.getIDList()
        
        for tl_id in tl_ids:
            # Get the current program
            current_program = traci.trafficlight.getProgram(tl_id)
            phases = traci.trafficlight.getAllProgramLogics(tl_id)[0].phases
            
            # Find pedestrian phases (simplified approach - assumes phases with 'g' for pedestrians)
            for i, phase in enumerate(phases):
                phase_state = phase.state
                
                # If this is a pedestrian phase (contains 'g' for pedestrian signals)
                if 'g' in phase_state.lower():
                    # Calculate new duration for pedestrian phases
                    adjustment_factor = self.rain_pedestrian_adjustments[self.current_rain_category]
                    new_duration = int(phase.duration * adjustment_factor)
                    
                    # Set new duration
                    traci.trafficlight.setPhaseDuration(tl_id, new_duration)
    
    def collect_statistics(self):
        """Collect performance statistics"""
        # Vehicle stats
        vehicles = traci.vehicle.getIDList()
        if vehicles:
            avg_wait_time = np.mean([traci.vehicle.getAccumulatedWaitingTime(v) for v in vehicles])
            self.stats['vehicle_wait_times'].append(avg_wait_time)
        
        # Pedestrian stats (if available in this SUMO version)
        pedestrians = traci.person.getIDList() if hasattr(traci, 'person') else []
        if pedestrians:
            # In newer SUMO versions, you can get waiting time for pedestrians
            # This is simplified and may need adaptation based on your SUMO version
            ped_waiting = []
            for ped in pedestrians:
                if traci.person.getWaitingTime(ped) > 0:
                    ped_waiting.append(traci.person.getWaitingTime(ped))
            
            if ped_waiting:
                avg_ped_wait = np.mean(ped_waiting)
                self.stats['pedestrian_wait_times'].append(avg_ped_wait)
        
        # Traffic flow (vehicles per hour)
        arrived = traci.simulation.getArrivedNumber()
        self.stats['traffic_flow'].append(arrived)
        
        # Current rain intensity
        self.stats['rain_intensity'].append(self.current_rain_category)
    
    def save_statistics(self, output_file):
        """Save collected statistics to CSV"""
        # Convert to DataFrame
        stats_df = pd.DataFrame({
            'vehicle_wait_times': self.stats['vehicle_wait_times'],
            'pedestrian_wait_times': self.stats['pedestrian_wait_times'] if self.stats['pedestrian_wait_times'] else [0] * len(self.stats['vehicle_wait_times']),
            'traffic_flow': self.stats['traffic_flow'],
            'rain_intensity': self.stats['rain_intensity']
        })
        
        # Save to CSV
        stats_df.to_csv(output_file, index=False)
        print(f"Statistics saved to {output_file}")
    
    def run_simulation(self, steps=3600):
        """Run the simulation for the specified number of steps"""
        self.start_simulation()
        
        try:
            for step in range(steps):
                traci.simulationStep()
                
                # Update weather every 5 minutes (simulation time)
                self.update_weather_conditions(step)
                
                # Apply rain-adaptive controls
                self.adjust_vehicle_speeds()
                self.adjust_traffic_lights()
                
                # Collect statistics
                self.collect_statistics()
                
                # Print progress
                if step % 100 == 0:
                    print(f"Simulation step: {step}/{steps}")
            
            # Save statistics
            self.save_statistics("simulation_results.csv")
        
        finally:
            traci.close()