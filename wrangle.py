import pandas as pd
from datetime import datetime, timezone

def wrangle_json(api_data):
    # Extract the 'list' key from the dictionary
    if 'list' in api_data:
        list_data = api_data['list']
    else:
        list_data = api_data  # Load all data if 'list' key does not exist

    # Check if list_data is not empty and contains dictionaries
    if not list_data or not isinstance(list_data, list) or not all(isinstance(item, dict) for item in list_data):
        return pd.DataFrame()  # Return an empty DataFrame or handle the error as needed

    # Convert the list of dictionaries to a DataFrame
    df = pd.DataFrame(list_data)

    # Assuming df is your DataFrame
    if not pd.api.types.is_datetime64_any_dtype(df['dt']):
        df['dt'] = pd.to_datetime(df['dt'], unit='s', utc=True)
        df['dt'] = df['dt'].dt.tz_convert("Asia/Yangon")
        
        df = pd.concat([df, pd.json_normalize(df['main']).add_prefix('main_')], axis=1)
        df = pd.concat([df, pd.json_normalize(df['wind']).add_prefix('wind_')], axis=1)
        df = pd.concat([df, pd.json_normalize(df['clouds']).add_prefix('clouds_')], axis=1)
            
        df['weather'] = df['weather'].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else {})
        df = pd.concat([df, pd.json_normalize(df['weather']).add_prefix('weather_')], axis=1)
        
        # Drop the original nested columns
        df = df.drop(['main', 'wind', 'clouds', 'weather'], axis=1)
        # We can't add this step here because not all JSON data has the 'rain' column
        # Keep in mind that we are dealing with non-structured data
        # df['rain_1h'] = df['rain'].apply(lambda x: x['1h'] if isinstance(x, dict) and '1h' in x else None)  
        df.drop(["main_feels_like", "wind_gust", "weather_id", "weather_icon"], axis=1, inplace=True, errors='ignore')
        df.set_index('dt', inplace=True)
        df = df[~df.index.duplicated()]
        return df
    else:
        return df