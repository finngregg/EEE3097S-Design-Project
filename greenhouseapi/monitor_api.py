# envrioment logger to record:
#                             - Temprature
#                             - Light
#                             - Humidity (output from a pot)

# FNNGRE002
# October 2020
# http://192.168.0.127:8050

# Imports
# for board
import spidev
import time
import os
import RPi.GPIO as GPIO

# for dash
import dash 
from dash.dependencies import Output, Input
import dash_core_components as dcc 
import dash_html_components as html 

# for plotly
import plotly 
import random 
import plotly.graph_objs as go 
from collections import deque 

# for demonstrator
import demo_alert

# Global Variables 
pwm_on = None
LED_on = 13

# Open SPI bus
spi = spidev.SpiDev()
spi.open(0,0)
spi.max_speed_hz=1000000

# Define sensor channels on the MCP3008
light_channel = 0
temp_channel  = 1
humid_channel = 2

# Dash App
app = dash.Dash(__name__) 

X = deque(maxlen = 20) # array to store x values for the x axis
X.append(1) 
  
Y1 = deque(maxlen = 20) # array to store values from the humidity sensor for the y axis
Y1.append(1) 
Y2 = deque(maxlen = 20) # array to store values from the temperature sensor for the y axis
Y2.append(1) 
Y3 = deque(maxlen = 20) # array to store values from the light sensor for the y axis
Y3.append(1) 

# Demonstrator 
demo = demo_alert.api_demonstrator()

# App layout
# creates a main heading and well as the sub heaidngs for the graphs being displayed
app.layout = html.Div(children=[
    html.Div([
        html.H1(children='Smart Agriculture Monitor', style={'text-align': 'center', 'font_size': '30px'})
    ]),
    html.Div([
        html.H2(children='Humidity Sensor', style={'text-align': 'center', 'font_size': '26px'}),
        dcc.Graph(id = 'live-graph1', animate = True) 
    ]),
    html.Div([
        html.H2(children='Temperature Sensor', style={'text-align': 'center', 'font_size': '26px'}),
        dcc.Graph(id = 'live-graph2', animate = True)
    ]),
    html.Div([
        html.H2(children='Light Sensor', style={'text-align': 'center', 'font_size': '26px'}),
        dcc.Graph(id = 'live-graph3', animate = True)
    ]),
    dcc.Interval( 
        id = 'graph-update', 
        interval = 5000, # interval that the graphs will be updated with new data has been set to 5 seconds
        n_intervals = 0
    )
]) 

# Functions
def setup():
  global pwm_on
  # Setup board mode
  GPIO.setmode(GPIO.BCM) 
  GPIO.setwarnings(False)
  # Setup pins    
  GPIO.setup(LED_alert, GPIO.OUT)
  pwm_alert = GPIO.PWM(LED_alert, 100) # sets up the first LED used for alerts
  GPIO.setup(LED_on, GPIO.OUT)
  pwm_on = GPIO.PWM(LED_on, 100) # sets up the first LED used to signal that the system is on
  pwm_on.start(100)

# Function to read SPI data from MCP3008 chip from the specified channel
def ReadChannel(channel):
  adc = spi.xfer2([1,(8+channel)<<4,0])
  data = ((adc[1]&3) << 8) + adc[2]
  return data
 
# Function to convert the analogue data to voltage level
def ConvertVolts(data,places):
  volts = (data * 3.3) / float(1023)
  volts = round(volts,places)
  return volts
 
# Function to calculate temperature
def ConvertTemp(data,places):
  temp = (data - 0.5)/0.01
  temp = round(temp,places)
  return temp 

# Function to calculate relative humidty
def ConvertHumid(data,places):
  humid = (data-0.958)/0.0307
  humid = round(humid,places)
  return humid

@app.callback( 
    Output('live-graph1', 'figure'),
    Output('live-graph2', 'figure'),  
    Output('live-graph3', 'figure'),  
    [ Input('graph-update', 'n_intervals') ] 
) 
def getAll(n):
  # Read the "humidity sensor" data from the pot
  humid_level = ReadChannel(humid_channel)
  humid_volts = ConvertVolts(humid_level,2)
  humid       = ConvertHumid(humid_volts,2)

  # Read the light sensor data
  light_level = ReadChannel(light_channel)
  light_volts = ConvertVolts(light_level,2)
  # light       = ConvertLight(light_volts,2)
 
  # Read the temperature sensor data
  temp_level = ReadChannel(temp_channel)
  temp_volts = ConvertVolts(temp_level,2)
  temp       = ConvertTemp(temp_volts,2)

  # Conditions in order to trigger an alert
  demo_alert.alert(humid,temp)
  
  X.append(X[-1]+5) # adds 5 to the last value in the array and stores it as a new value in the array
  Y1.append(humid) # adds latest humidty value to the array 
  Y2.append(temp) # adds latest temperature value to the array 
  Y3.append(light_level) # adds latest light value to the array 
  
  data1 = plotly.graph_objs.Scatter( x=list(X), y=list(Y1), name='Scatter', mode= 'lines+markers') 
  data2 = plotly.graph_objs.Scatter( x=list(X), y=list(Y2), name='Scatter', mode= 'lines+markers') 
  data3 = plotly.graph_objs.Scatter( x=list(X), y=list(Y3), name='Scatter', mode= 'lines+markers') 

  fig1 = {'data': [data1], 'layout' : go.Layout(xaxis=dict(range=[min(X),max(X)],title='Elapsed Time (s)'),yaxis = dict(range = [min(Y1),max(Y1)],title='Relative Humidity (%)'),)} 
  fig2 = {'data': [data2], 'layout' : go.Layout(xaxis=dict(range=[min(X),max(X)],title='Elapsed Time (s)'),yaxis = dict(range = [min(Y2),max(Y2)],title='Degrees Celsius (C)'),)} 
  fig3 = {'data': [data3], 'layout' : go.Layout(xaxis=dict(range=[min(X),max(X)],title='Elapsed Time (s)'),yaxis = dict(range = [min(Y3),max(Y3)],title='Voltage (V)'),)} 

  return fig1, fig2, fig3

if __name__ == "__main__":
    try:
        # Call setup function
        setup()
        demo_alert.setup()
        app.run_server(debug=True,host = '0.0.0.0')
    except Exception as e:
        print(e)
    finally:
        GPIO.cleanup()