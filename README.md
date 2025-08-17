# WEATHER FORECASTING OF YANGON REGION USING MACHINE LEARNING

## Project Overview

**TrustWeather** is a Flask web application that provides real-time weather data and ML-powered predictions for Yangon. It uses ARIMA models for temperature forecasting and AdaBoost classifiers for weather condition prediction, with data stored in MongoDB and sourced from OpenWeatherMap and OpenUV APIs.

This project was developed as a requirement for my Bachelor's degree.

## Preparation

Change directory to the project folder and use pip to install the required packages:

```bash
pip install -r requirements.txt
```

## Credentials Required
- **`app_secret_key`**: Flask Application Secret Key (can be any value)
- **`mongo_connection_string`**: MongoDB Connection String
- **`open_weather_api_key`**: OpenWeather API Key
- **`openuv_api_key`**: OpenUV API Key (from [openuv.io](https://www.openuv.io))
- **`mail_sender_email`**: Email of the SMTP server owner
- **`application_password`**: Application password for the SMTP server email

## MongoDB Structure
- **Database name**: `weather_forecast`
- **Collections:**
  1. `predictions`
  2. `user_contact`
  3. `user_report`
  4. `weather_data`
  5. `weatherforecast`

## Usage

Make sure to replace all the required credentials and ensure a MongoDB instance is up and running before starting the application.

```bash
py main.py
```

This will run the software in development environment.
