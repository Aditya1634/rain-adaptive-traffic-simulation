#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interactive dashboard for rain-adaptive traffic simulation results.
This script creates a Dash/Plotly dashboard to visualize and explore simulation results.
"""

import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
import dash
from dash import dcc, html, Input, Output, State
import plotly.express as px
import plotly.graph_objects as go
from dash.exceptions import PreventUpdate
import json
import base64
import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

# Import custom modules for analysis if needed
from src.visualization.plot_traffic_flow import load_traffic_data
from src.visualization.plot_wait_times import load_wait_time_data

# Set paths
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
OUTPUT_DIR = DATA_DIR / "output"
BASELINE_DIR = OUTPUT_DIR / "baseline_simulation"
ADAPTIVE_DIR = OUTPUT_DIR / "adaptive_simulation"
WEATHER_DIR = OUTPUT_DIR / "weather"
VIS_DIR = OUTPUT_DIR / "visualizations"

# Ensure visualization directory exists
os.makedirs(VIS_DIR, exist_ok=True)

# Initialize the Dash app
app = dash.Dash(__name__, title="Rain-Adaptive Traffic Simulation Dashboard")
server = app.server  # For deployment

# Define color scheme
COLORS = {
    'background': '#f8f9fa',
    'text': '#212529',
    'baseline': '#dc3545',  # Red
    'adaptive': '#28a745',  # Green
    'neutral': '#007bff',   # Blue
    'light_neutral': '#e9ecef',
    'plot_bg': '#ffffff',
    'gridlines': '#e9ecef'
}

# Define the app layout
app.layout = html.Div([
    # Header
    html.Div([
        html.H1("Rain-Adaptive Traffic Simulation Dashboard", 
                style={'color': COLORS['text'], 'textAlign': 'center'}),
        html.P("Interactive visualization of traffic simulation results with and without rain adaptation",
               style={'color': COLORS['text'], 'textAlign': 'center'})
    ], style={'padding': '20px', 'backgroundColor': COLORS['background']}),
    
    # Controls and Filters
    html.Div([
        html.Div([
            html.Label("Data Source"),
            dcc.RadioItems(
                id='data-source',
                options=[
                    {'label': 'Sample Data', 'value': 'sample'},
                    {'label': 'Upload Data', 'value': 'upload'}
                ],
                value='sample',
                labelStyle={'display': 'inline-block', 'marginRight': '10px'}
            )
        ], style={'width': '30%', 'display': 'inline-block'}),
        
        html.Div([
            html.Label("File Upload"),
            dcc.Upload(
                id='upload-data',
                children=html.Div(['Drag and Drop or ', html.A('Select Files')]),
                style={
                    'width': '100%',
                    'height': '60px',
                    'lineHeight': '60px',
                    'borderWidth': '1px',
                    'borderStyle': 'dashed',
                    'borderRadius': '5px',
                    'textAlign': 'center',
                    'margin': '10px'
                },
                multiple=True,
                disabled=True
            ),
        ], style={'width': '70%', 'display': 'inline-block'}),
        
        html.Div([
            html.Label("Visualization Type"),
            dcc.Dropdown(
                id='viz-type',
                options=[
                    {'label': 'Traffic Flow Comparison', 'value': 'flow_comparison'},
                    {'label': 'Wait Time Comparison', 'value': 'wait_comparison'},
                    {'label': 'Effectiveness Heatmap', 'value': 'heatmap'},
                    {'label': 'Rainfall Impact Analysis', 'value': 'rainfall_impact'},
                    {'label': 'Intersection Performance', 'value': 'intersection_performance'}
                ],
                value='flow_comparison'
            )
        ], style={'width': '50%', 'display': 'inline-block', 'padding': '10px'}),
        
        html.Div([
            html.Label("Time Range"),
            dcc.RangeSlider(
                id='time-slider',
                min=0,
                max=24,
                step=0.5,
                marks={i: f'{i}:00' if i % 3 == 0 else '' for i in range(0, 25, 1)},
                value=[0, 24]
            )
        ], style={'width': '50%', 'display': 'inline-block', 'padding': '10px'})
    ], style={'padding': '10px', 'backgroundColor': COLORS['light_neutral'], 'borderRadius': '5px'}),
    
    # Main content - visualization area
    html.Div([
        dcc.Loading(
            id="loading-main",
            type="circle",
            children=[
                html.Div(id='visualization-container', style={'height': '60vh'})
            ]
        )
    ], style={'padding': '20px'}),
    
    # Key Metrics Section
    html.Div([
        html.H3("Key Performance Metrics", style={'textAlign': 'center'}),
        
        html.Div([
            # Metric 1
            html.Div([
                html.Div([
                    html.H4("Avg. Traffic Flow Improvement", style={'textAlign': 'center'}),
                    html.Div(id='metric-flow', style={'fontSize': '24px', 'textAlign': 'center'})
                ], style={'backgroundColor': 'white', 'borderRadius': '5px', 'padding': '10px'})
            ], style={'width': '25%', 'display': 'inline-block', 'padding': '10px'}),
            
            # Metric 2
            html.Div([
                html.Div([
                    html.H4("Avg. Wait Time Reduction", style={'textAlign': 'center'}),
                    html.Div(id='metric-wait', style={'fontSize': '24px', 'textAlign': 'center'})
                ], style={'backgroundColor': 'white', 'borderRadius': '5px', 'padding': '10px'})
            ], style={'width': '25%', 'display': 'inline-block', 'padding': '10px'}),
            
            # Metric 3
            html.Div([
                html.Div([
                    html.H4("Avg. Speed Improvement", style={'textAlign': 'center'}),
                    html.Div(id='metric-speed', style={'fontSize': '24px', 'textAlign': 'center'})
                ], style={'backgroundColor': 'white', 'borderRadius': '5px', 'padding': '10px'})
            ], style={'width': '25%', 'display': 'inline-block', 'padding': '10px'}),
            
            # Metric 4
            html.Div([
                html.Div([
                    html.H4("System Effectiveness Score", style={'textAlign': 'center'}),
                    html.Div(id='metric-effectiveness', style={'fontSize': '24px', 'textAlign': 'center'})
                ], style={'backgroundColor': 'white', 'borderRadius': '5px', 'padding': '10px'})
            ], style={'width': '25%', 'display': 'inline-block', 'padding': '10px'})
        ])
    ], style={'padding': '20px', 'backgroundColor': COLORS['light_neutral'], 'margin': '20px 0', 'borderRadius': '5px'}),
    
    # Secondary visualization area - complementary charts
    html.Div([
        html.Div([
            html.H3("Detailed Analysis", style={'textAlign': 'center'}),
            dcc.Tabs([
                dcc.Tab(label="Time Analysis", children=[
                    dcc.Loading(
                        id="loading-time-tab",
                        children=[html.Div(id='time-analysis', style={'padding': '20px', 'height': '40vh'})]
                    )
                ]),
                dcc.Tab(label="Spatial Analysis", children=[
                    dcc.Loading(
                        id="loading-spatial-tab",
                        children=[html.Div(id='spatial-analysis', style={'padding': '20px', 'height': '40vh'})]
                    )
                ]),
                dcc.Tab(label="Rainfall Analysis", children=[
                    dcc.Loading(
                        id="loading-rainfall-tab",
                        children=[html.Div(id='rainfall-analysis', style={'padding': '20px', 'height': '40vh'})]
                    )
                ])
            ])
        ])
    ], style={'padding': '20px'}),
    
    # Store for data sharing between callbacks
    dcc.Store(id='stored-data'),
    
    # Footer
    html.Div([
        html.P("Rain-Adaptive Traffic Simulation Dashboard — Created with Dash & Plotly", 
               style={'textAlign': 'center', 'color': COLORS['text']})
    ], style={'padding': '20px', 'backgroundColor': COLORS['background'], 'marginTop': '20px'})
])

# Helper functions
def generate_sample_data():
    """Generate sample data if actual data is not available."""
    # Time range
    times = np.linspace(0, 24, 96)  # 15-minute intervals over 24 hours
    
    # Sample rainfall pattern
    rainfall = 2 * np.sin(np.pi * times / 12) + 1
    rainfall = np.clip(rainfall, 0, None)
    rainfall[rainfall < 0.2] = 0
    rainfall[32:40] = np.linspace(1, 10, 8)  # Heavy rain period
    rainfall[40:48] = np.linspace(10, 1, 8)  # Tapering off
    
    # Sample traffic flow - baseline
    base_flow = 1000 + 500 * np.sin(np.pi * times / 12 + np.pi/6)  # Morning and evening peaks
    base_flow -= rainfall * 20  # Flow decreases with rain
    
    # Sample traffic flow - adaptive
    adaptive_flow = base_flow.copy()
    adaptive_flow += rainfall * 15  # Adaptive strategy mitigates some rain impact
    
    # Sample wait times - baseline
    base_wait = 20 + 10 * np.sin(np.pi * times / 12) + rainfall * 4
    
    # Sample wait times - adaptive
    adaptive_wait = base_wait - rainfall * 2.5  # Adaptive strategy reduces wait during rain
    
    # Create DataFrames
    flow_data = pd.DataFrame({
        'time': times,
        'hour': times,
        'rainfall': rainfall,
        'flow_rate_baseline': base_flow,
        'flow_rate_adaptive': adaptive_flow
    })
    
    wait_data = pd.DataFrame({
        'time': times,
        'hour': times,
        'rainfall': rainfall,
        'avg_wait_time_baseline': base_wait,
        'avg_wait_time_adaptive': adaptive_wait
    })
    
    # Sample spatial data
    num_intersections = 20
    lats = np.random.uniform(40.7, 40.8, num_intersections)
    lons = np.random.uniform(-74.0, -73.9, num_intersections)
    
    spatial_data = pd.DataFrame({
        'intersection_id': [f'I{i:02d}' for i in range(num_intersections)],
        'lat': lats,
        'lon': lons,
        'avg_wait_time_baseline': np.random.uniform(20, 40, num_intersections),
        'avg_wait_time_adaptive': np.random.uniform(15, 35, num_intersections),
        'vehicles_per_hour_baseline': np.random.uniform(800, 1200, num_intersections),
        'vehicles_per_hour_adaptive': np.random.uniform(900, 1300, num_intersections)
    })
    
    # Calculate improvements
    spatial_data['wait_time_improvement'] = ((spatial_data['avg_wait_time_baseline'] - 
                                             spatial_data['avg_wait_time_adaptive']) / 
                                            spatial_data['avg_wait_time_baseline'] * 100)
    
    spatial_data['throughput_improvement'] = ((spatial_data['vehicles_per_hour_adaptive'] - 
                                              spatial_data['vehicles_per_hour_baseline']) / 
                                             spatial_data['vehicles_per_hour_baseline'] * 100)
    
    # Create effectiveness score
    spatial_data['effectiveness_score'] = (0.6 * spatial_data['wait_time_improvement'] + 
                                          0.4 * spatial_data['throughput_improvement'])
    
    return {
        'flow_data': flow_data,
        'wait_data': wait_data,
        'spatial_data': spatial_data
    }

def parse_uploaded_data(contents, filename):
    """Parse uploaded data files."""
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    
    try:
        if 'csv' in filename:
            return pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        elif 'json' in filename:
            return pd.DataFrame(json.loads(decoded.decode('utf-8')))
        else:
            return None
    except Exception as e:
        print(e)
        return None

def load_real_data():
    """Attempt to load real simulation output data."""
    try:
        # Load flow data
        baseline_flow = load_traffic_data(str(BASELINE_DIR / "traffic_flow.csv"))
        adaptive_flow = load_traffic_data(str(ADAPTIVE_DIR / "traffic_flow.csv"))
        
        # Load wait time data
        baseline_wait = load_wait_time_data(str(BASELINE_DIR / "wait_times.csv"))
        adaptive_wait = load_wait_time_data(str(ADAPTIVE_DIR / "wait_times.csv"))
        
        # Load weather data
        weather_data = pd.read_csv(str(WEATHER_DIR / "rainfall_data.csv"))
        
        # Load spatial data
        baseline_spatial = pd.read_csv(str(BASELINE_DIR / "spatial_metrics.csv"))
        adaptive_spatial = pd.read_csv(str(ADAPTIVE_DIR / "spatial_metrics.csv"))
        
        # Merge flow and wait data with weather
        if all(df is not None for df in [baseline_flow, adaptive_flow, baseline_wait, adaptive_wait, weather_data]):
            # Assuming we can merge on 'time' column
            flow_data = pd.merge(
                baseline_flow.rename(columns={'flow_rate': 'flow_rate_baseline'}),
                adaptive_flow.rename(columns={'flow_rate': 'flow_rate_adaptive'}),
                on='time'
            )
            flow_data = pd.merge(flow_data, weather_data, on='time')
            
            wait_data = pd.merge(
                baseline_wait.rename(columns={'avg_wait_time': 'avg_wait_time_baseline'}),
                adaptive_wait.rename(columns={'avg_wait_time': 'avg_wait_time_adaptive'}),
                on='time'
            )
            wait_data = pd.merge(wait_data, weather_data, on='time')
            
            # Process spatial data
            spatial_data = pd.merge(
                baseline_spatial,
                adaptive_spatial,
                on=['intersection_id', 'lat', 'lon'],
                suffixes=('_baseline', '_adaptive')
            )
            
            # Calculate improvement metrics
            spatial_data['wait_time_improvement'] = (
                (spatial_data['avg_wait_time_baseline'] - spatial_data['avg_wait_time_adaptive']) / 
                spatial_data['avg_wait_time_baseline'] * 100
            )
            
            spatial_data['throughput_improvement'] = (
                (spatial_data['vehicles_per_hour_adaptive'] - spatial_data['vehicles_per_hour_baseline']) / 
                spatial_data['vehicles_per_hour_baseline'] * 100
            )
            
            spatial_data['effectiveness_score'] = (
                0.6 * spatial_data['wait_time_improvement'] + 
                0.4 * spatial_data['throughput_improvement']
            )
            
            return {
                'flow_data': flow_data,
                'wait_data': wait_data,
                'spatial_data': spatial_data
            }
    
    except Exception as e:
        print(f"Error loading real data: {e}")
    
    return None

# Callback to handle data source selection
@app.callback(
    Output('upload-data', 'disabled'),
    Input('data-source', 'value')
)
def update_upload_status(source):
    return source != 'upload'

# Callback to load and store data
@app.callback(
    Output('stored-data', 'data'),
    Input('data-source', 'value'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename')
)
def load_and_store_data(source, contents, filenames):
    # First try loading real data
    real_data = load_real_data()
    
    if source == 'sample':
        # If real data exists, use it; otherwise use sample data
        if real_data:
            return real_data
        else:
            return generate_sample_data()
    
    elif source == 'upload' and contents:
        # TODO: Implement uploaded data processing
        # For now, return sample data
        return generate_sample_data()
    
    # Default: return sample data
    return generate_sample_data()

# Callback to update main visualization
@app.callback(
    Output('visualization-container', 'children'),
    Input('viz-type', 'value'),
    Input('time-slider', 'value'),
    Input('stored-data', 'data')
)
def update_main_visualization(viz_type, time_range, data):
    if not data:
        return html.Div("No data available.")
    
    # Filter by time range
    flow_data = pd.DataFrame(data['flow_data'])
    wait_data = pd.DataFrame(data['wait_data'])
    spatial_data = pd.DataFrame(data['spatial_data'])
    
    flow_data = flow_data[(flow_data['hour'] >= time_range[0]) & (flow_data['hour'] <= time_range[1])]
    wait_data = wait_data[(wait_data['hour'] >= time_range[0]) & (wait_data['hour'] <= time_range[1])]
    
    if viz_type == 'flow_comparison':
        # Traffic flow comparison
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=flow_data['time'], 
            y=flow_data['flow_rate_baseline'],
            name='Baseline Strategy',
            line=dict(color=COLORS['baseline'], width=2)
        ))
        
        fig.add_trace(go.Scatter(
            x=flow_data['time'], 
            y=flow_data['flow_rate_adaptive'],
            name='Rain-Adaptive Strategy',
            line=dict(color=COLORS['adaptive'], width=2)
        ))
        
        # Add rainfall as a separate axis
        fig.add_trace(go.Scatter(
            x=flow_data['time'], 
            y=flow_data['rainfall'],
            name='Rainfall (mm/h)',
            line=dict(color='lightblue', width=1, dash='dot'),
            fill='tozeroy',
            fillcolor='rgba(173, 216, 230, 0.3)',
            yaxis='y2'
        ))
        
        fig.update_layout(
            title='Traffic Flow Comparison',
            xaxis_title='Time (hours)',
            yaxis_title='Traffic Flow (vehicles/hour)',
            yaxis2=dict(
                title='Rainfall (mm/h)',
                titlefont=dict(color='lightblue'),
                tickfont=dict(color='lightblue'),
                overlaying='y',
                side='right'
            ),
            plot_bgcolor=COLORS['plot_bg'],
            paper_bgcolor=COLORS['plot_bg'],
            legend=dict(
                x=0.01,
                y=0.99,
                bgcolor='rgba(255, 255, 255, 0.8)',
                bordercolor='rgba(0, 0, 0, 0.2)',
                borderwidth=1
            ),
            hovermode='x unified'
        )
        
        return dcc.Graph(figure=fig, style={'height': '100%'})
    
    elif viz_type == 'wait_comparison':
        # Wait time comparison
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=wait_data['time'], 
            y=wait_data['avg_wait_time_baseline'],
            name='Baseline Strategy',
            line=dict(color=COLORS['baseline'], width=2)
        ))
        
        fig.add_trace(go.Scatter(
            x=wait_data['time'], 
            y=wait_data['avg_wait_time_adaptive'],
            name='Rain-Adaptive Strategy',
            line=dict(color=COLORS['adaptive'], width=2)
        ))
        
        # Add rainfall as a separate axis
        fig.add_trace(go.Scatter(
            x=wait_data['time'], 
            y=wait_data['rainfall'],
            name='Rainfall (mm/h)',
            line=dict(color='lightblue', width=1, dash='dot'),
            fill='tozeroy',
            fillcolor='rgba(173, 216, 230, 0.3)',
            yaxis='y2'
        ))
        
        fig.update_layout(
            title='Wait Time Comparison',
            xaxis_title='Time (hours)',
            yaxis_title='Average Wait Time (seconds)',
            yaxis2=dict(
                title='Rainfall (mm/h)',
                titlefont=dict(color='lightblue'),
                tickfont=dict(color='lightblue'),
                overlaying='y',
                side='right'
            ),
            plot_bgcolor=COLORS['plot_bg'],
            paper_bgcolor=COLORS['plot_bg'],
            legend=dict(
                x=0.01,
                y=0.99,
                bgcolor='rgba(255, 255, 255, 0.8)',
                bordercolor='rgba(0, 0, 0, 0.2)',
                borderwidth=1
            ),
            hovermode='x unified'
        )
        
        return dcc.Graph(figure=fig, style={'height': '100%'})
    
    elif viz_type == 'heatmap':
        # Effectiveness Heatmap
        fig = go.Figure(data=go.Heatmap(
            z=spatial_data['effectiveness_score'],
            x=spatial_data['lon'],
            y=spatial_data['lat'],
            colorscale='RdYlGn',
            text=spatial_data['intersection_id'],
            hovertemplate='<b>Intersection:</b> %{text}<br>' +
                         '<b>Effectiveness Score:</b> %{z:.1f}<br>' +
                         '<b>Location:</b> %{y:.4f}, %{x:.4f}<extra></extra>'
        ))
        
        fig.update_layout(
            title='Spatial Effectiveness Heatmap',
            xaxis_title='Longitude',
            yaxis_title='Latitude',
            plot_bgcolor=COLORS['plot_bg'],
            paper_bgcolor=COLORS['plot_bg']
        )
        
        return dcc.Graph(figure=fig, style={'height': '100%'})
    
    elif viz_type == 'rainfall_impact':
        # Rainfall Impact Analysis
        # Create a scatter plot with rainfall on x-axis and improvement on y-axis
        
        # Calculate improvement percentage at each time point
        flow_improvement = ((flow_data['flow_rate_adaptive'] - flow_data['flow_rate_baseline']) / 
                           flow_data['flow_rate_baseline'] * 100)
        
        wait_improvement = ((wait_data['avg_wait_time_baseline'] - wait_data['avg_wait_time_adaptive']) / 
                           wait_data['avg_wait_time_baseline'] * 100)
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=flow_data['rainfall'],
            y=flow_improvement,
            mode='markers',
            name='Traffic Flow Improvement',
            marker=dict(
                size=8,
                color=COLORS['adaptive'],
                opacity=0.7,
                line=dict(width=1, color='white')
            )
        ))
        
        fig.add_trace(go.Scatter(
            x=wait_data['rainfall'],
            y=wait_improvement,
            mode='markers',
            name='Wait Time Improvement',
            marker=dict(
                size=8,
                color=COLORS['baseline'],
                opacity=0.7,
                line=dict(width=1, color='white')
            )
        ))
        
        # Add trendlines
        # Flow improvement trendline
        z = np.polyfit(flow_data['rainfall'], flow_improvement, 1)
        p = np.poly1d(z)
        x_range = np.linspace(min(flow_data['rainfall']), max(flow_data['rainfall']), 100)
        
        fig.add_trace(go.Scatter(
            x=x_range,
            y=p(x_range),
            mode='lines',
            name='Flow Improvement Trend',
            line=dict(color=COLORS['adaptive'], width=2, dash='dash')
        ))
        
        # Wait improvement trendline
        z = np.polyfit(wait_data['rainfall'], wait_improvement, 1)
        p = np.poly1d(z)
        x_range = np.linspace(min(wait_data['rainfall']), max(wait_data['rainfall']), 100)
        
        fig.add_trace(go.Scatter(
            x=x_range,
            y=p(x_range),
            mode='lines',
            name='Wait Improvement Trend',
            line=dict(color=COLORS['baseline'], width=2, dash='dash')
        ))
        
        fig.update_layout(
            title='Impact of Rainfall on System Effectiveness',
            xaxis_title='Rainfall Intensity (mm/h)',
            yaxis_title='Improvement (%)',
            plot_bgcolor=COLORS['plot_bg'],
            paper_bgcolor=COLORS['plot_bg'],
            legend=dict(
                x=0.01,
                y=0.99,
                bgcolor='rgba(255, 255, 255, 0.8)',
                bordercolor='rgba(0, 0, 0, 0.2)',
                borderwidth=1
            ),
            hovermode='closest'
        )
        
        return dcc.Graph(figure=fig, style={'height': '100%'})
    
    elif viz_type == 'intersection_performance':
        # Intersection Performance
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=spatial_data['intersection_id'],
            y=spatial_data['wait_time_improvement'],
            name='Wait Time Improvement (%)',
            marker_color=COLORS['baseline']
        ))
        
        fig.add_trace(go.Bar(
            x=spatial_data['intersection_id'],
            y=spatial_data['throughput_improvement'],
            name='Throughput Improvement (%)',
            marker_color=COLORS['adaptive']
        ))
        
        fig.update_layout(
            title='Performance by Intersection',
            xaxis_title='Intersection ID',
            yaxis_title='Improvement (%)',
            barmode='group',
            plot_bgcolor=COLORS['plot_bg'],
            paper_bgcolor=COLORS['plot_bg'],
            legend=dict(
                x=0.01,
                y=0.99,
                bgcolor='rgba(255, 255, 255, 0.8)',
                bordercolor='rgba(0, 0, 0, 0.2)',
                borderwidth=1
            )
        )
        
        return dcc.Graph(figure=fig, style={'height': '100%'})
    
    else:
        return html.Div("Visualization type not implemented.")

# Callback to update key metrics
@app.callback(
    [Output('metric-flow', 'children'),
     Output('metric-wait', 'children'),
     Output('metric-speed', 'children'),
     Output('metric-effectiveness', 'children')],
    [Input('stored-data', 'data'),
     Input('time-slider', 'value')]
)
def update_key_metrics(data, time_range):
    if not data:
        return ["N/A", "N/A", "N/A", "N/A"]
    
    # Filter by time range
    flow_data = pd.DataFrame(data['flow_data'])
    wait_data = pd.DataFrame(data['wait_data'])
    spatial_data = pd.DataFrame(data['spatial_data'])
    
    flow_data = flow_data[(flow_data['hour'] >= time_range[0]) & (flow_data['hour'] <= time_range[1])]
    wait_data = wait_data[(wait_data['hour'] >= time_range[0]) & (wait_data['hour'] <= time_range[1])]
    
    # Calculate metrics
    flow_improvement = (flow_data['flow_rate_adaptive'].mean() - flow_data['flow_rate_baseline'].mean()) / flow_data['flow_rate_baseline'].mean() * 100
    
    wait_reduction = (wait_data['avg_wait_time_baseline'].mean() - wait_data['avg_wait_time_adaptive'].mean()) / wait_data['avg_wait_time_baseline'].mean() * 100
    
    # Calculate speed improvement (simulated)
    speed_improvement = 12.5  # In reality, would be calculated from simulation data
    
    # Calculate system effectiveness score
    effectiveness_score = spatial_data['effectiveness_score'].mean()
    
    return [
        f"+{flow_improvement:.1f}%",
        f"-{wait_reduction:.1f}%",
        f"+{speed_improvement:.1f}%",
        f"{effectiveness_score:.1f}"
    ]

# Callback to update time analysis tab
@app.callback(
    Output('time-analysis', 'children'),
    [Input('stored-data', 'data'),
     Input('viz-type', 'value'),
     Input('time-slider', 'value')]
)
def update_time_analysis(data, viz_type, time_range):
    if not data:
        return html.Div("No data available.")
    
    # Filter by time range
    flow_data = pd.DataFrame(data['flow_data'])
    wait_data = pd.DataFrame(data['wait_data'])
    
    flow_data = flow_data[(flow_data['hour'] >= time_range[0]) & (flow_data['hour'] <= time_range[1])]
    wait_data = wait_data[(wait_data['hour'] >= time_range[0]) & (wait_data['hour'] <= time_range[1])]
    
    # Calculate improvement over time
    flow_data['improvement'] = ((flow_data['flow_rate_adaptive'] - flow_data['flow_rate_baseline']) / 
                               flow_data['flow_rate_baseline'] * 100)
    
    wait_data['improvement'] = ((wait_data['avg_wait_time_baseline'] - wait_data['avg_wait_time_adaptive']) / 
                               wait_data['avg_wait_time_baseline'] * 100)
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=flow_data['time'],
        y=flow_data['improvement'],
        name='Traffic Flow Improvement',
        line=dict(color=COLORS['adaptive'], width=2)
    ))
    
    fig.add_trace(go.Scatter(
        x=wait_data['time'],
        y=wait_data['improvement'],
        name='Wait Time Reduction',
        line=dict(color=COLORS['baseline'], width=2)
    ))
    
    # Add rainfall as a separate axis
    fig.add_trace(go.Scatter(
        x=flow_data['time'], 
        y=flow_data['rainfall'],
        name='Rainfall (mm/h)',
        line=dict(color='lightblue', width=1, dash='dot'),
        fill='tozeroy',
        fillcolor='rgba(173, 216, 230, 0.3)',
        yaxis='y2'
    ))
    
    fig.update_layout(
        title='Improvement Percentage Over Time',
        xaxis_title='Time (hours)',
        yaxis_title='Improvement (%)',
        yaxis2=dict(
            title='Rainfall (mm/h)',
            titlefont=dict(color='lightblue'),
            tickfont=dict(color='lightblue'),
            overlaying='y',
            side='right'
        ),
        plot_bgcolor=COLORS['plot_bg'],
        paper_bgcolor=COLORS['plot_bg'],
        legend=dict(
            x=0.01,
            y=0.99,
            bgcolor='rgba(255, 255, 255, 0.8)',
            bordercolor='rgba(0, 0, 0, 0.2)',
            borderwidth=1
        ),
        hovermode='x unified'
    )
    
    return dcc.Graph(figure=fig, style={'height': '100%'})

# Callback to update spatial analysis tab
@app.callback(
    Output('spatial-analysis', 'children'),
    [Input('stored-data', 'data'),
     Input('viz-type', 'value')]
)
def update_spatial_analysis(data, viz_type):
    if not data:
        return html.Div("No data available.")
    
    spatial_data = pd.DataFrame(data['spatial_data'])
    
    fig = go.Figure()
    
    # Create a scatter plot on a map
    fig.add_trace(go.Scattermapbox(
        lat=spatial_data['lat'],
        lon=spatial_data['lon'],
        mode='markers',
        marker=dict(
            size=spatial_data['effectiveness_score'] / 2,
            color=spatial_data['effectiveness_score'],
            colorscale='RdYlGn',
            showscale=True,
            colorbar=dict(title='Effectiveness Score'),
            opacity=0.8
        ),
        text=spatial_data['intersection_id'],
        hoverinfo='text',
        hovertemplate='<b>Intersection:</b> %{text}<br>' +
                     '<b>Effectiveness Score:</b> %{marker.color:.1f}<br>' +
                     '<b>Wait Time Improvement:</b> %{customdata[0]:.1f}%<br>' +
                     '<b>Throughput Improvement:</b> %{customdata[1]:.1f}%<extra></extra>',
        customdata=np.stack((
            spatial_data['wait_time_improvement'], 
            spatial_data['throughput_improvement']
        ), axis=1)
    ))
    
    fig.update_layout(
        title='Spatial Distribution of System Effectiveness',
        mapbox=dict(
            style="open-street-map",
            center=dict(lat=spatial_data['lat'].mean(), lon=spatial_data['lon'].mean()),
            zoom=12
        ),
        margin=dict(l=0, r=0, t=30, b=0)
    )
    
    return dcc.Graph(figure=fig, style={'height': '100%'})

# Callback to update rainfall analysis tab
@app.callback(
    Output('rainfall-analysis', 'children'),
    [Input('stored-data', 'data'),
     Input('viz-type', 'value'),
     Input('time-slider', 'value')]
)
def update_rainfall_analysis(data, viz_type, time_range):
    if not data:
        return html.Div("No data available.")
    
    # Filter by time range
    flow_data = pd.DataFrame(data['flow_data'])
    wait_data = pd.DataFrame(data['wait_data'])
    
    flow_data = flow_data[(flow_data['hour'] >= time_range[0]) & (flow_data['hour'] <= time_range[1])]
    wait_data = wait_data[(wait_data['hour'] >= time_range[0]) & (wait_data['hour'] <= time_range[1])]
    
    # Group by rainfall intensity
    rainfall_bins = [0, 0.5, 2, 5, 10, float('inf')]
    rainfall_labels = ['No Rain (0mm)', 'Light (0-2mm)', 'Moderate (2-5mm)', 'Heavy (5-10mm)', 'Extreme (>10mm)']
    
    flow_data['rainfall_category'] = pd.cut(flow_data['rainfall'], bins=rainfall_bins, labels=rainfall_labels)
    wait_data['rainfall_category'] = pd.cut(wait_data['rainfall'], bins=rainfall_bins, labels=rainfall_labels)
    
    # Calculate metrics by rainfall category
    flow_grouped = flow_data.groupby('rainfall_category').agg({
        'flow_rate_baseline': 'mean',
        'flow_rate_adaptive': 'mean'
    }).reset_index()
    
    wait_grouped = wait_data.groupby('rainfall_category').agg({
        'avg_wait_time_baseline': 'mean',
        'avg_wait_time_adaptive': 'mean'
    }).reset_index()
    
    # Calculate improvements
    flow_grouped['flow_improvement'] = ((flow_grouped['flow_rate_adaptive'] - flow_grouped['flow_rate_baseline']) / 
                                       flow_grouped['flow_rate_baseline'] * 100)
    
    wait_grouped['wait_improvement'] = ((wait_grouped['avg_wait_time_baseline'] - wait_grouped['avg_wait_time_adaptive']) / 
                                       wait_grouped['avg_wait_time_baseline'] * 100)
    
    # Prepare bar chart
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=flow_grouped['rainfall_category'],
        y=flow_grouped['flow_improvement'],
        name='Traffic Flow Improvement',
        marker_color=COLORS['adaptive']
    ))
    
    fig.add_trace(go.Bar(
        x=wait_grouped['rainfall_category'],
        y=wait_grouped['wait_improvement'],
        name='Wait Time Reduction',
        marker_color=COLORS['baseline']
    ))
    
    fig.update_layout(
        title='System Effectiveness by Rainfall Intensity',
        xaxis_title='Rainfall Category',
        yaxis_title='Improvement (%)',
        barmode='group',
        plot_bgcolor=COLORS['plot_bg'],
        paper_bgcolor=COLORS['plot_bg'],
        legend=dict(
            x=0.01,
            y=0.99,
            bgcolor='rgba(255, 255, 255, 0.8)',
            bordercolor='rgba(0, 0, 0, 0.2)',
            borderwidth=1
        )
    )
    
    return dcc.Graph(figure=fig, style={'height': '100%'})

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)