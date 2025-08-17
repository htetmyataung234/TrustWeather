import base64
from flask import Flask, render_template, redirect, url_for,request,flash,session
from pydantic import BaseModel
import pytz
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
from weather_data_scrapping import *
from wrangle import *
from statsmodels.tsa.arima.model import ARIMA
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
import pickle
from datetime import datetime, timedelta,time
from sklearn.ensemble import AdaBoostClassifier
import os
import json
import time
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import base64
from flask_mail import Mail, Message
import uuid
from pymongo import MongoClient
import pymongo

MODEL_UPDATE_INTERVAL = timedelta(days=1)  # Retrain model every day
cached_df = None
last_execution_time = None
model_fit = None
app = Flask(__name__, static_folder="assets")
app.secret_key = os.getenv('APP_SECRET_KEY')
# Replace the connection string with your own MongoDB connection string
connection_string = os.getenv('MONGO_CONNECTION_STRING')
# Create a MongoDB client
client = MongoClient(connection_string)

# Access a specific database
db = client["weather_forecast"]


def load_df():
    global cached_df, last_execution_time
    current_time = datetime.now()
    one_year_ago = current_time - timedelta(days=365)
    collection = db["weather_data"]

    # Check if the collection is empty
    if collection.estimated_document_count() == 0:
        # First time fetching and inserting a full year's weather data
        df = fetch_and_wrangle_weather_data(os.getenv('OPEN_WEATHER_API_KEY'), 16.8661, 96.1951)
        if not df.empty:
            df.reset_index(inplace=True)
            df['dt'] = pd.to_datetime(df['dt'])      
            data_dict = df.to_dict("records")
            # Insert full data into the collection
            collection.insert_many(data_dict)
            print(f"Inserted {len(data_dict)} records for the first time.")
        else:
            print("No data to insert into the collection.")
    else:
        # Fetch the latest timestamp in the collection
        last_record = collection.find_one({}, sort=[("dt", -1)])
        last_modified_time = int(last_record["dt"].timestamp())

        # Calculate the next day's timestamp
        next_day_timestamp = last_modified_time + (3600 * 24)
        current_timestamp = int(current_time.timestamp())

        # Fetch and update data daily
        if next_day_timestamp <= current_timestamp:
            # Fetch historical weather data for the next day
            historical_data = get_historical_weather(
                os.getenv('OPEN_WEATHER_API_KEY'), 16.8661, 96.1951, next_day_timestamp, current_timestamp
            )
            # Use your wrangle_json function here to convert the fetched JSON data to a DataFrame
            df = wrangle_json(historical_data)
            if not df.empty:
                df.reset_index(inplace=True)
                df['dt'] = pd.to_datetime(df['dt'])                
                df['dt'] = pd.to_datetime(df['dt'], utc=True).dt.tz_convert(timezone.utc)
                data_dict = df.to_dict("records")
                # Insert the new data into the collection
                collection.insert_many(data_dict)
                print(f"Inserted {len(data_dict)} records for the new day.")
            else:
                print("No new data to insert.")
        else:
            print("Data is already up-to-date.")

    # Retrieve and cache the updated data
    df = pd.DataFrame(list(collection.find()))
    if not df.empty:
        df['dt'] = pd.to_datetime(df['dt']) 
        df.set_index('dt', inplace=True)
        cached_df = df
        last_execution_time = current_time
        return df
    else:
        print("No data found in the collection.")
        return None
    
def load_forecast_df():
    api_key = os.getenv('OPEN_WEATHER_API_KEY')
    # lat and lon for Yangon
    lat = 16.8661
    lon = 96.1951        
    df = get_forecast_data()
    df = wrangle_json(df)
    yangon_tz = pytz.timezone('Asia/Yangon')
    current_time = datetime.now(yangon_tz).replace(minute=0, second=0, microsecond=0)
    
    # Filter the DataFrame to include only rows with a datetime index before the current hour
    df = df[df.index > current_time]   
    
    return df

