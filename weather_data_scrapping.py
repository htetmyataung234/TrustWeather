import os
import requests
import json
from datetime import time
import datetime
import pandas as pd
from wrangle import wrangle_json
import time

def get_historical_weather(api_key, lat, lon, start, end):
    try:
        base_url = "https://history.openweathermap.org/data/2.5/history/city"
        params = {
            'lat': lat,
            'lon': lon,
            'type': 'hour',
            'start': start,
            'end': end,
            'appid': api_key
        }

        response = requests.get(base_url, params=params)
        response.raise_for_status()  # Check for errors in the HTTP response

        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from API: {e}")
        return None

def get_daily_forecast(api_key, lat, lon):
    try:
        base_url = "https://api.openweathermap.org/data/2.5/forecast/daily"
        params = {
            'lat': lat,
            'lon': lon,
            'appid': api_key
        }

        response = requests.get(base_url, params=params)
        response.raise_for_status()  # Check for errors in the HTTP response

        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from API: {e}")
        return None

def get_onecall(api_key, lat, lon, exclude):
    try:
        base_url = "https://api.openweathermap.org/data/3.0/onecall"
        params = {
            'lat': lat,
            'lon': lon,
            'exclude': exclude,
            'appid': api_key
        }

        response = requests.get(base_url, params=params)
        response.raise_for_status()  # Check for errors in the HTTP response

        return response.json()
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from API: {e}")
        return None



def get_current_weather(api_key, lat, lon):
    try:
        base_url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            'lat': lat,
            'lon': lon,
            'appid': api_key
        }

        response = requests.get(base_url, params=params)
        response.raise_for_status()  # Check for errors in the HTTP response

        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from API: {e}")
        return None

def get_forecast_weather(api_key, lat, lon):
    try:
        base_url = "https://pro.openweathermap.org/data/2.5/forecast/hourly"
        params = {
            'lat': lat,
            'lon': lon,
            'appid': api_key
        }

        response = requests.get(base_url, params=params)
        response.raise_for_status()  # Check for errors in the HTTP response

        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from API: {e}")
        return None


def fetch_and_wrangle_weather_data(api_key, lat, lon, max_api_calls=60, time_interval=1):
    # Get the current date and time
    current_date = datetime.datetime.now()

    # Calculate the timestamp for one year before the current date
    one_year_ago = current_date - datetime.timedelta(days=365)
    start_timestamp = int(one_year_ago.timestamp())

    # Calculate the current timestamp
    end_timestamp = int(current_date.timestamp())

    dfs = []

    for call_num in range(max_api_calls):
        call_start = start_timestamp + call_num * 604800  # 604800 seconds in a week
        call_end = call_start + 604800  # One week interval

        api_data = get_historical_weather(api_key, lat, lon, call_start, call_end)
        if api_data:
            df = wrangle_json(api_data)
            dfs.append(df)
        
        if call_num < max_api_calls - 1:
            print(f"Waiting for {time_interval} seconds before the next API call...")
            print("iteration Number : ",call_num)
            #time.sleep(time_interval)

    return pd.concat(dfs)

if __name__ == "__main__":
    # Replace 'your_api_key' with your actual OpenWeatherMap API key
    api_key = '{open_weather_api_key}'
    
    # Replace with the latitude and longitude of the desired location
    lat = 16.8661
    lon = 96.1951
    
    df = fetch_and_wrangle_weather_data(api_key, lat, lon)
    print(df)
    print(df.info())