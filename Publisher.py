import time
import board
import adafruit_dht
import paho.mqtt.client as mqtt
 
print("test")
 
# Sensor settings
dhtDevice = adafruit_dht.DHT11(board.D4, use_pulseio=False)  # Use the pin you've connected the data pin to
 
print("test")
# MQTT settings
#MQTT_BROKER = "broker.emqx.io"
MQTT_BROKER = "mosquitto.jdsr.de"
MQTT_PORT = 1883
MQTT_TOPIC = "sensor/temperature"
 
# Initialize MQTT client
client = mqtt.Client()
client.connect(MQTT_BROKER, MQTT_PORT, 60)
 
print("Starting loop...")
while True:
    try:
 
        temperature = dhtDevice.temperature
        humidity = dhtDevice.humidity
 
 
        if temperature is not None and humidity is not None:
            temp_f = temperature * 9/5.0 + 32  # Convert to Fahrenheit if needed
            #print(f"Temperature: {temperature:.2f}C / {temp_f:.2f}F, Humidity: {humidity:.2f}%")
            print(f"{temperature:.2f},{humidity:.2f}")
 
            # Publish to MQTT
            #client.publish(MQTT_TOPIC, f"{temperature:.2f}")
            #client.publish(MQTT_TOPIC, f"Temperature: {temperature:.2f}C / {temp_f:.2f}F, Humidity: {humidity:.2f}%")
            client.publish(MQTT_TOPIC,f"{temperature:.2f},{humidity:.2f}")
 
        else:
            print("Failed to retrieve data from sensor")
    except RuntimeError as error:
        print("RuntimeError: ", error.args[0])
    except Exception as error:
        print("An unexpected error occurred: ", error)
 
    time.sleep(0.5)  # Increase the delay