def get_daily_forecast_data(db = db):    
    tz = pytz.timezone('Asia/Yangon')
    db = db["weatherforecast"]
    # Get the current time in the specified timezone
    current_time = datetime.now(tz)

    last_24_hours = current_time - timedelta(hours=24)
    recent_data = db.find_one({"timestamp": {"$gte": last_24_hours}})
    print("hit before loop")
    if recent_data:
        # If data exists within the last 24 hours, return it
        print("recent_data", recent_data['data'])
        return recent_data['data']
    else:
        # Fetch new data
        data = get_daily_forecast(os.getenv('OPEN_WEATHER_API_KEY'), 16.8661, 96.1951)['list']
        temps = [int(round(((item['temp']['min'] + item['temp']['max']) / 2) - 273.15, 0)) for item in data]
        feel_temps = [int(round(((item['feels_like']['day']+item['feels_like']['night']+ item['feels_like']['eve']+item['feels_like']['morn'])/4)- 273.15, 0))for item in data]
        dt_values = [datetime.utcfromtimestamp(item['dt']).strftime('%b %d') for item in data]
        weather_main = [item['weather'][0]['main'] for item in data]
        speed = [item['speed'] for item in data]
        humidity = [item['humidity'] for item in data]
        result = [
            {"temp": temp, "feel_likes" : feel_temps, "time": dt, "weather": weather,"speed" : speed , "humidity" : humidity}
            for temp,feel_temps, dt, weather, speed, humidity in zip(temps,feel_temps, dt_values, weather_main,speed,humidity)
        ]

        # Insert new data with a timestamp
        db.insert_one({"timestamp": current_time, "data": result})
        print("hit")
        return result


def save_uv_index_data():
    file_path = 'uv_index.json'
    tz = pytz.timezone('Asia/Yangon')

    # Get the current time in the specified timezone
    current_time = datetime.now(tz)
    current_time_iso = current_time.isoformat()

    # Check if the file exists and its modification time
    if os.path.exists(file_path):
        last_modified_time = os.path.getmtime(file_path)
        current_time = time.time()
        
        # If the file was modified within the last hour, do not update
        if current_time - last_modified_time < 3600:
            print("Data was updated within the last hour. Skipping update.")
            return
    
    # Fetch the UV index data
    url = 'https://api.openuv.io/api/v1/uv'
    headers = {
        'x-access-token': os.getenv('OPENUV_API_KEY')
    }
    params = {
        'lat': 16.8661,
        'lng': 96.1951,
        'alt': 100,
        'dt': ''
    }
    
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        uv_index = response.json()['result']['uv']
        with open(file_path, 'w') as file:
            json.dump({'uv_index': uv_index}, file)
    else:
        response.raise_for_status()

def get_uv_index_value():
    file_path = 'uv_index.json'
    
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            data = json.load(file)
            return data.get('uv_index')
    else:
        print("UV index data not available.")
        return None

def save_model(model, filename):
    with open(filename, 'wb') as file:
        pickle.dump(model, file)

def load_model(filename):
    with open(filename, 'rb') as file:
        return pickle.load(file)

