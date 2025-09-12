import requests
import random
import math
import numpy as np
import time

SERVER_URL = 'http://127.0.0.1/api'
# SERVER_URL = 'http://10.102.50.15/api'


class PositionGenerator:
    def __init__(self, rect_corners=((-1.5, 2.5), (1.5, -2.5)), max_radius=10):
        """
        Initialize the position generator.
        
        Args:
            rect_corners: Tuple of diagonal corners ((x1, y1), (x2, y2))
            max_radius: Maximum distance from rectangle center
        """
        # Extract rectangle corners
        (x1, y1), (x2, y2) = rect_corners
        
        # Ensure correct ordering of corners
        self.x_min, self.x_max = min(x1, x2), max(x1, x2)
        self.y_min, self.y_max = min(y1, y2), max(y1, y2)
        
        # Calculate rectangle center and dimensions
        self.center_x = (self.x_min + self.x_max) / 2
        self.center_y = (self.y_min + self.y_max) / 2
        self.width = self.x_max - self.x_min
        self.height = self.y_max - self.y_min
        
        # Calculate rectangle half-diagonal (minimum distance from center to outside)
        self.half_diagonal = math.sqrt((self.width/2)**2 + (self.height/2)**2)
        
        # Maximum radius
        self.max_radius = max_radius
        
        # Initialize current position
        # initial_angle = random.uniform(0, 2 * math.pi)
        # initial_distance = self.half_diagonal + random.uniform(10, 50)
        initial_angle = 60
        initial_distance = 200

        self.current_distance = initial_distance
        self.current_angle_rad = initial_angle
        self.current_angle_deg = math.degrees(initial_angle)
        
        # Parameters for gradual changes
        self.distance_step_range = (0.25, 0.5)  # Range for distance changes
        self.angle_step_range = (0.1, 6)   # Range for angle changes in degrees
        
    def get_next_position(self):
        """
        Generate the next position data with gradual changes.
        
        Returns:
            List [distance, angle_degrees]
        """
        # Randomly decide whether to increase or decrease
        distance_direction = random.choice([-1, 1])
        # angle_direction = random.choice([-1, 1])
        angle_direction = 1
        
        # Generate random step sizes within the defined ranges
        distance_step = random.uniform(*self.distance_step_range)
        angle_step = random.uniform(*self.angle_step_range)
        
        # Update distance with bounds checking
        new_distance = self.current_distance + (distance_direction * distance_step)
        
        # Ensure distance stays within bounds (half_diagonal to max_radius)
        new_distance = max(self.half_diagonal, min(new_distance, self.max_radius))
        
        # Update angle (in degrees)
        new_angle_deg = self.current_angle_deg + (angle_direction * angle_step)
        
        # Normalize angle to 0-360 range
        new_angle_deg = new_angle_deg % 360
        
        # Convert angle to radians for position calculation
        new_angle_rad = math.radians(new_angle_deg)
        
        # Calculate new position
        new_x = self.center_x + new_distance * math.cos(new_angle_rad)
        new_y = self.center_y + new_distance * math.sin(new_angle_rad)
        
        # Check if the new position is inside the rectangle
        if self.x_min <= new_x <= self.x_max and self.y_min <= new_y <= self.y_max:
            # If inside, revert to previous position and try again
            return self.get_next_position()
        
        # Update current position
        self.current_distance = new_distance
        self.current_angle_rad = new_angle_rad
        self.current_angle_deg = new_angle_deg
        
        # Return [distance, angle_degrees]
        return [self.current_distance * 100, self.current_angle_deg]

position_gen = PositionGenerator()

def generate_random_ranging_data():
    """
    Generate random ranging data that simulates real-world behavior.
    
    Returns:
        dict: A dictionary with randomized ranging data
    """
    
    global position_gen

    distance,  angle = position_gen.get_next_position()
    
    # First path power depends on distance (closer = stronger signal)
    # Range from -80 dBm (far) to -30 dBm (close)
    # Using inverse square law: power ∝ 1/distance²
    base_power = -30  # dBm at 1m
    distance_factor = (distance / 100) ** 2  # Convert to meters and square
    power = base_power - 20 * math.log10(distance_factor)  # Convert to dB scale
    
    # Add some random variation
    power = power + random.uniform(-5, 5)
    
    # Ensure power is within reasonable bounds
    power = max(-80, min(-30, power))
    
    return {
        "FirstPathPower": round(power, 1),  # dbm
        "AOA": round(angle, 2),              # degree
        "Distance": round(distance,2)              # cm
    }

