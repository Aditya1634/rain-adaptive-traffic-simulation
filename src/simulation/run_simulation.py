# run_simulation.py
import os
import sys
import argparse
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.simulation.rain_adaptive_controller import RainAdaptiveController
# from rain_adaptive_controller import RainAdaptiveController

def run_baseline_simulation(config_file, steps=3600):
    """Run baseline simulation without any rain adaptation"""
    # Create controller but don't apply adaptations
    controller = RainAdaptiveController(config_file, None, None)
    
    # Override adaptive methods to do nothing
    controller.adjust_vehicle_speeds = lambda: None
    controller.adjust_traffic_lights = lambda: None
    
    print("Running baseline simulation...")
    controller.run_simulation(steps)
    controller.save_statistics("baseline_results.csv")

def run_adaptive_simulation(config_file, api_key, city, steps=3600):
    """Run simulation with rain-adaptive controls"""
    controller = RainAdaptiveController(config_file, api_key, city)
    
    print("Running rain-adaptive simulation...")
    controller.run_simulation(steps)
    controller.save_statistics("adaptive_results.csv")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run traffic simulation with rain adaptation')
    parser.add_argument('--config', required=True, help='Path to SUMO configuration file')
    parser.add_argument('--mode', choices=['baseline', 'adaptive', 'both'], default='both', 
                        help='Simulation mode: baseline, adaptive, or both')
    parser.add_argument('--steps', type=int, default=3600, help='Number of simulation steps')
    parser.add_argument('--api-key', help='OpenWeatherMap API key')
    parser.add_argument('--city', default='London', help='City name for weather data')
    
    args = parser.parse_args()
    
    if args.mode in ['baseline', 'both']:
        run_baseline_simulation(args.config, args.steps)
    
    if args.mode in ['adaptive', 'both']:
        if not args.api_key:
            print("Warning: No API key provided. Using simulated weather data.")
        run_adaptive_simulation(args.config, args.api_key, args.city, args.steps)
    
    print("Simulations completed!")