def predict_temperature():
    global model_fit, last_trained
    
    yangon_tz = pytz.timezone('Asia/Yangon')
    current = datetime.now(yangon_tz).replace(minute=0, second=0, microsecond=0)
    
    # Check if the model has already been trained for the current hour
    if 'last_trained' in globals() and last_trained == current:
        with open('temperature_predictions.json', 'r') as file:
            temperature_dict = json.load(file)
        return temperature_dict
    
    collection = db['weather_data']
    
    # Fetch data from MongoDB
    data = list(collection.find())
    df = wrangle_json(data)
    
    # Ensure the DataFrame has the correct datetime index and temperature column
    df['dt'] = pd.to_datetime(df['dt'])
    df.set_index('dt', inplace=True)
    df = df.asfreq('H')  # Set frequency to hourly
    df['main_temp'] = df['main_temp'] - 273.15  # Convert from Kelvin to Celsius
    
    order = (3, 0, 3)
    model = ARIMA(df['main_temp'], order=order)
    model_fit = model.fit()
    last_trained = current
    
    # Make a prediction
    prediction = model_fit.forecast(steps=168)
    if not isinstance(prediction.index, pd.DatetimeIndex):
        prediction.index = pd.to_datetime(prediction.index)

    # Localize the timezone to 'Asia/Yangon'
    prediction.index = prediction.index.tz_localize('UTC').tz_convert('Asia/Yangon')
    prediction = prediction[prediction.index+timedelta(minutes=30) > current]
    
    temperature_dict = [
        {"time": (index.strftime("%I:%M%p")), "temperature": int(round(value, 0))}
        for index, value in prediction.items()
        if index > current
    ]
    
    
    # Save the predictions to a file
    with open('temperature_predictions.json', 'w') as file:
        json.dump(temperature_dict, file)
    
    return temperature_dict

def get_current_weather_data():
    return get_current_weather(os.getenv('OPEN_WEATHER_API_KEY'), 16.8661, 96.1951)

def get_forecast_data():
    return get_forecast_weather(os.getenv('OPEN_WEATHER_API_KEY'), 16.8661, 96.1951)

def is_model_outdated(filename, interval):
    if not os.path.exists(filename):
        return True
    last_modified_time = datetime.fromtimestamp(os.path.getmtime(filename))
    return datetime.now() - last_modified_time > interval

def predict_weather():    
    df = load_df()
    features = ['main_humidity','main_temp','clouds_all']
    target = 'weather_main'
    X = df[features]
    y = df[target]
    adaboost = AdaBoostClassifier(n_estimators=10, learning_rate=1.0)
    adaboost.fit(X, y)
    forecast_df = load_forecast_df()
    forecast_df = forecast_df[features] 
    predictions = adaboost.predict(forecast_df)
    return predictions

def total_prediction(db = db):
    temp = predict_temperature()
    weather = predict_weather()
    combined_predictions = []

    for temp, weather in zip(temp, weather):
        time_str = temp['time']
        time_format = "%I:%M%p"  # Adjust this format to match your time string format
        time_obj = datetime.strptime(time_str, time_format)
        
        # Add 30 minutes to the datetime object
        adjusted_time = time_obj + timedelta(minutes=30)
        

        combined_predictions.append({
        "time": adjusted_time.strftime(time_format),
        "temperature": temp["temperature"],
        "weather": weather
        
        })

    collection = db["predictions"]

    # Define the timezone for GMT+6:30
    tz = pytz.timezone('Asia/Yangon')

    # Get the current time in the specified timezone  
    current_time = datetime.now(tz)

    # Check if there is any data in the last hour
    last_hour = current_time - timedelta(hours=1)
    recent_data = collection.find_one({"timestamp": {"$gte": last_hour}})
    print("hit")
    if recent_data:
        # If data exists within the last hour, return it
        print("hit recent")
        return recent_data['data']
    else:
        # Fetch new predictions
        print("hit else")
        predictions = combined_predictions

        # Insert new data with a timestamp
        collection.insert_one({"timestamp": current_time, "data": predictions})

        return combined_predictions


