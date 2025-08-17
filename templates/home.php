<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Document</title>
  <script>
    function updateTime() {
      var today = new Date();
      var day = today.getDate();
      var month = today.getMonth();
      var year = today.getFullYear();
      var hours = today.getHours();
      var minutes = today.getMinutes();
      var monthNames = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
      ];
    
      // Adding leading zero to minutes and seconds if they are less than 10
      minutes = minutes < 10 ? '0' + minutes : minutes;
    
      var formattedDate = day + " " + monthNames[month] + " " + year + " " + hours + ":" + minutes;
      document.getElementById("datetime").innerHTML = formattedDate;
      setTimeout(updateTime, 100000); // Call the function every 100 seconds 
      const body = document.body;  // Select the element to change background
      var hour = today.getHours();
      if (hour >= 6 && hour < 14) {
        body.style.background = "url('./assets/Morning.png')";
        body.style.backgroundSize = 'cover';
      } else if (hour >= 14 && hour < 19) {
        body.style.background = "url('./assets/Evening.png')";
        body.style.backgroundSize = "cover";
      } else {
        body.style.background = "url('./assets/Night.png')";
        body.style.backgroundSize = "cover";
      }
    }
  </script>
  
  

  <link rel="stylesheet" href="style1.css" />
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css" integrity="sha512-SnH5WK+bZxgPHs44uWIX+LLJAJ9/2PkPKZ5QiAj6Ta86w+fsb2TkcmfRyVX3pBnMFcV7oQPJkl9QevSCWr3W6A==" crossorigin="anonymous" referrerpolicy="no-referrer" />
</head>
<body style = "overflow: hidden;">
  <div class="description">
    <h1 style = "font-size : 40px">Yangon</h1>
    <h3 id="datetime"></h1>
    <script>updateTime();</script>
  </div>

  <?php
  /**
   * Converts Kelvin to Celsius
   *
   * @param float $kelvin Temperature in Kelvin
   * @return float Temperature in Celsius
   */
  function kelvinToCelsius($kelvin) {
      return $kelvin - 273.15;
  }
  
  // Define API request URL and API key
  $API_KEY = "b38b634aa2ef285315b9ea6197dffea3";
  $lat = 16.8409; // Latitude for Yangon
  $lon = 96.1735; // Longitude for Yangon
  $apiUrl = "https://api.openweathermap.org/data/2.5/weather?lat=$lat&lon=$lon&appid=$API_KEY";
  //https://api.openweathermap.org/data/2.5/weather?lat=16.8409&lon=96.1735&appid=b38b634aa2ef285315b9ea6197dffea3
  //https://pro.openweathermap.org/data/2.5/forecast/hourly?lat=16.8409&lon=96.1735&appid=b38b634aa2ef285315b9ea6197dffea3
  
  // Initialize stream context
  $context = stream_context_create([
    'http' => [
      'method' => 'GET',
      'header' => "Accept: application/json\r\n",
    ]
  ]);
  
  // Get the response from the API
  $response = file_get_contents($apiUrl, false, $context);
  
  // Check for errors
  if ($response === false) {
    echo "Error fetching weather data.";
    exit;
  }
  
  // Decode JSON response
  $weatherData = json_decode($response, true);
  ?>
  <div class="temperature">
    <div class="block_one">
      <div class="col_one"><h1 class = "temp" style = " margin : 0px;"><?php echo round( kelvinToCelsius($weatherData['main']['temp']),0).'°C'; ?></h1></div>
      <div class="col_two">
        <h2 id="tempToggle">|&#176;F</h2>
        <p><?php echo $weatherData["weather"][0]["description"]; ?></p>
      </div>
    </div>
    
    <div class="block_three">
      <img class = "image" src="https://openweathermap.org/img/wn/<?php echo $weatherData['weather'][0]['icon']; ?>@4x.png" alt="weather-icon">
    </div>
    <div class="block_four">
      <p><i class="fa-solid fa-temperature-half"></i>&nbsp;Feels Like: <span class = "temp"><?php echo round(kelvinToCelsius($weatherData['main']['feels_like']),0).'°C'; ?></span></p>
      <p><i class="fa-solid fa-droplet"></i>&nbsp;Humidity: <span><?php echo $weatherData['main']['humidity']; ?>%;</span></p>
    </div>
  </div>
