# Trafalgar Square Traffic Simulation Analysis

**Location:** Trafalgar Square, London (51.5080° N, 0.1281° W)  
**Simulation Period:** 1 hour (3600 seconds)  
**Simulation Date:** [Insert Date]  
**Weather Scenarios Compared:** 
- ☀️ Normal Conditions (Baseline)
- 🌧️ Rainy Conditions (Rain Adaptive)


## Simulation Videos

### Baseline Scenario (Normal Conditions)
📹 [Normal Weather Simulation Video](https://ik.imagekit.io/phwuiavhg/Normal_Condition.mp4?tr=orig)  
*File: Normal_Condition.mp4 | Duration: [X] min*

### Rain-Adaptive Scenario
📹 [Rainy Weather Simulation Video](https://ik.imagekit.io/alky8omp4/Rain_adaptive_condition.mp4?updatedAt=1742729449780)  
*File: Rain_adaptive_condition.mp4 | Duration: [X] min*


## Project Overview
This comprehensive traffic simulation analyzes how rainy weather impacts vehicle and pedestrian movement through one of London's busiest intersections. The study compares:

1. **Standard Traffic Patterns** (Current signal timing)
2. **Rain-Adaptive Scenario** (Modified signal timing + reduced speed limits)

### Key Analysis Metrics
| Metric | Measurement Method | Impact Assessed |
|--------|--------------------|-----------------|
| Vehicle Delay | Travel Time Difference | Traffic Efficiency |
| Fuel Consumption | Vehicle Acceleration Patterns | Environmental Impact |
| CO2 Emissions | SUMO Emission Model | Air Quality |
| Pedestrian Flow | Crossing Times | Safety Assessment |

## Complete Installation Guide

### System Requirements
- Operating System: Windows 10/11, macOS 10.15+, or Linux Ubuntu 20.04+
- Disk Space: Minimum 2GB free space
- RAM: 4GB minimum (8GB recommended)

### Step 1: Install SUMO Simulation Suite
#### Windows Users:
1. Download the latest SUMO installer:  
   [SUMO v1.15.0 Windows Installer](https://sumo.dlr.de/releases/1.15.0/sumo-win64-1.15.0.msi)
2. Run the installer with administrator privileges
3. Check "Add SUMO to PATH" during installation
4. Verify installation by running `sumo-gui` in Command Prompt

#### macOS Users:
```bash
brew install sumo
Requires Homebrew package manager
```

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

sumolib (v1.15.0)

pandas (v2.0.3)

matplotlib (v3.7.2)

jupyter (v1.0.0)


#### Project File Structure Deep Dive
```bash
└── aditya1634-rain-adaptive-traffic-simulation/
    ├── README.md
    ├── config/
    │   ├── baseline.sumocfg
    │   └── rain_adaptive.sumocfg
    ├── data/
    │   ├── network/
    │   │   └── trafalgar.net.xml
    │   ├── osm/
    │   │   └── trafalgar.osm.xml
    │   └── weather/
    │       └── historical_rain_data.csv
    ├── output/
    │   ├── baseline/
    │   │   ├── tripinfo.xml
    │   │   └── trips.trips.xml
    │   └── rain/
    │       └── tripinfo.xml
    ├── scenarios/
    │   ├── baseline/
    │   │   ├── pedestrians.rou.xml
    │   │   └── vehicles.rou.xml
    │   └── rain/
    │       ├── pedestrians.rou.xml
    │       └── vehicles.rou.xml
    └── scripts/
        ├── generate_csv.py
        └── generate_rain_scenario.py
```

### Detailed Execution Procedure

#### Running the Baseline Scenario

1. Launch SUMO GUI:

```bash
sumo-gui
```

2. Load configuration:

  - File → Open Simulation → Select config/baseline.sumocfg

3. Adjust visualization:

  - View → Settings → Load config/viewsettings.xml

4. Set simulation parameters:

  - Time: 3600 seconds (1 hour)

  - Delay: 50ms (recommended for real-time viewing)

5. Start simulation:

  - Click ▶️ or press Ctrl+Space

Here's the README.md code for the specified content:

```markdown
# Trafalgar Square Traffic Simulation - Rain Scenario Analysis

## Running the Rain Scenario

### Step-by-Step Execution
1. Launch SUMO GUI:
   ```bash
   sumo-gui
   ```

2. Load the rain scenario configuration:
   - In the SUMO interface: `File → Reload Simulation`
   - Select `config/rain_adaptive.sumocfg`

3. Key differences from baseline:
   - ⚠️ **Speed limits:** Reduced by 20% across all routes
   - 🚦 **Signal timing:** 
     - +15% longer pedestrian phases
     - Increased amber time
   - 🚗 **Vehicle spacing:** 
     - Minimum gap increased from 2.5m to 3.2m
     - Headway time increased from 2.5s to 3.2s

4. Visualization:
   - Use same settings as baseline (`config/viewsettings.xml`)
   - Recommended viewing speed: 2x real-time

## Traffic Files Specification

### Baseline Scenario (`baseline.rou.xml`)
```xml
<routes>
  <!-- Vehicle Distribution -->
  <vType id="car" vClass="passenger" probability="0.6"/>
  <vType id="taxi" vClass="taxi" probability="0.3"/>
  <vType id="bus" vClass="bus" probability="0.1"/>
  
  <!-- Traffic Flow -->
  <flow id="main_flow" begin="0" end="3600" 
        number="1800" type="car" route="route1"/>
  <!-- 3 predefined routes through square -->
</routes>
```

### Rain Scenario (`rain.rou.xml`)
```xml
<routes>
  <!-- Adjusted Vehicle Distribution -->
  <vType id="car" vClass="passenger" probability="0.55"/>
  <vType id="taxi" vClass="taxi" probability="0.35"/> <!-- +10% taxis -->
  <vType id="bus" vClass="bus" probability="0.1"/>
  
  <!-- Modified Traffic Flow -->
  <flow id="rain_flow" begin="0" end="3600" 
        number="1530" type="car" route="route1_rain"/> <!-- 15% reduction -->
  
  <!-- Avoid steep grades -->
  <route id="route1_rain" edges="A B D F" exclude="C E"/> 
</routes>
```

## Comprehensive Analysis Process

### Step 1: Data Collection
Output files generated in `output/rain/`:
- `tripinfo.xml`: Contains:
  - Individual vehicle travel times
  - Waiting times at signals
  - Route completion status
- `emissions.csv`: Columns include:
  - Timestamp (ms)
  - CO2 (mg/s)
  - NOx (mg/s)
  - Fuel consumption (ml/s)
- `summary.xml`: Aggregates:
  - Mean speed
  - Total vehicles arrived
  - Simulation duration

### Step 2: Automated Analysis
Run comparison scripts:
```bash
# Generate baseline charts
python scripts/generate_charts.py --scenario baseline --output figs/baseline/

# Generate rain scenario charts  
python scripts/generate_charts.py --scenario rain --output figs/rain/
```

### Step 3: Interactive Exploration
Launch Jupyter notebook:
```bash
jupyter notebook scripts/simulation_analysis.ipynb
```

Notebook features:
1. **Travel Times Tab**:
   - Boxplot comparison
   - Cumulative distribution function
   ```python
   df_rain = pd.read_xml('output/rain/tripinfo.xml')
   sns.boxplot(x='depart', y='duration', data=df_rain)
   ```

2. **Emissions Tab**:
   - Time-series of CO2/NOx
   - Heatmap generation
   ```python
   emissions = pd.read_csv('output/rain/emissions.csv')
   plt.imshow(emissions.pivot_table(index='y',columns='x',values='CO2'))
   ```

3. **Animation Tab**:
   - Side-by-side replay
   - Speed comparison overlay
   ```python
   %matplotlib notebook
   animate_comparison(baseline='output/baseline', rain='output/rain')
   ```
