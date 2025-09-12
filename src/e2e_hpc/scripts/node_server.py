#!/usr/bin/env python3.9
import rospy
import threading
import time
import json
import requests

from e2e_hpc.msg import CustomMsg_Ranging  # Adjust if needed
from e2e_hpc.msg import CustomMsg_Door  # Replace with your actual vehicle status msg

HOST = '127.0.0.1' # server IP address
PORT = 80            # server port

latest_localization = None
latest_vehicle = None
lock = threading.Lock()
new_data_event = threading.Event()  # Event to signal new data

def localization_callback(msg):
    global latest_localization
    with lock:
        latest_localization = msg
    new_data_event.set()  # Signal new data

def vehicle_callback(msg):
    global latest_vehicle
    with lock:
        latest_vehicle = msg
    new_data_event.set()  # Signal new data

def make_payload(alive_counter):
    with lock:
        loc = latest_localization
        veh = latest_vehicle

    payload = {
        "-": alive_counter,
        "Connection": {
            "VehicleStatus": "Awake", #getattr(veh, "status", "Unknown") if veh else "Awake",
            "BleStatus": getattr(veh, "ble_status", "Unknown") if veh else "Unknown",
            "UwbStatus": "Ranging", #getattr(veh, "uwb_status", "Ranging") if veh else "Ranging",
        },
        "Door": {
            "FrontLeft": ["close", "lock"],   # Fill with actual data if available
            "FrontRight": ["close", "lock"],
            "RearLeft": ["close", "lock"],
            "RearRight": ["close", "lock"],
            "Trunk": ["close", "lock"]
        },
        "Ranging": {
            "FisrtPath_Power": getattr(loc, "firstPath_power", 0) if loc else 0,
            "AOA": getattr(loc, "aoa", 0.0) if loc else 0.0,
            "Distance": getattr(loc, "distance", 0) if loc else 0,
        },
        "Device_ID": 0xFF
    }
    return payload

def sender_thread():
    alive_counter = 1
    while not rospy.is_shutdown():
        # Wait for new data event
        new_data_event.wait()
        if rospy.is_shutdown():
            break
        payload = make_payload(alive_counter)
        try:
            response = requests.post(url="http://{}:{}/api/".format(HOST, PORT), json=payload)
            print("Alive Counter: {} | Response: {} | Payload: {}".format(alive_counter, response.status_code, payload))
        except requests.RequestException as e:
            print("Failed to send payload: {}".format(e))
        alive_counter += 1
        new_data_event.clear()  # Reset event and wait for next data

def node_server():
    rospy.init_node('node_server', anonymous=True)
    rospy.Subscriber('topic_Localization_Driver', CustomMsg_Ranging, localization_callback)
    rospy.Subscriber('topic_Localization_Passenger', CustomMsg_Ranging, localization_callback)
    rospy.Subscriber('topic_Localization', CustomMsg_Ranging, localization_callback)
    rospy.Subscriber('topic_Vehicle', CustomMsg_Door, vehicle_callback)
    thread = threading.Thread(target=sender_thread)
    thread.daemon = True
    thread.start()
    rospy.spin()

if __name__ == '__main__':
    node_server()
