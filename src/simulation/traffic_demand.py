#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Traffic demand generation module for rain-adaptive traffic simulation.
Handles the creation of vehicle and pedestrian demands based on time of day,
weather conditions, and network characteristics.
"""

import os
import logging
import random
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
from pathlib import Path
import subprocess
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger(__name__)

class TrafficDemandGenerator:
    """
    Generates traffic demand (vehicles and pedestrians) for SUMO simulations.
    Considers rain conditions when generating demand, with configurable
    parameters for how weather affects travel patterns.
    """
    
    def __init__(self, config, network_file):
        """
        Initialize the traffic demand generator.
        
        Args:
            config: Dict containing configuration parameters
            network_file: Path to the SUMO network file
        """
        self.config = config
        self.network_file = Path(network_file)
        
        # Configure paths
        self.output_dir = Path(config.get('output_dir', 'data/output'))
        self.input_dir = Path(config.get('input_dir', 'data/input'))
        
        # Ensure directories exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.input_dir.mkdir(parents=True, exist_ok=True)
        
        # Traffic demand parameters
        self.vehicle_types = config.get('vehicle_types', {
            'passenger': 0.7,
            'taxi': 0.1,
            'bus': 0.05,
            'truck': 0.15
        })
        
        # Rain impact parameters
        self.rain_impact = config.get('rain_impact', {
            # Percentage reduction in traffic based on rain intensity (mm/h)
            'traffic_volume_factor': lambda rain: max(0.6, 1.0 - 0.1 * min(4, rain)),
            # Percentage increase in trips by car (vs walking/cycling) in rain
            'mode_shift_factor': lambda rain: min(1.3, 1.0 + 0.08 * min(4, rain)),
            # Percentage reduction in pedestrian volume based on rain intensity
            'pedestrian_volume_factor': lambda rain: max(0.3, 1.0 - 0.18 * min(4, rain))
        })
        
        # Cache for network data
        self._edge_data = None
        self._junction_data = None
        
    def _load_network_data(self):
        """
        Load and cache edge and junction data from the network file.
        """
        if self._edge_data is not None and self._junction_data is not None:
            return
            
        logger.info(f"Loading network data from {self.network_file}")
        
        tree = ET.parse(self.network_file)
        root = tree.getroot()
        
        # Extract edge data
        edges = []
        for edge in root.findall(".//edge"):
            if edge.get("function") != "internal":
                edges.append({
                    'id': edge.get('id'),
                    'from': edge.get('from'),
                    'to': edge.get('to'),
                    'priority': int(edge.get('priority', 0)),
                    'length': float(edge.get('length', 0)),
                    'speed': float(edge.get('speed', 13.89))
                })
        
        self._edge_data = pd.DataFrame(edges)
        
        # Extract junction data
        junctions = []
        for junction in root.findall(".//junction"):
            junctions.append({
                'id': junction.get('id'),
                'type': junction.get('type'),
                'x': float(junction.get('x', 0)),
                'y': float(junction.get('y', 0)),
                'incoming': len(junction.get('incLanes', '').split(' ')) if junction.get('incLanes') else 0,
                'shape': junction.get('shape', '')
            })
            
        self._junction_data = pd.DataFrame(junctions)
        
        logger.info(f"Loaded {len(self._edge_data)} edges and {len(self._junction_data)} junctions")
    
    def generate_random_trips(self, duration=3600, start_time=0, end_time=None, 
                              min_distance=300, max_distance=None, 
                              fringe_factor=10, rain_intensity=0):
        """
        Generate random trips for the simulation.
        
        Args:
            duration: Simulation duration in seconds
            start_time: Start time in seconds
            end_time: End time in seconds (if None, calculated from duration)
            min_distance: Minimum trip distance in meters
            max_distance: Maximum trip distance in meters
            fringe_factor: Bias for trips starting/ending at the fringe
            rain_intensity: Rain intensity in mm/h
            
        Returns:
            Path to the generated trip file
        """
        # Load network data
        self._load_network_data()
        
        # Set default end time if not provided
        if end_time is None:
            end_time = start_time + duration
            
        # Apply rain impact on traffic volume
        traffic_factor = self.rain_impact['traffic_volume_factor'](rain_intensity)
        mode_shift_factor = self.rain_impact['mode_shift_factor'](rain_intensity)
        
        # More cars in rain (mode shift from walking/cycling), but fewer trips overall
        # The net effect is adjusted by these factors
        vehicle_count = int(self.config.get('vehicles_per_hour', 1000) * 
                            duration / 3600 * traffic_factor * mode_shift_factor)
        
        logger.info(f"Generating random trips for {vehicle_count} vehicles (rain intensity: {rain_intensity} mm/h)")
        
        # Prepare randomTrips.py parameters
        trip_file = self.output_dir / f"{self.network_file.stem}_trips_{rain_intensity:.1f}mm.xml"
        route_file = self.output_dir / f"{self.network_file.stem}_routes_{rain_intensity:.1f}mm.xml"
        
        # Calculate vehicle count by type
        vehicle_type_params = []
        for vtype, proportion in self.vehicle_types.items():
            type_count = int(vehicle_count * proportion)
            vehicle_type_params.extend(["--vehicle-class", vtype, 
                                       "--vclass-output-count", str(type_count)])
        
        # Build command for randomTrips.py
        cmd = [
            "python", f"{os.environ.get('SUMO_HOME', '')}/tools/randomTrips.py",
            "-n", str(self.network_file),
            "-o", str(trip_file),
            "-r", str(route_file),
            "-e", str(end_time - start_time),
            "-p", str(max(0.1, duration / max(1, vehicle_count))),
            "--fringe-factor", str(fringe_factor),
            "--allow-fringe",
            "--min-distance", str(min_distance)
        ]
        
        # Add vehicle type parameters
        cmd.extend(vehicle_type_params)
        
        # Add max distance if provided
        if max_distance:
            cmd.extend(["--max-distance", str(max_distance)])
            
        # Run randomTrips.py
        logger.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Trip generation failed: {result.stderr}")
            raise RuntimeError(f"Failed to generate trips: {result.stderr}")
        
        logger.info(f"Trips generated successfully: {trip_file}")
        logger.info(f"Routes generated successfully: {route_file}")
        
        # Modify vehicle types for rain conditions
        self._customize_vehicle_parameters(route_file, rain_intensity)
        
        return route_file
    
    def generate_time_based_demand(self, start_time=0, duration=86400, time_slots=24, 
                                  rain_data=None, output_file=None):
        """
        Generate time-varying demand based on time of day and rain conditions.
        
        Args:
            start_time: Simulation start time in seconds
            duration: Simulation duration in seconds
            time_slots: Number of time slots to divide the day
            rain_data: DataFrame with timestamp and rain_intensity
            output_file: Output route file path
            
        Returns:
            Path to the generated time-based route file
        """
        # Load network data
        self._load_network_data()
        
        # Create output file if not provided
        if output_file is None:
            output_file = self.output_dir / f"{self.network_file.stem}_time_demand.rou.xml"
            
        # Create base time distribution (daily pattern)
        seconds_per_slot = duration / time_slots
        
        # Define time factors (hourly traffic distribution, 0-23 hour mapping)
        hour_factors = self.config.get('hour_factors', [
            0.2, 0.1, 0.1, 0.1, 0.2, 0.4, 0.7, 1.0,  # 0-7
            1.0, 0.9, 0.8, 0.8, 0.9, 0.9, 0.9, 0.9,  # 8-15
            1.0, 1.0, 0.9, 0.8, 0.7, 0.5, 0.4, 0.3   # 16-23
        ])
        
        # Expand hour factors to match time slots if needed
        time_factors = []
        for i in range(time_slots):
            hour_index = int((i * 24) / time_slots)
            time_factors.append(hour_factors[hour_index])
        
        # Base vehicle count
        base_vehicles_per_hour = self.config.get('vehicles_per_hour', 1000)
        
        # Generate trips for each time slot
        trips_by_slot = []
        route_files = []
        
        for slot in range(time_slots):
            slot_start = start_time + slot * seconds_per_slot
            slot_end = slot_start + seconds_per_slot
            
            # Get rain intensity for this time slot
            rain_intensity = 0
            if rain_data is not None:
                slot_time = datetime.fromtimestamp(slot_start)
                if 'timestamp' in rain_data.columns:
                    # Find the closest timestamp
                    closest = rain_data.iloc[(rain_data['timestamp'] - slot_time).abs().argsort()[0]]
                    rain_intensity = closest['rain_intensity']
            
            # Apply time and rain factors
            time_factor = time_factors[slot]
            traffic_factor = self.rain_impact['traffic_volume_factor'](rain_intensity)
            mode_shift_factor = self.rain_impact['mode_shift_factor'](rain_intensity)
            
            # Calculate vehicle count for this slot
            slot_vehicles = int(base_vehicles_per_hour * 
                               (seconds_per_slot / 3600) * 
                               time_factor * traffic_factor * mode_shift_factor)
            
            if slot_vehicles > 0:
                # Generate trips for this time slot
                logger.info(f"Generating trips for slot {slot}: {slot_start}-{slot_end} "
                          f"(rain: {rain_intensity:.1f} mm/h, vehicles: {slot_vehicles})")
                
                slot_file = self.generate_random_trips(
                    duration=int(seconds_per_slot),
                    start_time=int(slot_start),
                    end_time=int(slot_end),
                    rain_intensity=rain_intensity
                )
                
                route_files.append(slot_file)
        
        # Combine all route files
        self._combine_route_files(route_files, output_file)
        
        logger.info(f"Time-based demand generation complete: {output_file}")
        return output_file
    
    def generate_od_matrix_demand(self, od_file, start_time=0, duration=3600, 
                                 rain_intensity=0, output_file=None):
        """
        Generate demand based on an origin-destination matrix.
        
        Args:
            od_file: Path to OD matrix file
            start_time: Simulation start time in seconds
            duration: Simulation duration in seconds
            rain_intensity: Rain intensity in mm/h
            output_file: Output route file path
            
        Returns:
            Path to the generated route file
        """
        # Load network data
        self._load_network_data()
        
        # Create output file if not provided
        if output_file is None:
            output_file = self.output_dir / f"{self.network_file.stem}_od_demand.rou.xml"
            
        # Apply rain impact on traffic volume
        traffic_factor = self.rain_impact['traffic_volume_factor'](rain_intensity)
        mode_shift_factor = self.rain_impact['mode_shift_factor'](rain_intensity)
        
        # Build command for OD2TRIPS
        trip_file = self.output_dir / f"{self.network_file.stem}_od_trips.xml"
        
        cmd = [
            "od2trips",
            "-n", str(self.network_file),
            "-d", str(od_file),
            "-o", str(trip_file),
            "--scale", str(traffic_factor * mode_shift_factor),
            "--begin", str(start_time),
            "--end", str(start_time + duration)
        ]
        
        # Run OD2TRIPS
        logger.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"OD demand generation failed: {result.stderr}")
            raise RuntimeError(f"Failed to generate OD demand: {result.stderr}")
        
        # Generate routes from trips
        route_file = self.output_dir / f"{self.network_file.stem}_od_routes.xml"
        
        cmd = [
            "duarouter",
            "-n", str(self.network_file),
            "-t", str(trip_file),
            "-o", str(route_file),
            "--ignore-errors",
            "--begin", str(start_time),
            "--end", str(start_time + duration)
        ]
        
        # Run DUAROUTER
        logger.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.warning(f"Route generation warning: {result.stderr}")
        
        # Modify vehicle types for rain conditions
        self._customize_vehicle_parameters(route_file, rain_intensity)
        
        # Copy to final output file
        if route_file != output_file:
            import shutil
            shutil.copy(route_file, output_file)
        
        logger.info(f"OD-based demand generation complete: {output_file}")
        return output_file
    
    def generate_pedestrian_demand(self, count=None, start_time=0, duration=3600, 
                                  rain_intensity=0, output_file=None):
        """
        Generate pedestrian demand for the simulation.
        
        Args:
            count: Number of pedestrians (if None, calculated based on config)
            start_time: Simulation start time in seconds
            duration: Simulation duration in seconds
            rain_intensity: Rain intensity in mm/h
            output_file: Output route file path
            
        Returns:
            Path to the generated pedestrian demand file
        """
        # Load network data
        self._load_network_data()
        
        # Create output file if not provided
        if output_file is None:
            output_file = self.output_dir / f"{self.network_file.stem}_pedestrians.xml"
            
        # Apply rain impact on pedestrian volume
        pedestrian_factor = self.rain_impact['pedestrian_volume_factor'](rain_intensity)
        
        # Calculate pedestrian count if not provided
        if count is None:
            base_count = self.config.get('pedestrians_per_hour', 500)
            count = int(base_count * duration / 3600 * pedestrian_factor)
            
        logger.info(f"Generating pedestrian demand for {count} pedestrians "
                   f"(rain intensity: {rain_intensity:.1f} mm/h)")
        
        # Create pedestrian demand XML
        root = ET.Element("routes")
        
        # Define pedestrian type
        ped_type = ET.SubElement(root, "vType")
        ped_type.set("id", "pedestrian")
        ped_type.set("vClass", "pedestrian")
        ped_type.set("width", "0.8")
        ped_type.set("length", "0.5")
        ped_type.set("minGap", "0.5")
        ped_type.set("maxSpeed", "1.5")
        ped_type.set("guiShape", "pedestrian")
        ped_type.set("color", "0,1,0")
        
        # Get suitable junctions (pedestrian crossings or traffic lights)
        suitable_junctions = self._junction_data[
            (self._junction_data['type'].isin(['priority', 'traffic_light']))
        ]
        
        if len(suitable_junctions) < 2:
            logger.warning("Not enough suitable junctions for pedestrian demand")
            suitable_junctions = self._junction_data  # Use all junctions
            
        junction_ids = suitable_junctions['id'].tolist()
        
        # Generate pedestrian trips
        generated = 0
        min_trip_duration = 60  # Minimum trip duration in seconds
        
        # Distribution of departure times
        departure_times = np.random.uniform(start_time, start_time + duration, count)
        departure_times.sort()
        
        for i, depart in enumerate(departure_times):
            # Select random origin and destination junctions
            from_junction = random.choice(junction_ids)
            to_junction = random.choice([j for j in junction_ids if j != from_junction])
            
            # Find connecting edges
            from_edges = self._edge_data[self._edge_data['from'] == from_junction]['id'].tolist()
            to_edges = self._edge_data[self._edge_data['to'] == to_junction]['id'].tolist()
            
            if not from_edges or not to_edges:
                continue
                
            from_edge = random.choice(from_edges)
            to_edge = random.choice(to_edges)
            
            # Create person element
            person = ET.SubElement(root, "person")
            person.set("id", f"ped_{i}")
            person.set("type", "pedestrian")
            person.set("depart", str(int(depart)))
            
            # Create walk element
            walk = ET.SubElement(person, "walk")
            walk.set("from", from_edge)
            walk.set("to", to_edge)
            
            # Adjust walking speed in rain
            if rain_intensity > 0:
                # Walking slightly faster in rain (trying to get out of the rain)
                walk_speed = 1.5 * (1.0 + 0.1 * min(rain_intensity, 3))
                walk.set("speed", str(walk_speed))
            
            generated += 1
        
        logger.info(f"Generated {generated} pedestrian trips")
        
        # Write to file
        tree = ET.ElementTree(root)
        tree.write(output_file)
        
        return output_file
    
    def _customize_vehicle_parameters(self, route_file, rain_intensity):
        """
        Modify vehicle parameters for rain conditions.
        
        Args:
            route_file: Path to the route file to modify
            rain_intensity: Rain intensity in mm/h
            
        Returns:
            Path to the modified route file
        """
        if rain_intensity <= 0:
            return route_file
            
        logger.info(f"Customizing vehicle parameters for rain intensity {rain_intensity:.1f} mm/h")
        
        try:
            tree = ET.parse(route_file)
            root = tree.getroot()
            
            # Speed factor reduction based on rain intensity
            # More intense rain = greater speed reduction
            # Using a logarithmic relationship to model diminishing impact
            speed_factor = max(0.6, 1.0 - 0.08 * np.log(1 + rain_intensity))
            
            # Modify vehicle types
            for vtype in root.findall(".//vType"):
                # Original parameters (or defaults if not specified)
                orig_speed_factor = float(vtype.get("speedFactor", "1.0"))
                orig_speed_dev = float(vtype.get("speedDev", "0.1"))
                orig_min_gap = float(vtype.get("minGap", "2.5"))
                orig_accel = float(vtype.get("accel", "2.9"))
                orig_decel = float(vtype.get("decel", "4.5"))
                
                # Modify for rain conditions
                rain_speed_factor = orig_speed_factor * speed_factor
                rain_speed_dev = orig_speed_dev * 0.8  # Less speed variation in rain
                rain_min_gap = orig_min_gap * 1.3  # Larger gaps in rain
                rain_accel = orig_accel * 0.9  # Slower acceleration in rain
                rain_decel = orig_decel * 0.9  # More cautious braking in rain
                
                # Update vehicle type parameters
                vtype.set("speedFactor", str(rain_speed_factor))
                vtype.set("speedDev", str(rain_speed_dev))
                vtype.set("minGap", str(rain_min_gap))
                vtype.set("accel", str(rain_accel))
                vtype.set("decel", str(rain_decel))
                
                # Add visualization elements for rain
                vtype.set("imgFile", "rainy_vehicle.png" if hasattr(vtype, "imgFile") else None)
                vtype.set("carFollowModel", "IDM")  # Intelligent Driver Model for more realistic following
            
            # Save modified route file
            tree.write(route_file)
            logger.info(f"Vehicle parameters customized for rain in {route_file}")
            
        except Exception as e:
            logger.error(f"Error customizing vehicle parameters: {e}")
            
        return route_file
    
    def _combine_route_files(self, route_files, output_file):
        """
        Combine multiple route files into a single file.
        
        Args:
            route_files: List of route file paths
            output_file: Output combined file path
            
        Returns:
            Path to the combined route file
        """
        if not route_files:
            logger.warning("No route files to combine")
            return None
            
        logger.info(f"Combining {len(route_files)} route files")
        
        # Create root element
        root = ET.Element("routes")
        
        # Collect all vehicle types
        vtypes = {}
        
        # Process each route file
        vehicle_count = 0
        for file_path in route_files:
            tree = ET.parse(file_path)
            file_root = tree.getroot()
            
            # Extract vehicle types
            for vtype in file_root.findall(".//vType"):
                vtype_id = vtype.get("id")
                if vtype_id not in vtypes:
                    vtypes[vtype_id] = vtype
            
            # Extract vehicles and routes
            for vehicle in file_root.findall(".//vehicle"):
                root.append(vehicle)
                vehicle_count += 1
                
            # Extract routes
            for route in file_root.findall(".//route"):
                # Only add standalone routes not inside vehicles
                if route.getparent().tag != "vehicle":
                    root.append(route)
        
        # Add vehicle types to the beginning
        for vtype_id, vtype in vtypes.items():
            root.insert(0, vtype)
            
        # Write combined file
        tree = ET.ElementTree(root)
        tree.write(output_file)
        
        logger.info(f"Combined {len(route_files)} files with {vehicle_count} vehicles to {output_file}")
        return output_file
    
    def create_scenario_demand(self, scenario_config, rain_data=None):
        """
        Create a complete scenario demand based on configuration.
        
        Args:
            scenario_config: Dict with scenario configuration
            rain_data: DataFrame with timestamp and rain_intensity
            
        Returns:
            Dict with paths to generated demand files
        """
        # Load network data
        self._load_network_data()
        
        # Get scenario parameters
        start_time = scenario_config.get('start_time', 0)
        duration = scenario_config.get('duration', 3600)
        output_prefix = scenario_config.get('output_prefix', 'scenario')
        
        # Get constant rain intensity if provided
        rain_intensity = scenario_config.get('rain_intensity', 0)
        
        output_files = {}
        
        # Generate vehicle demand
        if scenario_config.get('demand_type') == 'time_based':
            # Time-based demand
            route_file = self.generate_time_based_demand(
                start_time=start_time,
                duration=duration,
                time_slots=scenario_config.get('time_slots', 24),
                rain_data=rain_data,
                output_file=self.output_dir / f"{output_prefix}_vehicles.xml"
            )
            output_files['vehicle_demand'] = route_file
            
        elif scenario_config.get('demand_type') == 'od_matrix':
            # OD matrix demand
            od_file = scenario_config.get('od_file')
            if not od_file:
                logger.error("OD matrix file not specified")
                raise ValueError("OD matrix file not specified in scenario config")
                
            route_file = self.generate_od_matrix_demand(
                od_file=od_file,
                start_time=start_time,
                duration=duration,
                rain_intensity=rain_intensity,
                output_file=self.output_dir / f"{output_prefix}_vehicles.xml"
            )
            output_files['vehicle_demand'] = route_file
            
        else:
            # Random trip generation (default)
            route_file = self.generate_random_trips(
                duration=duration,
                start_time=start_time,
                rain_intensity=rain_intensity,
                output_file=self.output_dir / f"{output_prefix}_vehicles.xml"
            )
            output_files['vehicle_demand'] = route_file
        
        # Generate pedestrian demand if needed
        if scenario_config.get('include_pedestrians', True):
            ped_file = self.generate_pedestrian_demand(
                count=scenario_config.get('pedestrian_count'),
                start_time=start_time,
                duration=duration,
                rain_intensity=rain_intensity,
                output_file=self.output_dir / f"{output_prefix}_pedestrians.xml"
            )
            output_files['pedestrian_demand'] = ped_file
            
        logger.info(f"Scenario demand generation complete: {output_files}")
        return output_files

if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    config = {
        'output_dir': 'data/output',
        'input_dir': 'data/input',
        'vehicles_per_hour': 800,
        'pedestrians_per_hour': 200,
    }
    
    # Network file (must exist)
    network_file = 'data/output/manhattan_small.net.xml'
    
    try:
        # Initialize demand generator
        generator = TrafficDemandGenerator(config, network_file)
        
        # Generate random trips
        print("\nGenerating random trips...")
        route_file = generator.generate_random_trips(
            duration=3600,
            rain_intensity=0.0
        )
        
        # Generate random trips with rain
        print("\nGenerating random trips with rain...")
        rain_route_file = generator.generate_random_trips(
            duration=3600,
            rain_intensity=5.0
        )
        
        # Generate pedestrian demand
        print("\nGenerating pedestrian demand...")
        ped_file = generator.generate_pedestrian_demand(
            duration=3600,
            rain_intensity=0.0
        )
        
        # Generate rain-affected pedestrian demand
        print("\nGenerating pedestrian demand with rain...")
        rain_ped_file = generator.generate_pedestrian_demand(
            duration=3600,
            rain_intensity=5.0
        )
        
        print("\nDemand generation complete!")
        print(f"Dry weather vehicle demand: {route_file}")
        print(f"Rainy weather vehicle demand: {rain_route_file}")
        print(f"Dry weather pedestrian demand: {ped_file}")
        print(f"Rainy weather pedestrian demand: {rain_ped_file}")
        
    except Exception as e:
        logger.error(f"Error in demand generation: {e}")
        import traceback
        traceback.print_exc()