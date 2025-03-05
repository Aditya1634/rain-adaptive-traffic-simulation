#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SUMO Network generation and configuration utilities for rain-adaptive traffic simulation.
"""

import os
import subprocess
import logging
from pathlib import Path
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np

# Configure logging
logger = logging.getLogger(__name__)

class SUMONetworkGenerator:
    """
    Handles the generation and configuration of SUMO networks for traffic simulation.
    Provides functionality to create networks from OSM data, modify network parameters,
    and configure traffic lights for rain-adaptive control.
    """
    
    def __init__(self, config):
        """
        Initialize the network generator.
        
        Args:
            config: Dict containing configuration parameters
        """
        self.config = config
        self.network_file = None
        self.osm_file = None
        
        # Configure paths
        self.output_dir = Path(config.get('output_dir', 'data/output'))
        self.input_dir = Path(config.get('input_dir', 'data/input'))
        
        # Ensure directories exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.input_dir.mkdir(parents=True, exist_ok=True)
        
        # SUMO binary paths - try to get from environment or use defaults
        self.sumo_home = os.environ.get('SUMO_HOME')
        if not self.sumo_home:
            logger.warning("SUMO_HOME environment variable not set. Using default binary paths.")
            
        # Junction parameters
        self.rain_speed_factor = config.get('rain_speed_factor', 0.8)
        self.junction_type = config.get('junction_type', 'traffic_light')
        
    def import_osm(self, osm_file, bbox=None, prefix=None):
        """
        Import OpenStreetMap data for network generation.
        
        Args:
            osm_file: Path to OSM file or URL
            bbox: Bounding box for OSM data (min_lon, min_lat, max_lon, max_lat)
            prefix: Prefix for output files
            
        Returns:
            Path to the created OSM file
        """
        if bbox and not os.path.exists(osm_file):
            # Download OSM data using the bbox
            prefix = prefix or "network"
            output_file = self.input_dir / f"{prefix}.osm"
            cmd = [
                "wget", 
                f"https://api.openstreetmap.org/api/0.6/map?bbox={','.join(map(str, bbox))}", 
                "-O", str(output_file)
            ]
            logger.info(f"Downloading OSM data with bbox {bbox}")
            subprocess.run(cmd, check=True)
            self.osm_file = output_file
        else:
            # Use provided file
            if not os.path.exists(osm_file):
                raise FileNotFoundError(f"OSM file not found: {osm_file}")
            self.osm_file = Path(osm_file)
            
        logger.info(f"OSM file set to {self.osm_file}")
        return self.osm_file
    
    def generate_network(self, output_prefix=None, options=None):
        """
        Generate SUMO network from OSM data.
        
        Args:
            output_prefix: Prefix for output files
            options: Additional options for netconvert
            
        Returns:
            Path to the generated network file
        """
        if not self.osm_file:
            raise ValueError("OSM file not set. Call import_osm() first.")
            
        output_prefix = output_prefix or Path(self.osm_file).stem
        net_output = self.output_dir / f"{output_prefix}.net.xml"
        
        # Build command for netconvert
        cmd = [
            "netconvert",
            "--osm", str(self.osm_file),
            "--output", str(net_output),
            "--geometry.remove", "true",
            "--roundabouts.guess", "true",
            "--junctions.join", "true",
            "--tls.guess", "true",
            "--tls.default-type", "actuated",
        ]
        
        # Add additional options
        if options:
            for key, value in options.items():
                cmd.extend([f"--{key}", str(value)])
                
        # Run netconvert
        logger.info(f"Generating SUMO network with command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Network generation failed: {result.stderr}")
            raise RuntimeError(f"Failed to generate network: {result.stderr}")
        
        logger.info(f"Network generated successfully: {net_output}")
        self.network_file = net_output
        return net_output
    
    def extract_poly(self, output_prefix=None, options=None):
        """
        Extract polygons from OSM data for visualization.
        
        Args:
            output_prefix: Prefix for output files
            options: Additional options for polyconvert
            
        Returns:
            Path to the generated polygon file
        """
        if not self.osm_file:
            raise ValueError("OSM file not set. Call import_osm() first.")
            
        output_prefix = output_prefix or Path(self.osm_file).stem
        poly_output = self.output_dir / f"{output_prefix}.poly.xml"
        
        # Build command for polyconvert
        cmd = [
            "polyconvert",
            "--osm-files", str(self.osm_file),
            "--net-file", str(self.network_file),
            "--output-file", str(poly_output),
            "--osm.keep-full-type", "true"
        ]
        
        # Add additional options
        if options:
            for key, value in options.items():
                cmd.extend([f"--{key}", str(value)])
                
        # Run polyconvert
        logger.info(f"Extracting polygons with command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Polygon extraction failed: {result.stderr}")
            raise RuntimeError(f"Failed to extract polygons: {result.stderr}")
        
        logger.info(f"Polygons extracted successfully: {poly_output}")
        return poly_output
    
    def customize_network_for_rain(self, rain_intensity=None):
        """
        Customize network parameters based on rain intensity.
        
        Args:
            rain_intensity: Current rain intensity in mm/h (if None, uses the config value)
            
        Returns:
            Path to the modified network file
        """
        if not self.network_file:
            raise ValueError("Network file not set. Call generate_network() first.")
            
        # Use provided rain intensity or get from config
        rain_intensity = rain_intensity or self.config.get('rain_intensity', 0.0)
        
        # Calculate speed factor based on rain intensity
        # More intense rain = greater speed reduction
        if rain_intensity > 0:
            # Logarithmic relationship - more reduction at higher intensities, but with diminishing effect
            speed_factor = max(0.5, 1.0 - 0.1 * np.log(1 + rain_intensity))
        else:
            speed_factor = 1.0
            
        logger.info(f"Customizing network for rain intensity {rain_intensity} mm/h (speed factor: {speed_factor:.2f})")
        
        # Parse the network file
        tree = ET.parse(self.network_file)
        root = tree.getroot()
        
        # Modify edge speeds
        edges_modified = 0
        for edge in root.findall(".//edge"):
            # Only modify roads (not pedestrian paths, etc.)
            if edge.get("function") != "internal" and not edge.get("allow") == "pedestrian":
                speed = float(edge.get("speed", 13.89))  # Default to 50 km/h (13.89 m/s)
                new_speed = speed * speed_factor
                edge.set("speed", str(new_speed))
                edges_modified += 1
        
        # Modify junction parameters for wet conditions
        junctions_modified = 0
        for junction in root.findall(".//junction"):
            if junction.get("type") == "traffic_light":
                # Increase minimum gap for safety in rain
                if "minGap" in junction.attrib:
                    min_gap = float(junction.get("minGap", 2.5))
                    junction.set("minGap", str(min_gap * 1.2))  # 20% increase in minimum gap
                
                junctions_modified += 1
        
        # Save modified network
        rain_network_file = self.output_dir / f"{Path(self.network_file).stem}_rain.net.xml"
        tree.write(rain_network_file)
        
        logger.info(f"Modified {edges_modified} edges and {junctions_modified} junctions for rain conditions")
        logger.info(f"Rain-customized network saved to {rain_network_file}")
        
        return rain_network_file
    
    def create_traffic_light_programs(self, tls_file=None):
        """
        Create traffic light programs for the network.
        
        Args:
            tls_file: Path to write traffic light programs
            
        Returns:
            Path to the traffic light program file
        """
        if not self.network_file:
            raise ValueError("Network file not set. Call generate_network() first.")
            
        # Default output file
        if not tls_file:
            tls_file = self.output_dir / f"{Path(self.network_file).stem}_tls.add.xml"
            
        # Parse the network file to extract traffic light junctions
        tree = ET.parse(self.network_file)
        root = tree.getroot()
        
        # Extract traffic light IDs
        tls_ids = []
        for tl in root.findall(".//tlLogic"):
            tls_ids.append(tl.get("id"))
            
        logger.info(f"Found {len(tls_ids)} traffic lights in the network")
        
        # Create a new XML for additional TLS programs
        tls_root = ET.Element("additional")
        
        # For each traffic light, create baseline and rain-adaptive programs
        for tls_id in tls_ids:
            # Extract original phases
            original_tl = root.find(f".//tlLogic[@id='{tls_id}']")
            if original_tl is None:
                continue
                
            original_phases = original_tl.findall("phase")
            phase_count = len(original_phases)
            
            # Create rain-adaptive program (longer yellow phases, longer green for main direction)
            tl_program = ET.SubElement(tls_root, "tlLogic")
            tl_program.set("id", tls_id)
            tl_program.set("type", "actuated")
            tl_program.set("programID", "rain_adaptive")
            tl_program.set("offset", "0")
            
            for i, phase in enumerate(original_phases):
                new_phase = ET.SubElement(tl_program, "phase")
                
                # Copy all attributes
                for key, value in phase.attrib.items():
                    new_phase.set(key, value)
                
                # Modify durations for rain adaptation
                if "duration" in phase.attrib:
                    phase_type = self._determine_phase_type(phase.get("state", ""))
                    
                    if phase_type == "yellow":
                        # Longer yellow time in rain for safety
                        duration = float(phase.get("duration"))
                        new_phase.set("duration", str(duration * 1.5))  # 50% longer yellow
                    elif phase_type == "green" and i < phase_count / 2:
                        # Extend main direction green phase (assumed to be first half of phases)
                        duration = float(phase.get("duration"))
                        new_phase.set("duration", str(duration * 1.2))  # 20% longer green
        
        # Write to file
        tree = ET.ElementTree(tls_root)
        tree.write(tls_file)
        
        logger.info(f"Created traffic light programs at {tls_file}")
        return tls_file
    
    def _determine_phase_type(self, state):
        """
        Determine the type of traffic light phase based on its state string.
        
        Args:
            state: The state string from the phase
            
        Returns:
            String indicating the phase type ('red', 'yellow', 'green')
        """
        if 'y' in state.lower():
            return "yellow"
        elif 'g' in state.lower():
            return "green"
        else:
            return "red"
            
    def analyze_network(self):
        """
        Analyze the network to extract key metrics and structure.
        
        Returns:
            Dict with network analysis results
        """
        if not self.network_file:
            raise ValueError("Network file not set. Call generate_network() first.")
            
        # Parse the network file
        tree = ET.parse(self.network_file)
        root = tree.getroot()
        
        # Extract basic statistics
        edges = root.findall(".//edge")
        junctions = root.findall(".//junction")
        connections = root.findall(".//connection")
        traffic_lights = root.findall(".//tlLogic")
        
        # Count different road types
        road_types = {}
        total_length = 0
        for edge in edges:
            if edge.get("function") != "internal":
                edge_type = edge.get("type", "unknown")
                road_types[edge_type] = road_types.get(edge_type, 0) + 1
                
                # Calculate length if available
                if "length" in edge.attrib:
                    total_length += float(edge.get("length"))
        
        # Analyze junctions
        junction_types = {}
        for junction in junctions:
            j_type = junction.get("type", "unknown")
            junction_types[j_type] = junction_types.get(j_type, 0) + 1
        
        # Network complexity metrics
        metrics = {
            "total_edges": len([e for e in edges if e.get("function") != "internal"]),
            "internal_edges": len([e for e in edges if e.get("function") == "internal"]),
            "total_junctions": len(junctions),
            "traffic_lights": len(traffic_lights),
            "connections": len(connections),
            "total_length_m": total_length,
            "road_types": road_types,
            "junction_types": junction_types,
            "avg_speed_limit": np.mean([float(e.get("speed", 13.89)) for e in edges if e.get("function") != "internal"]),
            "network_density": len(connections) / max(1, len(junctions)),  # Connections per junction
        }
        
        # Calculate junction complexity for ML model
        junction_complexity = {}
        for junction in junctions:
            j_id = junction.get("id")
            incoming = len(root.findall(f".//connection[@to='{j_id}']"))
            outgoing = len(root.findall(f".//connection[@from='{j_id}']"))
            
            # Complexity score based on number of connections and traffic light presence
            is_tl = junction.get("type") == "traffic_light"
            complexity = (incoming + outgoing) * (1.5 if is_tl else 1.0)
            junction_complexity[j_id] = min(5, complexity / 4)  # Scale 0-5
            
        metrics["junction_complexity"] = junction_complexity
        
        logger.info(f"Network analysis complete: {metrics['total_edges']} edges, {metrics['total_junctions']} junctions")
        return metrics
    
    def export_junction_data(self, output_file=None):
        """
        Export junction data for use in ML models and analysis.
        
        Args:
            output_file: Path to save the junction data
            
        Returns:
            DataFrame with junction data and path to saved CSV
        """
        metrics = self.analyze_network()
        
        # Create junction DataFrame
        junctions = []
        for j_id, complexity in metrics["junction_complexity"].items():
            junctions.append({
                "junction_id": j_id,
                "complexity": complexity,
                "is_traffic_light": j_id in [tl.get("id") for tl in ET.parse(self.network_file).findall(".//tlLogic")]
            })
            
        df = pd.DataFrame(junctions)
        
        # Save to file if requested
        if output_file:
            output_path = self.output_dir / output_file
            df.to_csv(output_path, index=False)
            logger.info(f"Junction data exported to {output_path}")
            return df, output_path
            
        return df

if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    config = {
        'output_dir': 'data/output',
        'input_dir': 'data/input',
        'rain_intensity': 2.5,  # mm/h
    }
    
    # Initialize network generator
    generator = SUMONetworkGenerator(config)
    
    # Example for Manhattan (small area)
    bbox = (-74.0050, 40.7090, -73.9950, 40.7190)
    
    try:
        # Import OSM data
        osm_file = generator.import_osm(None, bbox=bbox, prefix="manhattan_small")
        
        # Generate network
        net_file = generator.generate_network()
        
        # Extract polygons for visualization
        poly_file = generator.extract_poly()
        
        # Create rain-adapted network
        rain_net_file = generator.customize_network_for_rain()
        
        # Create traffic light programs
        tls_file = generator.create_traffic_light_programs()
        
        # Analyze network
        metrics = generator.analyze_network()
        
        # Export junction data
        junction_df, junction_file = generator.export_junction_data("junctions.csv")
        
        print("Network generation complete!")
        print(f"Network file: {net_file}")
        print(f"Rain-adapted network: {rain_net_file}")
        print(f"Traffic light programs: {tls_file}")
        print(f"Junction data: {junction_df.head()}")
        
    except Exception as e:
        logger.error(f"Error in network generation: {e}")
        import traceback
        traceback.print_exc()