def send_email(name, email, subject, message):
    sender_email = os.getenv('MAIL_SENDER_EMAIL')
    receiver_email = email
    password = os.getenv('APPLICATION_PASSWORD')
    # Create the email content
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = f"Thanks for contacting us, {name}!"
    current_weather_data = get_current_weather_data()
    current_temperature = int(round(current_weather_data["main"]["temp"] - 273.15, 0))
    current_feels_like = int(round(current_weather_data["main"]["feels_like"] - 273.15, 0))
    current_humidity = current_weather_data["main"]["humidity"]
    current_wind_speed = current_weather_data["wind"]["speed"]
    current_weather = current_weather_data["weather"][0]["main"]
    uvindex = get_uv_index_value()
    # Creating the body of the email with weather details
    body = (
        f"We have received your message with the following details:\n\n"
        f"Subject : {subject}\n"
        f"Message : {message}\n\n"
        f"Current Weather Report :\n"
        f"Temperature : {current_temperature} degrees Celsius\n"
        f"Feels Like : {current_feels_like} degrees Celsius\n"
        f"Humidity : {current_humidity}%\n"
        f"Wind Speed : {current_wind_speed} m/s\n"
        f"Weather : {current_weather}\n"
        f"UVI : {uvindex}\n\n"
        f"We will get back to you as soon as possible.\n\n"
        f"Best regards,\nTrust Weather Team"
    )

    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    # Connect to the SMTP server and send the email
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(sender_email, password)
    server.sendmail(sender_email, receiver_email, msg.as_string())

    server.quit()

@app.route("/", methods=["GET", "POST"])
def entry():
    return redirect(url_for("index"))

@app.route("/home", methods=["GET", "POST"])
def home():
    return redirect("/dashboard.html")
   
@app.route("/index.html", methods=["GET","POST"])
def index():
    save_uv_index_data()
    current_weather_data = get_current_weather_data()
    current_temperature = int(round(current_weather_data["main"]["temp"] - 273.15,0))
    current_feels_like = int(round(current_weather_data["main"]["feels_like"] - 273.15,0))
    current_humidity = current_weather_data["main"]["humidity"]
    current_wind_speed = current_weather_data["wind"]["speed"]
    current_weather = current_weather_data["weather"][0]["main"]
    predictions = total_prediction()[:12]
    daily_forecast = get_daily_forecast_data()
    return render_template("index.html",
                           time=time,
                           predictions = predictions,
                           current_temperature=current_temperature, 
                           current_feels_like=current_feels_like, 
                           current_humidity=current_humidity, 
                           current_wind_speed=current_wind_speed, 
                           current_weather= current_weather,
                           daily_forecast= daily_forecast) 

@app.route("/dashboard.html", methods=["GET","POST"])
def dashboard():
    save_uv_index_data()
    current_weather_data = get_current_weather_data()
    current_temperature = int(round(current_weather_data["main"]["temp"] - 273.15,0))
    current_feels_like = int(round(current_weather_data["main"]["feels_like"] - 273.15,0))
    current_humidity = current_weather_data["main"]["humidity"]
    current_wind_speed = current_weather_data["wind"]["speed"]
    current_weather = current_weather_data["weather"][0]["main"]
    current_weather_description = current_weather_data["weather"][0]["description"]
    predictions = total_prediction()
    daily_forecast = get_daily_forecast_data()
    return render_template("dashboard.html",
                           predictions = predictions,
                           current_weather_description = current_weather_description,
                           current_temperature=current_temperature, 
                           current_feels_like=current_feels_like, 
                           current_humidity=current_humidity, 
                           current_wind_speed=current_wind_speed, 
                           current_weather= current_weather,
                           daily_forecast= daily_forecast) 
    
@app.route("/dashboard.html", methods=["GET","POST"])
def overview():
    save_uv_index_data()
    current_weather_data = get_current_weather_data()
    current_temperature = int(round(current_weather_data["main"]["temp"] - 273.15,0))
    current_feels_like = int(round(current_weather_data["main"]["feels_like"] - 273.15,0))
    current_humidity = current_weather_data["main"]["humidity"]
    current_wind_speed = current_weather_data["wind"]["speed"]
    current_weather = current_weather_data["weather"][0]["main"]
    uv_index = round(get_uv_index_value(),2)
    return render_template("overview.html",
                           time=time,
                           current_temperature=current_temperature, 
                           current_feels_like=current_feels_like, 
                           current_humidity=current_humidity, 
                           current_wind_speed=current_wind_speed, 
                           current_weather= current_weather,
                           uv_index=uv_index)

