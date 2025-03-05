# weather_api.py
import requests
import json
import os
from datetime import datetime

class WeatherAPI:
    def __init__(self, api_key, city):
        self.api_key = api_key
        self.city = city
        self.base_url = "https://api.openweathermap.org/data/2.5/weather"
    
    def get_current_rainfall(self):
        """Get current rainfall intensity in mm/h"""
        params = {
            'q': self.city,
            'appid': self.api_key,
            'units': 'metric'
        }
        
        response = requests.get(self.base_url, params=params)
        data = response.json()
        
        # Extract rainfall data if available
        rain_mm_per_hour = 0
        if 'rain' in data and '1h' in data['rain']:
            rain_mm_per_hour = data['rain']['1h']
        
        return rain_mm_per_hour
    
    def get_rain_category(self):
        """Categorize rainfall intensity"""
        rainfall = self.get_current_rainfall()
        
        if rainfall == 0:
            return "no_rain"
        elif rainfall < 2.5:
            return "light_rain"
        elif rainfall < 7.6:
            return "moderate_rain"
        else:
            return "heavy_rain"