def set_connection_status(vehicle_status, ble_status, uwb_status, door_states=None, ranging_data=None):
    # Default door states
    door_data = {
        "FrontLeft": ["close", "lock"],
        "FrontRight": ["close", "lock"],
        "RearLeft": ["close", "lock"],
        "RearRight": ["close", "lock"],
        "Trunk": ["close", "lock"]
    }
    
    # Update door states if provided
    if door_states:
        for door, state in door_states.items():
            if door in door_data:
                door_data[door] = state
    
    hpc_data_dict = {
        #Info and Vehicle notification
        "Connection": {
            "VehicleStatus" : vehicle_status, #[Sleep, Awake]
            "BleStatus" : ble_status, # [Connected, Disconnected]
            "UwbStatus": uwb_status,   #  [NA, Ranging, CPD, Mixed]
        },
        # Vehicle Door model
        "Door": door_data,
        # User model
        "Ranging": ranging_data,
        "Device_ID" : 0xFF # 0xFF : Unknown, ...
    }
    response = requests.post(SERVER_URL, json=hpc_data_dict)
    if response.ok:
        print('Status updated:', response.json())
    else:
        print('Failed to update status:', response.status_code, response.text)

def set_door_status(door_command, current_door_states=None):
    """
    Processes a door command and returns updated door states without sending to server.
    
    Args:
        door_command (str): Door command in the format 'position_action'
                           (e.g., 'fl_open', 'rr_lock', 't_unlock')
        current_door_states (dict, optional): Current door states. If None, uses defaults.
    
    Returns:
        tuple: (success, updated_door_states, message)
    """
    # Door command mapping
    door_command_map = {
        # Front Left door commands
        'fl_open': ('FrontLeft', 0, 'open'),
        'fl_close': ('FrontLeft', 0, 'close'),
        'fl_lock': ('FrontLeft', 1, 'lock'),
        'fl_unlock': ('FrontLeft', 1, 'unlock'),
        
        # Front Right door commands
        'fr_open': ('FrontRight', 0, 'open'),
        'fr_close': ('FrontRight', 0, 'close'),
        'fr_lock': ('FrontRight', 1, 'lock'),
        'fr_unlock': ('FrontRight', 1, 'unlock'),
        
        # Rear Left door commands
        'rl_open': ('RearLeft', 0, 'open'),
        'rl_close': ('RearLeft', 0, 'close'),
        'rl_lock': ('RearLeft', 1, 'lock'),
        'rl_unlock': ('RearLeft', 1, 'unlock'),
        
        # Rear Right door commands
        'rr_open': ('RearRight', 0, 'open'),
        'rr_close': ('RearRight', 0, 'close'),
        'rr_lock': ('RearRight', 1, 'lock'),
        'rr_unlock': ('RearRight', 1, 'unlock'),
        
        # Trunk commands
        't_open': ('Trunk', 0, 'open'),
        't_close': ('Trunk', 0, 'close'),
        't_lock': ('Trunk', 1, 'lock'),
        't_unlock': ('Trunk', 1, 'unlock')
    }
    
    # Default door states if not provided
    door_states = {
        "FrontLeft": ["close", "lock"],
        "FrontRight": ["close", "lock"],
        "RearLeft": ["close", "lock"],
        "RearRight": ["close", "lock"],
        "Trunk": ["close", "lock"]
    }
    
    # Use provided door states if available
    if current_door_states:
        for door, state in current_door_states.items():
            if door in door_states:
                door_states[door] = state
    
    # Check if the command is valid
    if door_command not in door_command_map:
        valid_commands = ', '.join(door_command_map.keys())
        return False, door_states, f"Invalid door command. Valid commands: {valid_commands}"
    
    # Process the door command
    door, index, value = door_command_map[door_command]
    door_state = door_states[door].copy()
    door_state[index] = value
    door_states[door] = door_state
    
    return True, door_states, f"Updated {door} state to {door_state[0]}, {door_state[1]}"