@app.route("/feelslike.html", methods=["GET","POST"])
def feelslike():    
    current_weather_data = get_current_weather_data()     
    current_feels_like = int(round(current_weather_data["main"]["feels_like"] - 273.15,0))       
    current_temperature = int(round(current_weather_data["main"]["temp"] - 273.15,0)) 
    daily_forecast = get_daily_forecast_data()
    return render_template("feelslike.html", current_feels_like=current_feels_like, daily_forecast = daily_forecast, current_temperature= current_temperature)

@app.route("/windspeed.html", methods=["GET","POST"])
def windspeed():
    current_weather_data = get_current_weather_data()
    current_wind_speed = current_weather_data["wind"]["speed"]    
    daily_forecast = get_daily_forecast_data()
    return render_template("windspeed.html", current_wind_speed=current_wind_speed, daily_forecast = daily_forecast)

@app.route("/humidity.html", methods=["GET","POST"])
def humidity():
    current_weather_data = get_current_weather_data()
    current_humidity = current_weather_data["main"]["humidity"]
    daily_forecast = get_daily_forecast_data()[1:]
    return render_template("humidity.html", current_humidity=current_humidity, daily_forecast = daily_forecast)

@app.route("/uvindex.html", methods=["GET","POST"])
def uvindex():
    save_uv_index_data()
    uv_index = round(get_uv_index_value(),2)
    return render_template("uvindex.html", uv_index=uv_index)

@app.route("/hourly.html", methods=["POST","GET"])
def predict():
    save_uv_index_data()
    predictions = total_prediction()
    time = predictions.index
    current_weather_data = get_current_weather_data()
    current_temperature = int(round(current_weather_data["main"]["temp"] - 273.15,0))
    current_feels_like = int(round(current_weather_data["main"]["feels_like"] - 273.15,0))
    current_humidity = current_weather_data["main"]["humidity"]
    current_wind_speed = current_weather_data["wind"]["speed"]
    current_weather = current_weather_data["weather"][0]["main"]

    return render_template("hourly.html", 
                           predictions=predictions, 
                           time=time,
                           current_temperature=current_temperature, 
                           current_feels_like=current_feels_like, 
                           current_humidity=current_humidity, 
                           current_wind_speed=current_wind_speed, 
                           current_weather= current_weather)

@app.route("/3days_forecast.html", methods=["GET"])    
def daily_forecast():
    daily_forecast = get_daily_forecast_data()
    return render_template("3days_forecast.html", daily_forecast=daily_forecast)  

@app.route("/pages-contact.html",methods=["GET","POST"])
def contact():
    if request.method == "POST":
        return submit_form()
    return render_template("pages-contact.html")

def submit_form():
    collection = db["user_contact"]
    name = request.form['name']
    email = request.form['email']
    subject = request.form['subject']
    message = request.form['message']
    
    # Read existing data
    try:
    # Find the highest cid in the collection
        highest_record = collection.find_one(sort=[("cid", pymongo.DESCENDING)])
        if highest_record:
            uid = highest_record["cid"] + 1
        else:
            uid = 1
    except Exception as e:
        uid = 1
        print(f"An error occurred: {e}")    
    
    # Create a new entry
    new_entry = {
        "cid": uid,
        "name": name,
        "email": email,
        "subject": subject,
        "message": message
    }
    
    collection.insert_one(new_entry)
    
    # Optionally, send an email
    send_email(name, email, subject, message)
    
    # Flash a success message
    flash("Form submitted successfully!", "success")
    
    return redirect(url_for("contact"))