</div>
  
  <!-- <script>
    document.getElementById('tempToggle').addEventListener('click', function() {
      var temperatureElement = document.getElementById('temperature');
      var currentTemp = parseInt(temperatureElement.innerText);
      var currentUnit = temperatureElement.innerText.slice(-1);

      if (currentUnit === 'C') {
        // Convert to Fahrenheit
        var fahrenheitTemp = Math.round((currentTemp * 9/5) + 32);
        temperatureElement.innerText = fahrenheitTemp + '°F';
        document.getElementById('tempToggle').innerHTML = '|&#176;C'; // Update the toggle text to show °C
      } else {
        // Convert to Celsius
        var celsiusTemp = Math.round((currentTemp - 32) * 5/9);
        temperatureElement.innerText = celsiusTemp + '°C';
        document.getElementById('tempToggle').innerHTML = '|&#176;F'; // Update the toggle text to show °F
      }
    });
  </script> -->
  
  <?php
  $apiUrl = "https://pro.openweathermap.org/data/2.5/forecast/hourly?lat=$lat&lon=$lon&appid=$API_KEY";

  // Get the response from the API
  $response = file_get_contents($apiUrl, false, $context);

  // Check for errors
  if ($response === false) {
    echo "Error fetching weather data.";
    exit;
  }

  // Decode JSON response
  $forecastData = json_decode($response, true);

  $currentTimestamp = time() + (33 * 60);

  // Filter forecast data to keep only future hours
  $filteredForecastList = array_filter($forecastData['list'], function ($forecast) use ($currentTimestamp) {
      // Convert forecast timestamp to Unix timestamp for comparison
      $forecastTimestamp = $forecast['dt'];
      return $forecastTimestamp > $currentTimestamp;
  });

  // If you need the filtered list to be reindexed
  $filteredForecastList = $filteredForecastList;

    // Check if the response contains 'list' data and print it
  if (isset($filteredForecastList)) {
    $forecastList = $filteredForecastList;
  } 

  // Get the current minute from the timestamp
  $currentMinute = (int)date('i', $currentTimestamp);
  
  // Check if the current minute is 30
  if ($currentMinute >= 30) {?>
  

  <div class="hourly_forecast">

    <?php
      for($j = 6; $j < 6+24; $j++) { ?>
      
          <div class = "hourly">
    <h1><?php echo date("h:i A", strtotime($forecastList[$j]["dt_txt"])); ?></h1>
    <h1 class = "temp" ><?php echo round(kelvinToCelsius($forecastList[$j]["main"]["temp"]),0).'°C'; ?></h1>
      <img src="https://openweathermap.org/img/wn/<?php echo $forecastList[$j]['weather'][0]['icon']; ?>@4x.png" alt="weather-icon">
      <h1><?php echo $forecastList[$j]["weather"][0]["main"]; ?></h1>
    </div>
    <?php }?>      
  <?php } else {?>
      <?php
    
    for($j = 7; $j < 7+24; $j++) {?>
    <div class = "hourly">
    <h1><?php echo date("h:i A", strtotime($forecastList[$j]["dt_txt"])); ?></h1>
    <h1 class = "temp" ><?php echo round(kelvinToCelsius($forecastList[$j]["main"]["temp"]),0).'°C'; ?></h1>
      <img src="https://openweathermap.org/img/wn/<?php echo $forecastList[$j]['weather'][0]['icon']; ?>@4x.png" alt="weather-icon">
      <h1><?php echo $forecastList[$j]["weather"][0]["main"]; ?></h1>
    </div>
      <?php }}?>

  </div>

  <script>
  document.getElementById('tempToggle').addEventListener('click', function() {
    var temperatureElements = document.getElementsByClassName('temp');

    Array.prototype.forEach.call(temperatureElements, function(temperatureElement) {
        var currentTemp = parseInt(temperatureElement.innerText);
        var currentUnit = temperatureElement.innerText.slice(-1);

        if (currentUnit === 'C') {
            // Convert to Fahrenheit
            var fahrenheitTemp = Math.round((currentTemp * 9/5) + 32);
            temperatureElement.innerText = fahrenheitTemp + '°F';
        } else {
            // Convert to Celsius
            var celsiusTemp = Math.round((currentTemp - 32) * 5/9);
            temperatureElement.innerText = celsiusTemp + '°C';
        }
    });
    // Update the toggle text
    var toggleText = document.getElementById('tempToggle').innerText;
    if (toggleText.includes('C')) {
        document.getElementById('tempToggle').innerHTML = '|&#176;F'; // Update the toggle text to show °F
    } else {
        document.getElementById('tempToggle').innerHTML = '|&#176;C'; // Update the toggle text to show °C
    }
});
  
  </script>

</body>
</html>

