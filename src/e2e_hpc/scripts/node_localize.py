#!/usr/bin/env python3.9
import rospy
import threading
import threading
import numpy as np
import os
import csv
from e2e_hpc.msg import CustomMsg_Ranging
from e2e_hpc.msg import CustomMsg_RSSI




def append2Csv(filename, distance, aoa):
    file_exist = os.path.exists(filename)

    try:
        with open(filename, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            
            if not file_exist:
                writer.writerow(['distance', 'aoa'])
            
            writer.writerow([distance, aoa])
    except Exception as e:
        print(f"Error while appending to csv: {e}")


"""
#This function calculates the residuals for the optimization problem.
def residuals(p, anchor, d, aoa_rad):
    x, y = p
    dx, dy = x - anchor[0], y - anchor[1]
    pred_d = np.hypot(dx, dy)
    pred_aoa = np.arctan2(dy, dx)
    return [pred_d - d, wrap_angle(pred_aoa - aoa_rad)]



def estimate_position(d, aoa_deg):
    aoa_rad = np.deg2rad(aoa_deg)
    initial_guess = calculate_initial_guess(anchor1, d, aoa_deg)
    result = least_squares(residuals, initial_guess, args=(anchor1, d, aoa_rad), method='lm')
    return result.x
"""
anchor1 = np.array([0.0, 0.0])  # Fixed anchor position
Sync_Flag = [0,0]
RangingMsg_Passenger = CustomMsg_Ranging()
RangingMsg_Driver = CustomMsg_Ranging()
RangingMsg_Passenger_Event = threading.Event()
RangingMsg_Driver_Event = threading.Event()
threading_lock = threading.Lock()



def wrap_angle_radians(angle):
    return (angle + np.pi) % (2 * np.pi) - np.pi

def wrap_angle_360(angle):
    """Wrap angle to [0, 360) degrees."""
    return angle % 360

def calculate_initial_guess(anchor, d, aoa_deg):
    aoa_rad = np.deg2rad(aoa_deg)
    x = anchor[0] + d * np.cos(aoa_rad)
    y = anchor[1] + d * np.sin(aoa_rad)
    return np.array([x, y])

def calcualte_distance_angle(x1, y1, x2, y2):
    dx = x2 - x1
    dy = y2 - y1
    distance = np.hypot(dx, dy)
    angle_rad = np.arctan2(dy, dx)
    angle_deg = np.rad2deg(angle_rad)
    return distance, angle_deg

class ExtendedKalmanFilter:
    def __init__(self, x_init, P_init, Q, R):
        self.x = x_init
        self.P = P_init
        self.Q = Q
        self.R = R

    def predict(self):
        self.P = self.P + self.Q

    def update(self, z, anchor):
        px, py = self.x
        dx, dy = px - anchor[0], py - anchor[1]
        d_pred = np.hypot(dx, dy)
        aoa_pred = np.arctan2(dy, dx)
        z_pred = np.array([d_pred, aoa_pred])

        r2 = dx**2 + dy**2
        H = np.array([
            [dx/d_pred, dy/d_pred],
            [-dy/r2,     dx/r2]
        ])

        y = z - z_pred
        y[1] = wrap_angle_radians(y[1])

        S = H.dot(self.P).dot(H.T) + self.R
        K = self.P.dot(H.T).dot(np.linalg.inv(S))
        self.x = self.x + K.dot(y)
        self.P = (np.eye(2) - K.dot(H)).dot(self.P)

    def current_position(self):
        return self.x

class ExtendedKalmanFilterPolar:
    def __init__(self, x_init, P_init, Q, R):
        self.x = x_init  # [distance, aoa_rad]
        self.P = P_init
        self.Q = Q
        self.R = R

    def predict(self):
        # For static or simple motion, prediction may be identity
        self.P = self.P + self.Q

    def update(self, z):
        # z = [measured_distance, measured_aoa_rad]
        y = z - self.x
        y[1] = wrap_angle_radians(y[1])  # Ensure angle difference is wrapped

        H = np.eye(2)  # Measurement matrix is identity
        S = np.dot(np.dot(H, self.P), H.T) + self.R
        K = np.dot(np.dot(self.P, H.T), np.linalg.inv(S))
        self.x = self.x + np.dot(K, y)
        self.x[1] = wrap_angle_radians(self.x[1])  # Keep angle in [-pi, pi]
        self.P = np.dot((np.eye(2) - np.dot(K, H)), self.P)

    def current_position(self):
        # Returns distance and AoA in degrees
        return self.x[0], np.rad2deg(self.x[1])

def Ranging_callback(ekf_class, msg, publish_to_node):
    d = msg.distance
    aoa_rad = np.deg2rad(msg.aoa)
    z = np.array([d, aoa_rad])
    ekf_class.predict()
    ekf_class.update(z)
    
    #Debug msg
    received_xy = calculate_initial_guess(anchor1, msg.distance, msg.aoa)
    ##print("Kalman input  {} / {}".format(msg.distance, msg.aoa))
    predict_distance, predict_angle = ekf_class.current_position()
    
    #predict_distance, predict_angle = calcualte_distance_angle(0, 0, predict_xy[0], predict_xy[1])
    msg_localization = CustomMsg_Ranging()
    msg_localization = msg
    msg_localization.distance = predict_distance
    msg_localization.aoa = predict_angle
    publish_to_node.publish(msg_localization)  
    #print("Kalman output {} / {}".format(predict_distance, predict_angle))
    #print("------------")    

A_old = 0
aoa_system = 0
A = 0
counter = 0
predict_distance_driver_old = 0
predict_distance_passenger_old = 0

def Ranging_callback_all(ekf_class_driver, msg_driver, ekf_class_passenger, msg_passenger , publish_to_node):
    global A_old, aoa_system, A, counter,predict_distance_driver_old , predict_distance_passanger_old
    aoa_median = 0
    aoa_final = 0

    d_anchor = 100 #change later
    # driver 
    print("-------------------------------")
    predict_distance_driver = msg_driver.distance
    predict_angle_driver = msg_driver.aoa
    # time_driver = msg_driver.hpc_system_time
    # aoa_rad_driver = np.deg2rad(msg_driver.aoa)
    # z_driver = np.array([d_driver, aoa_rad_driver])
    # ekf_class_driver.predict()
    # ekf_class_driver.update(z_driver)
    # predict_distance_driver, predict_angle_driver = ekf_class_driver.current_position()


    #passenger
    predict_distance_passenger = msg_passenger.distance
    predict_angle_passenger = msg_passenger.aoa
    # time_passenger = msg_passenger.hpc_system_time
    # aoa_rad_passenger = np.deg2rad(msg_passenger.aoa)
    # z_passenger = np.array([d_passenger, aoa_rad_passenger])
    # ekf_class_passenger.predict()
    # ekf_class_passenger.update(z_passenger)
    # predict_distance_passenger, predict_angle_passenger = ekf_class_passenger.current_position()

    msg_localization = CustomMsg_Ranging()
    #compare time
    
    # if (time_driver > time_passenger): 
    #print("Receive Driver first")
    flipped_aoa_passenger = predict_angle_driver + 180
    if (flipped_aoa_passenger > 360):
        flipped_aoa_passenger -= 360
    aoa_median = (msg_driver.aoa + flipped_aoa_passenger) / 2
    predict_distance_passenger
    # OMG {calcualte} is the variable for cos(BAC)
    # with A is passenger, B is driver and C is user as points in 2D space
    # calculate = (((np.round(predict_distance_passenger)) **2) + (d_anchor **2) - ((np.round(predict_distance_driver)) **2)) / (2 * (np.round(predict_distance_passenger)) * d_anchor)
    #print("Driver Distance = {} / Passenger Distance = {} / calcualte = {}".format(predict_distance_driver, predict_distance_passenger,calculate))
    
    cos_driver = (predict_distance_driver**2 + d_anchor**2 - predict_distance_passenger**2) / (2 * predict_distance_passenger * predict_distance_driver)

    if (cos_driver > 1):
        cos_driver = 1
    elif (cos_driver < -1):
        cos_driver = -1
    # if (predict_angle_driver > 0)
    # B = np.acos(calculate)*180/np.pi#print("B: {}".format(B))
    sine_driver = np.sqrt(1 - cos_driver**2)

    xc = predict_distance_driver * cos_driver - d_anchor / 2
    yc = predict_distance_driver * sine_driver

    aoa_system = np.degrees(np.atan2(yc, xc))
    
    
    if(counter < 5):
        A = aoa_system*0.2 + (A_old * 0.8) #Low pass filter
    else:
        if(abs(aoa_system - A_old)> 60):
            A = A_old
        else:
            A = aoa_system*0.2 + (A_old * 0.8) #Low pass filter

    
    counter +=1
    # print("B: {} / A: {} / A_old: {}".format(B, A, A_old))
    A_old = A
    # if(msg_passenger.aoa > 0):
    #     A = 360 - A
    aoa_final = A
    # print("Driver AoA = {} / Passenger AoA = {}".format(msg_driver.aoa, (msg_passenger.aoa )))
    # print("A = {} / AoA Final: {}".format(A, aoa_final))
    msg_localization = CustomMsg_Ranging()
    # msg_localization.distance = predict_distance_driver * 1.3
    msg_localization.distance = np.sqrt(xc**2 + yc**2)
    msg_localization.aoa = aoa_system


    print(
        f"[i] Driver anchor value:        d = {predict_distance_driver} cm --- | ---  aoa = {predict_angle_driver}\n" +
        f"[i] Passenger anchor value:     d = {predict_distance_passenger} cm --- | ---  aoa = {predict_angle_passenger}\n" +
        f"[i] System calculated value:    d = {msg_localization.distance} cm --- | --- aoa = {msg_localization.aoa} degree\n"
    )
    publish_to_node.publish(msg_localization)  
    #print("Kalman output {} / {} / timestamp".format(predict_distance_driver, aoa_final))
    #print("------------") 

    # elif (time_passenger > time_driver):
    #     print("Receive Passenger first")
    #     flipped_aoa_driver = predict_angle_passenger + 180
    #     if (flipped_aoa_driver > 360):
    #         flipped_aoa_driver -= 360
    #     aoa_median = (msg_passenger.aoa + flipped_aoa_driver) / 2
    #     #print("Driver AoA = {} / Passenger AoA = {}".format(predict_angle_passenger, aoa_median))
    #     calculate = ((predict_distance_passenger **2) + (d_anchor **2) - (predict_distance_driver **2)) / (2 * predict_distance_passenger * d_anchor)
    #     print("Driver AoA = {} / Passenger AoA = {} / calcualte = {}".format(predict_distance_driver, predict_distance_passenger,calculate))
    #     if (calculate > 1):
    #         calculate = 1
    #     elif (calculate < -1):
    #         calculate = -1
        
    #     B = np.acos(calculate)*180/np.pi#print("B: {}".format(B))
    #     A = 180 - B
    #     print("A: {}".format(A))
    #     aoa_final = A
    #     #print("AoA Final: {}".format(aoa_final))
    #     msg_localization = msg_passenger
    #     msg_localization.distance = predict_distance_passenger
    #     msg_localization.aoa = aoa_final
    #     publish_to_node.publish(msg_localization)  
        #print("Kalman output {} / {} / timestamp".format(predict_distance_passenger, aoa_final))
        #print("------------")



    
    # #Debug msg
    # received_xy = calculate_initial_guess(anchor1, msg.distance, msg.aoa)
    # ##print("Kalman input  {} / {}".format(msg.distance, msg.aoa))
    # predict_distance, predict_angle = ekf_class_pass.current_position()
    
    #predict_distance, predict_angle = calcualte_distance_angle(0, 0, predict_xy[0], predict_xy[1])   


counter_passenger = 0
current_aoa_passenger = 0.0
previous_aoa_passenger = 0.0
def Ranging_Passenger_callback(msg):
    global RangingMsg_Passenger, counter_passenger, current_aoa_passenger, previous_aoa_passenger, ekf_passenger
    ##print("Passenger received value  {} / {}".format(msg.distance, msg.aoa))
    current_aoa_passenger = msg.aoa
    if (counter_passenger >= 5):
        if(counter_passenger == 5):
            previous_aoa_passenger = current_aoa_passenger
            ekf_passenger = ExtendedKalmanFilter(
                x_init=[msg.distance, current_aoa_passenger],
                P_init=np.eye(2) * 100,
                Q=np.eye(2) * 5.0,
                R=np.diag([10, np.deg2rad(3.0)**2]) #(cm, aoa)
            )
        counter_passenger = 11
        # if (previous_aoa_passener >= 50):
        #     if (-70 <= current_aoa_passenger <= -50):
        #         current_aoa_passenger = previous_aoa_passener
        a= 0
        #passenger
        aoa = np.deg2rad(current_aoa_passenger)
        z_passenger = np.array([msg.distance, aoa])
        ekf_passenger.predict()
        ekf_passenger.update(z_passenger, anchor1)
        predict_distance_passenger, a = ekf_passenger.current_position()
        msg.distance = predict_distance_passenger
        #print("Passenger AoA: {}".format(msg.aoa))
        predict_angle_passenger = current_aoa_passenger*0.2 + (previous_aoa_passenger * 0.8) #Low pass filter
        # if (np.abs(predict_angle_passenger) > 30):
        #     msg.aoa = previous_aoa_passener   
        # else:
        previous_aoa_passenger = predict_angle_passenger
            
        with threading_lock:
            RangingMsg_Passenger = msg
        RangingMsg_Passenger_Event.set()
    counter_passenger += 1

counter_driver = 0
current_aoa_driver = 0.0
previous_aoa_driver = 0.0
def Ranging_Driver_callback(msg):
    global RangingMsg_Driver, counter_driver, current_aoa_driver, previous_aoa_driver, ekf_driver
    # #print("Driver received value  {} / {}".format(msg.distance, msg.aoa))
    current_aoa_driver = msg.aoa
    if (counter_driver >= 5):
        if(counter_driver == 5):
            previous_aoa_driver = current_aoa_driver
            ekf_driver = ExtendedKalmanFilter(
                x_init=[msg.distance, current_aoa_driver],
                P_init=np.eye(2) * 100,
                Q=np.eye(2) * 5.0,
                R=np.diag([10, np.deg2rad(3.0)**2]) #(cm, aoa)
            )
        counter_driver = 11
        # if (previous_aoa_driver >= 50):
        #     if (-70 <= current_aoa_driver <= -50):
        #         current_aoa_driver = previous_aoa_driver

        aoa = np.deg2rad(msg.aoa)
        z_driver = np.array([msg.distance, aoa])
        ekf_driver.predict()
        ekf_driver.update(z_driver, anchor1)
        predict_distance_driver, predict_angle_driver = ekf_driver.current_position()
        msg.distance = predict_distance_driver
      
        if (np.abs(predict_angle_driver) > 30):
            msg.aoa = previous_aoa_driver
            
        else:
            previous_aoa_driver = current_aoa_driver
        #print("Driver AoA: {}".format(msg.aoa))    
        with threading_lock:
            RangingMsg_Driver = msg
        #print("msg AoA: {}".format(RangingMsg_Driver.aoa))   
        RangingMsg_Driver_Event.set()
    counter_driver += 1

def background_thread():
    global ekf_driver, ekf_passenger, pub_Localization, pub_Localization_Driver, pub_Localization_Passenger, RangingMsg_Driver, RangingMsg_Passenger

    while not rospy.is_shutdown():
        
        if((RangingMsg_Driver_Event.wait(timeout=0.002) == True) and (RangingMsg_Passenger_Event.wait(timeout=0.002) == True)):
            with threading_lock:
                
                #print("Ranging callback all")
                
                Ranging_callback_all(ekf_driver, RangingMsg_Driver, ekf_passenger, RangingMsg_Passenger, pub_Localization)
                RangingMsg_Driver_Event.clear()
                RangingMsg_Passenger_Event.clear()
        else:
            pass
            # if(RangingMsg_Driver_Event.wait(timeout=0.002) == True):
            #     with threading_lock:
            #         #print("Ranging callback driver")
            #         
            #         Ranging_callback(ekf_driver, RangingMsg_Driver, pub_Localization_Driver)
            #         RangingMsg_Driver_Event.clear()
            # if(RangingMsg_Passenger_Event.wait(timeout=0.002) == True):
            #     with threading_lock:    
            #         #print("Ranging callback passenger")
            #         Ranging_callback(ekf_passenger, RangingMsg_Passenger, pub_Localization_Passenger)
            #         RangingMsg_Passenger_Event.clear()
        if rospy.is_shutdown():
            break
        
            
        
        

def Node_Ranging():
    global pub_Localization_Driver, pub_Localization_Passenger, pub_Localization
    #Initialize
    rospy.init_node('node_Ranging', anonymous=True)

    #Publish to
    pub_Localization = rospy.Publisher('topic_Localization', CustomMsg_Ranging, queue_size=10)
    pub_Localization_Driver = rospy.Publisher('topic_Localization_Driver', CustomMsg_Ranging, queue_size=10)
    pub_Localization_Passenger = rospy.Publisher('topic_Localization_Passenger', CustomMsg_Ranging, queue_size=10)

    #Subscribe to
    rospy.Subscriber('topic_Ranging_Driver', CustomMsg_Ranging, Ranging_Driver_callback)
    rospy.Subscriber('topic_Ranging_Passenger', CustomMsg_Ranging, Ranging_Passenger_callback)



    # Start a background thread to keep the node alive
    bg_thread = threading.Thread(target=background_thread)
    bg_thread.daemon = True
    bg_thread.start()
    #print("Start node")
    rospy.spin()


# Initial state
# P:  < 1: trust more on inital predictions / ~5: balance / >10: trust more on measurements
# Q: 0.01: standstill/ 0.1: Slow movement / fast movement 0.3 ~ 0.5 / Vehicle: 1.0+
# R Small: trust measurrements / Large: trust predictions. variance = standard_deviation**2
initial_x = calculate_initial_guess(anchor1, 10, 40)

if __name__ == '__main__':
    Node_Ranging()