@app.route("/report.html", methods=["GET", "POST"])
def report():
    collection = db["user_report"]
    if request.method == "POST":
        # Retrieve form data
        form_data = request.form.to_dict()

        # Generate a unique ID
        uid = collection.count_documents({}) + 1

        # Add UID to form data
        form_data = {"rid": uid, **form_data}

        # Save data to MongoDB collection
        collection.insert_one(form_data)

    return render_template("report.html")

#Admin Part Start Here

@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username == "admin" and password == "admin":
            session['logged_in'] = True
            return redirect(url_for("admin_index"))
        else:
            flash("Invalid username or password", "error")
            return redirect(url_for("admin_login"))

    return render_template("admin_login.html")  # Render login page for GET requests

@app.route("/admin_index.html", methods=["GET", "POST"])
def admin_index():
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))

    save_uv_index_data()
    current_weather_data = get_current_weather_data()
    current_temperature = int(round(current_weather_data["main"]["temp"] - 273.15, 0))
    current_feels_like = int(round(current_weather_data["main"]["feels_like"] - 273.15, 0))
    current_humidity = current_weather_data["main"]["humidity"]
    current_wind_speed = current_weather_data["wind"]["speed"]
    current_weather = current_weather_data["weather"][0]["main"]
    uv_index = round(get_uv_index_value(), 2)
    return render_template("admin_index.html",
                           time=time,
                           current_temperature=current_temperature, 
                           current_feels_like=current_feels_like, 
                           current_humidity=current_humidity, 
                           current_wind_speed=current_wind_speed, 
                           current_weather=current_weather,
                           uv_index=uv_index)

@app.route("/logout", methods=["POST"])
def logout():
    session.pop('logged_in', None)
    return redirect(url_for("admin_login"))

@app.route("/admin_user_report.html",methods=["GET","POST"])
def admin_user_report():    
    collection = db["user_report"]
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))

    if request.method == "GET":
        try:
            data = list(collection.find())
        except Exception as e:
            data = []
            flash(f"An error occurred: {e}", "danger")
        return render_template("admin_user_report.html", data=data)
    
    if request.method == "POST":
        action = request.form.get("action")
        
        try:
            data = list(collection.find())
        except Exception as e:
            data = []
            flash(f"An error occurred: {e}", "danger")

        if action == "search":
            query = request.form.get("query").lower()
            filtered_data = [
                item for item in data 
                if any(query in str(value).lower() for value in item.values())
            ]
            return render_template("admin_user_report.html", data=filtered_data)
        
        elif action == "delete":
            rid = request.form.get("rid")
            if rid is not None:
                try:
                    collection.delete_one({"rid": int(rid)})
                    flash("Contact deleted successfully!", "success")
                except Exception as e:
                    flash(f"An error occurred: {e}", "danger")
            return redirect(url_for("admin_user_report"))

        else:
            # Handle other actions if necessary
            pass

@app.route("/admin_customer_contact.html",methods=["GET","POST"])
def admin_customer_contact():    
    collection = db["user_contact"]
    if request.method == "GET":
        try:
            data = list(collection.find())
        except Exception as e:
            data = []
            flash(f"An error occurred: {e}", "danger")
        return render_template("admin_customer_contact.html", data=data)
    
    if request.method == "POST":
        action = request.form.get("action")

        try:
            data = list(collection.find())
        except Exception as e:
            data = []
            flash(f"An error occurred: {e}", "danger")

        if action == "search":
            query = request.form.get("query").lower()
            filtered_data = [
                item for item in data 
                if any(query in str(value).lower() for value in item.values())
            ]
            return render_template("admin_customer_contact.html", data=filtered_data)
        
        elif action == "delete":
            cid = request.form.get("cid")
            if cid is not None:
                try:
                    collection.delete_one({"cid": int(cid)})
                    flash("Contact deleted successfully!", "success")
                except Exception as e:
                    flash(f"An error occurred: {e}", "danger")
            return redirect(url_for("admin_customer_contact"))

        else:
            # Handle other actions if necessary
            pass

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=39420)
