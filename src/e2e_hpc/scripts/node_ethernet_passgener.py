#!/usr/bin/env python3.9
import socket
import rospy
import time
from e2e_hpc.msg import CustomMsg_Ranging

# Configuration for the TCP server
HOST = '192.168.8.70' # anchor IP address (change to the 2nd anchor IP)
PORT = 101      # Port 

def parse_string_data(data, ble_status):
    """
    Parse the received string data in the format
    Returns a dictionary with parsed values or None if parsing fails.
    """
    try:
        fields = data.split('/')
        print(fields)
        parsed_data = {
            'ble_status': ble_status,
            'anchor_system_time': fields[-3],
            'anchor_received_time': fields[-1],
            'firstPath_power': float(fields[-8]),
            'aoa': float(fields[-7]),
            'distance': float(fields[-5])
        }
        return parsed_data
    except (IndexError, ValueError) as e:
        # rospy.logerr("Failed to parse string data: {}. Data: {}".format(e, data))
        return None

def populate_message(msg_type, parsed_data):
    """
    Populate a ROS message of type msg_type with values from parsed_data.
    Only sets fields that exist in both the message and the parsed data.
    """
    msg = msg_type()
    for field in msg.__slots__:
        if field in parsed_data:
            setattr(msg, field, parsed_data[field])
    return msg

def start_node_ethernet():
    # Initialize the ROS node
    rospy.init_node('node_ethernet', anonymous=True)
    rospy.loginfo("Node Ethernet Started.")
    ID = 0
    # Create a ROS publisher for the ranging topic
    ranging_pub = rospy.Publisher('topic_Ranging_Driver', CustomMsg_Ranging, queue_size=10)

    # Create and configure the TCP server socket
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST, PORT))
        srv.listen(1)
        srv.setblocking(False)
        rospy.loginfo("Node ethernet is listening on {}:{}".format(HOST, PORT))

        last_ranging_time = None
        ble_status = "Disconnected"

        # Main server loop: accept new connections
        while not rospy.is_shutdown():
            try:
                conn, addr = srv.accept()  # Wait for a client connection
                conn.setblocking(False)
                rospy.loginfo("Accepted connection from {}".format(addr))
                buffer = b''  # Buffer for incoming data
                # Connection loop: receive and process data from the client
                while not rospy.is_shutdown():
                    try:
                        data = conn.recv(1024)  # Receive up to 4096 bytes

                        if data:
                            buffer += data  # Append received data to buffer
                            # Process all complete lines in the buffer
                            while b'\n' in buffer:
                                line, buffer = buffer.split(b'\n', 1)
                                if not line:
                                    continue  # Skip empty lines
                                try:
                                    CurrentSystemTime = rospy.Time.now()
                                    ID = line.decode('utf-8').strip().split('/')[0]
                                    parsed_data = parse_string_data(line.decode('utf-8').strip(), ble_status)
                                    ble_status = "Connected"
                                    last_ranging_time = CurrentSystemTime

                                    if(float(ID) == 4.0):
                                        print(parsed_data)
                                        if parsed_data:                                            
                                            # Log out the system_time for manual checking
                                            #rospy.loginfo("Time received from {}: {}".format(addr, parsed_data.get('system_time')))
                                            
                                            # Create and publish the ROS message
                                            ranging_msg = populate_message(CustomMsg_Ranging, parsed_data)
                                            
                                            # Get the HPC system time (nanoseconds since epoch uint64)
                                            ranging_msg.hpc_system_time = CurrentSystemTime.to_nsec()
                                            
                                            ranging_pub.publish(ranging_msg)
                                            #rospy.loginfo("Published ranging message: \n{}".format(ranging_msg))
                                    elif(float(ID) == 5.0):
                                        pass
                                except:
                                    pass
                        else:
                            #return NULL due to setblocking(false)
                            break
                        # Check for BLE timeout and publish if status changes to Disconnected
                        if last_ranging_time is not None and (rospy.Time.now() - last_ranging_time) > 0.288:
                            ble_status = "Disconnected"
                            last_ranging_time = None
                        if ble_status != prev_ble_status and ble_status == "Disconnected":
                            # Publish a message indicating BLE is disconnected
                            msg = CustomMsg_Ranging()
                            msg.ble_status = "Disconnected"
                            msg.hpc_system_time = rospy.Time.now().to_nsec()
                            # Set other fields to default/zero/None as needed
                            ranging_pub.publish(msg)
                            prev_ble_status = ble_status
                        elif ble_status != prev_ble_status:
                            prev_ble_status = ble_status

                    except BlockingIOError:
                        #BlockingIOError exception due to no data from conn.recv
                        pass           
                    except Exception as e:
                        pass
                                # rospy.logerr("Error processing message from {}: {}".format(addr, e))
            except BlockingIOError:
                #BlockingIOError exception due to no data from srv.accept()
                pass
            except socket.error as e:
                # Handle socket errors (e.g., address in use)
                if not rospy.is_shutdown():
                    rospy.logerr("Socket error in main loop: {}".format(e))
                if e.errno == 98:
                    rospy.logfatal("Address already in use. Shutting down node ethernet.")
                    break
            except Exception as e:
                # Handle other exceptions (e.g., ROS shutdown)
                if not rospy.is_shutdown():
                    rospy.loginfo("Node ethernet interrupted.")
                break

    except Exception as e:
        # Handle any unhandled exceptions during setup or main loop
        rospy.logerr("Unhandled exception in node ethernet: {}".format(e))
    finally:
        # Always close the server socket on exit
        srv.close()
        rospy.loginfo("Node ethernet is shutting down.")

if __name__ == '__main__':
    try:
        # Uncomment the next line to run the test publisher instead of the socket server:
        # test_publisher()
        start_node_ethernet()
    except rospy.ROSInterruptException:
        rospy.loginfo("Node ethernet is interrupted.")
    except Exception as e:
        rospy.logerr("Unhandled exception in node ethernet: {}".format(e))