if __name__ == "__main__":
    # Initialize default values
    vehicle_status = 'Sleep'
    ble_status = 'Disconnected'
    uwb_status = 'NA'
    ranging_data = None
    
    # Default door states
    door_states = {
        "FrontLeft": ["close", "lock"],
        "FrontRight": ["close", "lock"],
        "RearLeft": ["close", "lock"],
        "RearRight": ["close", "lock"],
        "Trunk": ["close", "lock"]
    }
      # Define valid values for each status
    vehicle_status_values = ['Sleep', 'Awake']
    ble_status_values = ['Connected', 'Disconnected']
    uwb_status_values = ['NA', 'Ranging', 'CPD', 'Mixed']
    
    # Door command mapping
    door_command_map = {
        # Front Left door commands
        'fl_open': ('FrontLeft', 0, 'open'),
        'fl_close': ('FrontLeft', 0, 'close'),
        'fl_lock': ('FrontLeft', 1, 'lock'),
        'fl_unlock': ('FrontLeft', 1, 'unlock'),
        
        # Front Right door commands
        'fr_open': ('FrontRight', 0, 'open'),
        'fr_close': ('FrontRight', 0, 'close'),
        'fr_lock': ('FrontRight', 1, 'lock'),
        'fr_unlock': ('FrontRight', 1, 'unlock'),
        
        # Rear Left door commands
        'rl_open': ('RearLeft', 0, 'open'),
        'rl_close': ('RearLeft', 0, 'close'),
        'rl_lock': ('RearLeft', 1, 'lock'),
        'rl_unlock': ('RearLeft', 1, 'unlock'),
        
        # Rear Right door commands
        'rr_open': ('RearRight', 0, 'open'),
        'rr_close': ('RearRight', 0, 'close'),
        'rr_lock': ('RearRight', 1, 'lock'),
        'rr_unlock': ('RearRight', 1, 'unlock'),
        
        # Trunk commands
        't_open': ('Trunk', 0, 'open'),
        't_close': ('Trunk', 0, 'close'),
        't_lock': ('Trunk', 1, 'lock'),
        't_unlock': ('Trunk', 1, 'unlock')
    }
    
    # Create a mapping of values to their respective status
    status_mapping = {}
    for val in vehicle_status_values:
        status_mapping[val.lower()] = 'vehicle'
    for val in ble_status_values:
        status_mapping[val.lower()] = 'ble'
    for val in uwb_status_values:
        status_mapping[val.lower()] = 'uwb'
    
    print("Type 'exit' to quit.")
    print(f"Current status: Vehicle={vehicle_status}, BLE={ble_status}, UWB={uwb_status}")
    print("Current door states:")
    for door, state in door_states.items():
        print(f"  {door}: {state[0]}, {state[1]}")
    print(f"Connection status inputs: {', '.join(list(status_mapping.keys()))}")
    print("Door command format examples: 'fl_open', 'rr_lock', 't_unlock'")
    print("  fl=FrontLeft, fr=FrontRight, rl=RearLeft, rr=RearRight, t=Trunk")
      # Keep track of the last known states to send in requests
    last_vehicle_status = vehicle_status
    last_ble_status = ble_status
    last_uwb_status = uwb_status
    last_door_states = door_states.copy()
    
    # Flag to track if we need to send an update to the server
    need_to_update_server = False
    
    while True:
        user_input = input("Enter a command: ").strip().lower()
        
        if user_input == 'exit':
            set_connection_status(
                "sleep",
                "disconnected",
                "na",
                {
                    "FrontLeft": ["close", "lock"],
                    "FrontRight": ["close", "lock"],
                    "RearLeft": ["close", "lock"],
                    "RearRight": ["close", "lock"],
                    "Trunk": ["close", "lock"]
                },
                {
                    "FirstPathPower": 0,  # dbm
                    "AOA": 0,              # degree
                    "Distance": 0             # cm
                }
            );
            break
            
        # Check if input is a door command
        if user_input in door_command_map:
            # Use the set_door_status function to handle door commands
            success, updated_door_states, message = set_door_status(user_input, last_door_states)
            if success:
                last_door_states = updated_door_states
                print(message)
                      # Send the updated door state to the server with random ranging data
                try:
                    # ranging_data = generate_random_ranging_data()
                    set_connection_status(last_vehicle_status, last_ble_status, last_uwb_status, last_door_states, ranging_data)
                    print(f"Door status sent to server with ranging data: Distance={ranging_data['Distance']}cm, Angle={ranging_data['AOA']}°, Power={ranging_data['FirstPathPower']}dBm")
                except Exception as e:
                    print(f"Error sending door status to server: {str(e)}")
            else:
                print(message)
        
        # Check if input is a connection status command
        elif user_input in status_mapping:
            status_type = status_mapping[user_input]
            need_to_update_server = True
            
            if status_type == 'vehicle':
                last_vehicle_status = user_input.capitalize()
            elif status_type == 'ble':
                last_ble_status = user_input.capitalize()
            elif status_type == 'uwb':
                last_uwb_status = user_input.capitalize()
                
            print(f"Updated status: Vehicle={last_vehicle_status}, BLE={last_ble_status}, UWB={last_uwb_status}")
              # Send the updated connection status to the server with random ranging data
            if need_to_update_server:
                try:
                    ranging_data = generate_random_ranging_data()
                    set_connection_status(last_vehicle_status, last_ble_status, last_uwb_status, last_door_states, ranging_data)
                    print(f"Connection status sent to server with ranging data: Distance={ranging_data['Distance']}cm, Angle={ranging_data['AOA']}°, Power={ranging_data['FirstPathPower']}dBm")
                    need_to_update_server = False
                except Exception as e:
                    print(f"Error sending connection status to server: {str(e)}")
        else:
            import time
            while(True):
                try:
                    ranging_data = generate_random_ranging_data()
                    set_connection_status(last_vehicle_status, last_ble_status, last_uwb_status, last_door_states, ranging_data)
                    print(f"Connection status sent to server with ranging data: Distance={ranging_data['Distance']}cm, Angle={ranging_data['AOA']}°, Power={ranging_data['FirstPathPower']}dBm")
                    need_to_update_server = False
                    time.sleep((288 + 20) / 1000)
                except KeyboardInterrupt as e:
                    break
            continue
