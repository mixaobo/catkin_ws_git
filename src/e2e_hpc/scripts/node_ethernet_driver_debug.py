#!/usr/bin/env python3.9
import socket
import rospy
from e2e_hpc.msg import CustomMsg_Ranging
from e2e_hpc.msg import CustomMsg_RSSI

# Configuration for the TCP server
HOST = '192.168.8.70' # Listen on all interfaces (replace with anchor IP if needed)
PORT = 100      # Port to listen on (replace with anchor port if needed)

def parse_string_data(data):
    """
    Parse the received string data in the format
    Returns a dictionary with parsed values or None if parsing fails.
    """
    try:
        fields = data.split('/')
        print(fields)
        parsed_data = {
            'ble_status': "Connected",
            'system_time': fields[-3],
            'received_time': fields[-1],
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
counter = 0
def start_node_ethernet():
    # Initialize the ROS node
    global counter
    rospy.init_node('node_ethernet', anonymous=True)
    rospy.loginfo("Node Ethernet Started.")
    ID = 0
    # Create a ROS publisher for the ranging topic
    ranging_pub = rospy.Publisher('topic_Ranging_Driver', CustomMsg_Ranging, queue_size=10)
    rssi_pub = rospy.Publisher('topic_RSSI_Driver', CustomMsg_RSSI, queue_size=10)

    # Create and configure the TCP server socket
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        #srv.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 8192)
        srv.bind((HOST, PORT))
        srv.listen(2)
        srv.setblocking(False)
        rospy.loginfo("Node ethernet is listening on {}:{}".format(HOST, PORT))

        # Main server loop: accept new connections
        while not rospy.is_shutdown():
            try:
                conn, addr = srv.accept()  # Wait for a client connection
                conn.setblocking(False)
                rospy.loginfo("Accepted connection from {}".format(addr))

                # Connection loop: receive and process data from the client
                while not rospy.is_shutdown():
                    try:
                        # Receive data from the Ethernet device
                        data = conn.recv(1024)  # Buffer size is 1024 bytes

                        if data:
                            buffer += data  # Append received data to buffer
                            # Process all complete lines in the buffer
                            while b'\n' in buffer:
                                line, buffer = buffer.split(b'\n', 1)
                                if not line:
                                    continue  # Skip empty lines

                                try:
                                    rospy.loginfo("Received string data from {}: {}".format(addr, line))
                                    ID = line.decode('utf-8').strip().split('/')[0]
                                    print(line.decode('utf-8').strip().split('/'))
                                    temp_data = (line.decode('utf-8').strip().split('/'))
                                    if(float(ID) == 4.0):
                                        parsed_data = CustomMsg_Ranging()
                                    
                                        parsed_data.ble_status = "Connected"
                                        parsed_data.system_time = int(temp_data[-3])
                                        parsed_data.received_time = int(temp_data[-1])
                                        parsed_data.firstPath_power = float(temp_data[-8])
                                        parsed_data.aoa = float(temp_data[-7])
                                        parsed_data.distance = float(temp_data[-5])
                                        ranging_msg.hpc_system_time = rospy.Time.now().to_nsec()
                                        # Create and publish the ROS message
                                        ranging_msg = populate_message(CustomMsg_Ranging, parsed_data)
                                        ranging_pub.publish(parsed_data)
                                        rospy.loginfo("Published ranging message: \n{}".format(ranging_msg))
                                    elif(float(ID) == 5.0):
                                        pass
                                except:
                                    pass
                        else:
                            pass
                                
                        #if not data:
                            
                            rospy.loginfo("Connection closed by client")
                            break  # Exit the inner loop to accept a new connection
                        # Decode the received data and publish it to the 'ethernet_data' topic
                        decoded_data = data.decode('utf-8')
                        
                    except BlockingIOError:
                        pass    
                    except socket.error as e:
                        rospy.logerr("Socket error: %s", e)
                        break  # Exit the inner loop to accept a new connection
                    # data = conn.recv(4096)  # Receive up to 4096 bytes

                    # if not data:
                    #     # Client disconnected
                    #     #rospy.loginfo("Client {} disconnected.".format(addr))
                    #     break

                    # buffer += data  # Append received data to buffer

                    # # Process all complete lines in the buffer
                    # while b'\n' in buffer:
                    #     line, buffer = buffer.split(b'\n', 1)
                    #     if not line:
                    #         continue  # Skip empty lines

                    #     try:
                            
                    #         rospy.loginfo("Received string data from {}: {}".format(addr, line))
                    #         ID = line.decode('utf-8').strip().split('/')[0]
                    #         print(line.decode('utf-8').strip().split('/'))
                    #         temp_data = (line.decode('utf-8').strip().split('/'))
                    #         if(float(ID) == 4.0):
                    #             parsed_data = CustomMsg_Ranging()
                            
                    #             parsed_data.ble_status = "Connected"
                    #             parsed_data.system_time = int(temp_data[-3])
                    #             parsed_data.received_time = int(temp_data[-1])
                    #             print("parsed_data")
                    #             parsed_data.firstPath_power = float(temp_data[-8])
                                
                    #             parsed_data.aoa = float(temp_data[-7])
                    #             parsed_data.distance = float(temp_data[-5])
                                
                    #             print(parsed_data)
                    #             if 1:
                    #                 # Create and publish the ROS message
                    #                 # ranging_msg = populate_message(CustomMsg_Ranging, parsed_data)
                    #                 ranging_pub.publish(parsed_data)
                    #                 rospy.loginfo("Published ranging message: \n{}".format(ranging_msg))
                            
                            
                    #         # rospy.loginfo("Received string data from {}: {}".format(addr, line))
                    #         # ID = line.decode('utf-8').strip().split('/')[0]
                    #         # try:
                    #         #     parsed_data = parse_string_data(line.decode('utf-8').strip())
                    #         #     if(float(ID) == 4.0):
                                    
                    #         #         if parsed_data:
                    #         #             # Log out the system_time for manual checking
                    #         #             #rospy.loginfo("Time received from {}: {}".format(addr, parsed_data.get('system_time')))
                    #         #             # Create and publish the ROS message
                    #         #             ranging_msg = populate_message(CustomMsg_Ranging, parsed_data)
                    #         #             print("herre")
                    #         #             ranging_pub.publish(ranging_msg)
                    #         #             rospy.loginfo("Published ranging message: \n{}".format(ranging_msg))
                    #         elif(float(ID) == 5.0):
                    #             """
                    #             parsed_data = CustomMsg_RSSI()
                    #             parsed_data.pdoa1 = 0
                    #             parsed_data.tof1 = 0   
                    #             parsed_data.rssi1 = 0
                    #             parsed_data.pdoa2 = 0
                    #             parsed_data.tof2 = 0
                    #             parsed_data.rssi2 = 0

                    #             rssi_msg = populate_message(CustomMsg_RSSI, parsed_data)
                    #             rssi_pub.publish(parsed_data)
                    #             rospy.loginfo("Published rssi message: \n{}".format(rssi_msg))
                    #             """

                    #         elif(float(ID) == 6.0):
                    #             # Handle RSSI msg
                    #             pass
                    #     # except:
                    #     #     pass
                            
                                
                        # except Exception as e:
                        #     pass
                            # rospy.logerr("Error processing message from {}: {}".format(addr, e))

            except BlockingIOError:
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