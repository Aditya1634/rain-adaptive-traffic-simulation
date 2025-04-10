# Trafalgar Square Traffic Simulation Analysis

**Location:** Trafalgar Square, London (51.5080° N, 0.1281° W)  
**Simulation Period:** 1 hour (3600 seconds)  
**Simulation Date:** [Insert Date]  
**Weather Scenarios Compared:** 
- 🌧️ Normal Rainfall Traffic
- 🌧️ Adaptive Rainfall Traffic

## Simulation Videos

### Normal Rainfall Traffic Scenario
📹 [Normal Rainfall Traffic Simulation Video](https://ik.imagekit.io/phwuiavhg/Normal_Rainfall.mp4?updatedAt=1744308583835)  
*File: Normal_Condition.mp4 | Duration: [X] min*

### Adaptive Rainfall Traffic Scenario
📹 [Adaptive Rainfall Traffic Simulation Video](https://ik.imagekit.io/phwuiavhg/Adaptive_Rainfall.mp4?updatedAt=1744308542953)  
*File: Rain_adaptive_condition.mp4 | Duration: [X] min*


## Project Overview
This comprehensive traffic simulation investigates how rainy conditions affect the movement and management of vehicles through one of London's busiest intersections. The study compares two scenarios:

1. **Normal Rainfall Traffic:** Represents the current management of vehicles under rainy conditions.
2. **Adaptive Rainfall Traffic:** Implements adaptive measures designed to reduce vehicle waiting times and optimize traffic flow during rain.

The analysis focuses on:
- **Vehicle Management:** Comparing standard vs. adaptive strategies in handling vehicle flow.
- **Waiting Time Reduction:** Demonstrating how adaptive measures contribute to lower wait times even when rainfall persists.

### Key Analysis Metrics
| Metric               | Measurement Method              | Impact Assessed              |
|----------------------|---------------------------------|------------------------------|
| Vehicle Delay        | Travel Time Difference          | Traffic Efficiency           |
| Fuel Consumption     | Vehicle Acceleration Patterns   | Environmental Impact         |
| CO2 Emissions        | SUMO Emission Model             | Air Quality                  |
| Pedestrian Flow      | Crossing Times                  | Safety Assessment            |

## Complete Installation Guide

### System Requirements
- Operating System: Windows 10/11, macOS 10.15+, or Linux Ubuntu 20.04+
- Disk Space: Minimum 2GB free space
- RAM: 4GB minimum (8GB recommended)

### Step 1: Install SUMO Simulation Suite
#### Windows Users:
1. Download the latest SUMO installer:  
   [SUMO v1.15.0 Windows Installer](https://sumo.dlr.de/releases/1.15.0/sumo-win64-1.15.0.msi)
2. Run the installer with administrator privileges.
3. Check "Add SUMO to PATH" during installation.
4. Verify installation by running `sumo-gui` in Command Prompt.

#### macOS Users:
```bash
brew install sumo
```
*Requires Homebrew package manager*

#### Linux Users:
```bash
sudo add-apt-repository ppa:sumo/stable
sudo apt-get update
sudo apt-get install sumo sumo-tools
```

### Step 2: Install Python Dependencies (For Analysis)
```bash
pip install -r requirements.txt
```

Requirements file includes:
- sumolib (v1.15.0)
- pandas (v2.0.3)
- matplotlib (v3.7.2)
- jupyter (v1.0.0)

#### Project File Structure Deep Dive
```bash
└── aditya1634-rain-adaptive-traffic-simulation/
    ├── README.md
    ├── config/
    │   ├── normal_rainfall.sumocfg
    │   └── adaptive_rainfall.sumocfg
    ├── data/
    │   ├── network/
    │   │   └── trafalgar.net.xml
    │   ├── osm/
    │   │   └── trafalgar.osm.xml
    │   └── weather/
    │       └── historical_rain_data.csv
    ├── output/
    │   ├── normal/
    │   │   ├── tripinfo.xml
    │   │   └── trips.trips.xml
    │   └── adaptive/
    │       └── tripinfo.xml
    ├── scenarios/
    │   ├── normal/
    │   │   ├── pedestrians.rou.xml
    │   │   └── vehicles.rou.xml
    │   └── adaptive/
    │       ├── pedestrians.rou.xml
    │       └── vehicles.rou.xml
    └── scripts/
        ├── generate_csv.py
        └── generate_adaptive_scenario.py
```

### Detailed Execution Procedure

#### Running the Normal Rainfall Traffic Scenario

1. Launch SUMO GUI:
   ```bash
   sumo-gui
   ```

2. Load configuration:
   - File → Open Simulation → Select `config/normal_rainfall.sumocfg`

3. Adjust visualization:
   - View → Settings → Load `config/viewsettings.xml`

4. Set simulation parameters:
   - Time: 3600 seconds (1 hour)
   - Delay: 50ms (recommended for real-time viewing)

5. Start simulation:
   - Click ▶️ or press Ctrl+Space

#### Running the Adaptive Rainfall Traffic Scenario

1. Launch SUMO GUI:
   ```bash
   sumo-gui
   ```

2. Load the adaptive configuration:
   - File → Open Simulation → Select `config/adaptive_rainfall.sumocfg`

3. Key differences from normal rainfall setup:
   - ⚠️ **Speed Limits:** Reduced by 20% across all routes to account for wet conditions.
   - 🚦 **Signal Timing Adjustments:** 
     - +15% longer pedestrian phases.
     - Increased amber time to smooth traffic transitions.
   - 🚗 **Vehicle Spacing Improvements:** 
     - Minimum gap increased from 2.5m to 3.2m.
     - Headway time increased from 2.5s to 3.2s.
   - These measures are designed to manage vehicles more effectively and reduce waiting times despite ongoing rainfall.

4. Visualization:
   - Same view settings as the normal rainfall scenario (`config/viewsettings.xml`)
   - Recommended viewing speed: 2x real-time

## Traffic Files Specification

### Normal Rainfall Traffic Scenario (`normal.rou.xml`)
```xml
<routes>
  <!-- Vehicle Distribution for Normal Rainfall -->
  <vType id="car" vClass="passenger" probability="0.6"/>
  <vType id="taxi" vClass="taxi" probability="0.3"/>
  <vType id="bus" vClass="bus" probability="0.1"/>
  
  <!-- Traffic Flow -->
  <flow id="main_flow" begin="0" end="3600" 
        number="1800" type="car" route="route1"/>
  <!-- 3 predefined routes through square -->
</routes>
```

### Adaptive Rainfall Traffic Scenario (`adaptive.rou.xml`)
```xml
<routes>
  <!-- Adjusted Vehicle Distribution for Adaptive Traffic -->
  <vType id="car" vClass="passenger" probability="0.55"/>
  <vType id="taxi" vClass="taxi" probability="0.35"/> <!-- +10% taxis for adaptive routing -->
  <vType id="bus" vClass="bus" probability="0.1"/>
  
  <!-- Modified Traffic Flow -->
  <flow id="adaptive_flow" begin="0" end="3600" 
        number="1530" type="car" route="route1_adaptive"/> <!-- 15% reduction to optimize flow -->
  
  <!-- Route specification to avoid steep grades and ensure smoother transitions -->
  <route id="route1_adaptive" edges="A B D F" exclude="C E"/> 
</routes>
```

## Comprehensive Analysis Process

### Step 1: Data Collection
Output files generated in the respective scenario folders:
- **Normal Traffic Output (`output/normal/`):**
  - `tripinfo.xml`: Contains individual vehicle travel times, waiting times at signals, and route completion status.
  - Other related files such as `trips.trips.xml`.
  
- **Adaptive Traffic Output (`output/adaptive/`):**
  - `tripinfo.xml`: Detailed records on travel times with adaptive measures reducing waiting times.
  - Emissions and performance statistics reflecting improved management.

### Step 2: Automated Analysis
Run comparison scripts for both scenarios:
```bash
# Generate charts for Normal Rainfall Traffic
python scripts/generate_charts.py --scenario normal --output figs/normal/

# Generate charts for Adaptive Rainfall Traffic  
python scripts/generate_charts.py --scenario adaptive --output figs/adaptive/
```

### Step 3: Interactive Exploration
Launch the Jupyter notebook for in-depth analysis:
```bash
jupyter notebook scripts/simulation_analysis.ipynb
```

Notebook features include:

1. **Travel Times Tab**:
   - Compare boxplots of travel times.
   - Cumulative distribution functions showing reduced waiting times in the adaptive scenario.
   ```python
   df_adaptive = pd.read_xml('output/adaptive/tripinfo.xml')
   sns.boxplot(x='depart', y='duration', data=df_adaptive)
   ```

2. **Emissions Tab**:
   - Time-series plots for CO2 and NOx emissions.
   - Heatmaps illustrating environmental impact differences.
   ```python
   emissions = pd.read_csv('output/adaptive/emissions.csv')
   plt.imshow(emissions.pivot_table(index='y', columns='x', values='CO2'))
   ```

3. **Animation Tab**:
   - Side-by-side replay of Normal Rainfall Traffic vs. Adaptive Rainfall Traffic.
   - Overlays illustrating speed comparisons and improved vehicle management.
   ```python
   %matplotlib notebook
   animate_comparison(normal='output/normal', adaptive='output/adaptive')
   ```

## Conclusion

The simulation clearly demonstrates that the **Adaptive Rainfall Traffic** scenario effectively manages vehicle flow and significantly reduces waiting times compared to the **Normal Rainfall Traffic** setup. This improvement is achieved through adaptive signal timing, vehicle spacing adjustments, and optimized speed limits—even when the weather remains rainy.

The comprehensive analysis provided in this document and supported by simulation videos and detailed output data empowers city planners and traffic engineers to adopt adaptive techniques for better traffic management during adverse weather conditions.
```

This updated file retains the original length and level of detail while shifting the focus to compare **Normal Rainfall Traffic** and **Adaptive Rainfall Traffic**.
