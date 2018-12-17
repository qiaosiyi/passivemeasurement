#!/bin/env python
# coding=UTF-8
# @file       passive measurement client
# @details    download the meas job to hardware, calculating the counter, calculating HH(heavy hitter),HC(heavy changer)
#             Port scan.
# @author     KJ, siyiq
# @date       Nov 2018
# @version    v4
# @par Copyright (c):
#      	      xjtu, xilinx
"""gRPC passive measurement client implementation in python."""

from __future__ import print_function
from collections import defaultdict
from ctypes import *
import random
import time
import threading
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.animation as animation

import grpc

import MeasurementTask_pb2
import MeasurementTask_pb2_grpc
import DataReport_pb2
import DataReport_pb2_grpc
import PacketGenerator_pb2
import PacketGenerator_pb2_grpc

# HH HC port_scan setting threshold value
HEAVY_HITTER = 4000000
HEAVY_CHANGER = 500000
PSNUMBER = 8

# init data structures 
# flow table : {flow ID: 5 tuples} 
flow_tuple_dic = {
    # range(1,11), HH detection and HC detection flow ID:
    1: "22.2.2.41:4141 -> 22.2.2.45:9090 tcp",
    2: "22.2.2.41:4141 -> 22.2.2.45:9091 tcp",
    3: "22.2.2.41:4141 -> 22.2.2.45:9092 tcp",
    4: "22.2.2.41:4141 -> 22.2.2.45:5001 tcp",
    5: "22.2.2.41:4141 -> 22.2.2.45:3456 tcp",
    6: "22.2.2.41:4141 -> 22.2.2.45:9095 tcp",
    7: "22.2.2.41:4141 -> 22.2.2.45:9096 tcp",
    8: "22.2.2.41:4141 -> 22.2.2.45:9097 tcp",
    9: "22.2.2.41:4141 -> 22.2.2.45:9098 tcp",
    10: "22.2.2.41:4141 -> 22.2.2.45:9099 tcp",
    #port access deny ：range(11,16)
        11: "22.2.2.45 21",
        12: "22.2.2.45 22",
        13: "22.2.2.45 31",
        14: "22.2.2.45 1433",
        15: "22.2.2.45 1521",
        # port scan：range(16,26)
        16: "22.2.2.45",
        17: "22.2.2.45",
        18: "22.2.2.45",
        19: "22.2.2.45",
        20: "22.2.2.45",
        21: "22.2.2.45",
        22: "22.2.2.45",
        23: "22.2.2.45",
        24: "22.2.2.45",
        25: "22.2.2.45"
}
# result of HH:{5 tuple:[[10 counter value in histry], whether HH]} 
result = {flow_tuple_dic[1]: [[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], ""],
          flow_tuple_dic[2]: [[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], ""],
          flow_tuple_dic[3]: [[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], ""],
          flow_tuple_dic[4]: [[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], ""],
          flow_tuple_dic[5]: [[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], ""],
          flow_tuple_dic[6]: [[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], ""],
          flow_tuple_dic[7]: [[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], ""],
          flow_tuple_dic[8]: [[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], ""],
          flow_tuple_dic[9]: [[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], ""],
          flow_tuple_dic[10]: [[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], ""]}
# in HC detection, a set value of early counter
flow_map = {flow_tuple_dic[1]: 0.0,
            flow_tuple_dic[2]: 0.0,
            flow_tuple_dic[3]: 0.0,
            flow_tuple_dic[4]: 0.0,
            flow_tuple_dic[5]: 0.0,
            flow_tuple_dic[6]: 0.0,
            flow_tuple_dic[7]: 0.0,
            flow_tuple_dic[8]: 0.0,
            flow_tuple_dic[9]: 0.0,
            flow_tuple_dic[10]: 0.0}
# result of HC: {5 tuple:[derta of counter value, whether HC]} 
heavy_changer_result = {flow_tuple_dic[1]: [0.0, ""],
                        flow_tuple_dic[2]: [0.0, ""],
                        flow_tuple_dic[3]: [0.0, ""],
                        flow_tuple_dic[4]: [0.0, ""],
                        flow_tuple_dic[5]: [0.0, ""],
                        flow_tuple_dic[6]: [0.0, ""],
                        flow_tuple_dic[7]: [0.0, ""],
                        flow_tuple_dic[8]: [0.0, ""],
                        flow_tuple_dic[9]: [0.0, ""],
                        flow_tuple_dic[10]: [0.0, ""]}
# result of port deny, alert information
port_access_result = {}
port_access_alarm = {}
# result of SUM of being scaned port {host IP address:SUM}
port_scan_count = {}
# result of port scan task {host IP address:whether scanning}
port_scan_result = {}
# in port scan task, the SUM throughput of scan flow {host IP address:SUM}
port_scan_sum_result = {}

def SetDefault():
    """init access deny and port scan storage value"""
    for i in range(11,16):
      port_access_result[flow_tuple_dic[i]] = 0.0
      port_access_alarm[flow_tuple_dic[i]] = ""

    port_scan_count[flow_tuple_dic[16]] = 0
    port_scan_result[flow_tuple_dic[16]] = ""
    port_scan_sum_result[flow_tuple_dic[16]] = 0
'''
    print("port_access_result:\n")
    print(port_access_result)
    print("port_access_alarm:\n")
    print(port_access_alarm)
    print("port_scan_count:\n")
    print(port_scan_count)
    print("port_scan_result:\n")
    print(port_scan_result)
    print("port_scan_sum_result:\n")
    print(port_scan_sum_result)
'''
SetDefault()

# figure ploting
grid = plt.GridSpec(20, 10)
fig = plt.figure()
fig.canvas.set_window_title('Xilinx Labs NMAS Demo')
ax1 = fig.add_subplot(grid[0:17, :4])
ax2 = fig.add_subplot(grid[0:7, 5:])
ax5 = fig.add_subplot(grid[7:14, 5:])
ax3 = fig.add_subplot(grid[14:18, 5:])
ax4 = fig.add_subplot(grid[18:20, 5:])

# HH init ploting data
# x axle，y axle
x = range(0, 10)
# 10 HH counter value in histry
y = [[1, 4, 6, 8, 9, 1, 4, 6, 8, 9], [2, 8, 5, 10, 6, 2, 8, 5, 10, 6],
     [1, 4, 6, 8, 9, 1, 4, 6, 8, 9], [2, 8, 5, 10, 6, 2, 8, 5, 10, 6],
     [1, 4, 6, 8, 9, 1, 4, 6, 8, 9], [2, 8, 5, 10, 6, 2, 8, 5, 10, 6],
     [1, 4, 6, 8, 9, 1, 4, 6, 8, 9], [2, 8, 5, 10, 6, 2, 8, 5, 10, 6],
     [1, 4, 6, 8, 9, 1, 4, 6, 8, 9], [2, 8, 5, 10, 6, 2, 8, 5, 10, 6]]
glable = []
for i in range(1, 11):
    glable.append('Flow #%d' % i)
mycolor = ('#30a2da', '#fc4f30', '#e5ae38', '#6d904f', '#8b8b8b', '#9467bd',
           '#8c564b', '#e377c2', '#1f77b4', '#d62728')
# the flow ID of HH,HC detection task 
flow_tuple = [flow_tuple_dic[1],
              flow_tuple_dic[2],
              flow_tuple_dic[3],
              flow_tuple_dic[4],
              flow_tuple_dic[5],
              flow_tuple_dic[6],
              flow_tuple_dic[7],
              flow_tuple_dic[8],
              flow_tuple_dic[9],
              flow_tuple_dic[10]
              ]
# init of HH status
hc_status = ["", "", "", "", "", "", "", "", "", ""]

add = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
MB = 1.0*10**6

# form headline
columns = ['Flow Tuples', 'Total Counter(MB)', 'Speed(MB/s)', 'Heavy Hitter']

# suggested color
# ['#30a2da', '#fc4f30', '#e5ae38', '#6d904f', '#8b8b8b', '#9467bd',
# '#8c564b', '#e377c2', '#1f77b4', '#d62728', '#17becf', '#bcbd22']
# init of HH form value
cluster_data = []
for i in range(0, 10):
    cluster_data.append([flow_tuple[i], 0, y[i][-1], hc_status[i]])


def div(x):
    """Byte2MB"""
    return x/MB


# the headline of port access deny
columns2 = ["IP Address", "Port", "Counter", "Alarm"]
# spliting the IP address and port, in port access deny task 
split_ip_port = [[], []]
for i in range(11, 16):
    split_ip_port[0].append(flow_tuple_dic[i].split(' ')[0])
    split_ip_port[1].append(flow_tuple_dic[i].split(' ')[1])
# Port forbidden access Table data initialization
cluster_data2 = []
for i in range(0, 5):
    '''
    print(port_access_result)
    print(flow_tuple_dic)
    print(port_access_alarm)
    '''
    cluster_data2.append(["", "", \
                          "", ""])

# Port scan table header
columns3 = ["IP Address", "Total Counter", "Hit Number", "Alarm"]
# host IP address
src_ip_list = flow_tuple_dic[16]
# Port scan table data initialization
cluster_data3 = []
total_number = "/8"
port_scan_rate = str(int(port_scan_count[flow_tuple_dic[16]]))+total_number
cluster_data3.append(["", "",
                      "", ""])

# HC form headline
columns4 = ['Flow Tuples', 'Changer', 'Heavy Changer']
# HC init form data
cluster_data4 = []
for i in range(0, 10):
    cluster_data4.append([flow_tuple[i], 0, hc_status[i]])


def prepare_data():
    """update HH, Port forbidden access,HC,Port scan task table data，ploting data(x,y) in HH task"""
    x.pop(0)
    x.append(x[-1]+1)

    # Update HH table data and y-axis data
    for i in range(0, 10):
        y[i] = map(div, result[flow_tuple[i]][0])
        sum_counter = cluster_data[i][1] + y[i][-1]
        cluster_data[i] = ([flow_tuple[i], sum_counter, y[i][-1], result[flow_tuple[i]][1]])

    # Update port prohibits access to tabular data
    j=0
    for j in range(0, 5):
        if(cluster_data2[j][3]!=True):
            break

    for i in range(0, 5):
        if(port_access_alarm[flow_tuple_dic[11+i]] == True):
          cluster_data2[j] = ([split_ip_port[0][i], split_ip_port[1][i], port_access_result[flow_tuple_dic[11+i]],
                             port_access_alarm[flow_tuple_dic[11+i]]])
          j = j+1
          if(j>=5):
            break

    # Update port scan table data
    for i in range(0, 1):
        port_scan_rate = str(port_scan_count[flow_tuple_dic[16]])+total_number
        if(port_scan_result[flow_tuple_dic[16]] == True):
          cluster_data3[i] = ([src_ip_list, port_scan_sum_result[flow_tuple_dic[16]],
                             port_scan_rate, port_scan_result[flow_tuple_dic[16]]])

    # Update HC table data
    for i in range(0, 10):
        cluster_data4[i] = ([flow_tuple[i], heavy_changer_result[flow_tuple[i]]
                             [0], heavy_changer_result[flow_tuple[i]][1]])


def animate(i):
    """After the data is ready, print out the images and tables of each task."""
    ax1.clear()
    ax2.clear()
    ax3.clear()
    ax4.clear()
    ax5.clear()
    ax2.axis('off')
    ax2.axis('tight')
    ax2.patch.set_visible(False)
    ax3.axis('off')
    ax3.axis('tight')
    ax3.patch.set_visible(False)
    ax4.axis('off')
    ax4.axis('tight')
    ax4.patch.set_visible(False)
    ax5.axis('off')
    ax5.axis('tight')
    ax5.patch.set_visible(False)
    # update data
    prepare_data()

    # Print HH image
    ax1.set_ylim(0, 10)
    ax1.stackplot(x, y[::-1], labels=glable,
                  colors=mycolor)  # , lw=2, color=blue
    plt.legend(loc='upper left')
    ax1.set_xlabel('Time(s)', fontsize=20)
    ax1.set_ylabel('Throughput(MB/s)', fontsize=20)
    ax1.set_title("Realtime Flow statistics", size=24)
    ax1.tick_params(reset=True, labelsize=20)

    # Print HH form
    tmp_cluster_data = cluster_data[0:8]
    tmp_glable = glable[0:8]
    the_table = ax2.table(cellText=tmp_cluster_data, cellLoc='center',
                          rowLabels=tmp_glable, rowColours=mycolor[::-1],
                          colWidths=[0.1, 0.05, 0.035, 0.035],
                          colLabels=columns,
                          loc='center')
    the_table.set_fontsize(22)
    the_table.scale(5, 2)
    ax2.set_title("Application: Flow Statistics", size=24)

    # Print port is forbidden to access task table
    the_table2 = ax3.table(cellText=cluster_data2, cellLoc='center',
                           colWidths=[0.1, 0.05, 0.05, 0.05],
                           colLabels=columns2,
                           loc='center')
    the_table2.set_fontsize(22)
    the_table2.scale(3, 2)
    ax3.set_title("Application: Access Control", size=24)

    # Print port scan task table
    tmp_col3_lab = columns3[0:4]
    the_table3 = ax4.table(cellText=cluster_data3, cellLoc='center',
                           colWidths=[0.1, 0.05, 0.05, 0.05],
                           colLabels=columns3,
                           loc='center')
    the_table3.set_fontsize(22)
    the_table3.scale(3, 2)
    ax4.set_title("Application: Port Scan", size=24)
    
    # Print HC task form
    tmp_cluster_data4 = cluster_data4[0:8]
    
    the_table4 = ax5.table(cellText=tmp_cluster_data4, cellLoc='center',
                           
                           colWidths=[0.1, 0.05, 0.05, 0.05],
                           colLabels=columns4,
                           loc='center')
    the_table4.set_fontsize(22)
    the_table4.scale(5, 2)
    ax5.set_title("Application: Heavy Changer(HC)", size=24)
    

class StructPointer(Structure):
    """Call the cpp program to decode the data uploaded by the hardware. Structure definition in python"""
    _fields_ = [("index", c_uint), ("de_counter", c_uint)]


def Heavy_Hitter(flow_index, decounter):
    """Check whether HH occurs according to the counter value of the current stream.."""
    heavy_hitter = decounter
    # When the counter value is greater than a certain threshold, the current 
    #judgment result is saved as True, otherwise it is empty.
    if heavy_hitter > HEAVY_HITTER:
        result[flow_tuple_dic[flow_index]][1] = True
    else:
        result[flow_tuple_dic[flow_index]][1] = ""
    # Delete the first historical data in the saved counter result, and save the current counter value in the end of the list.
    del result[flow_tuple_dic[flow_index]][0][0]
    result[flow_tuple_dic[flow_index]][0].append(heavy_hitter)


def Heavy_Changer(flow_index, decounter):
    """Check whether HC occurs according to the counter value of the current stream."""
    # Calculate the difference between the current period and the previous period to get the changed value
    heavy_changer = abs(decounter - flow_map[flow_tuple_dic[flow_index]])
    # When the change is greater than a certain threshold, save the current judgment result as True, otherwise it is empty.
    if heavy_changer > HEAVY_CHANGER:
        heavy_changer_result[flow_tuple_dic[flow_index]][1] = True
    else:
        heavy_changer_result[flow_tuple_dic[flow_index]][1] = ""
    # Save the calculated change value in the HC result variable
    heavy_changer_result[flow_tuple_dic[flow_index]][0] = heavy_changer
    # Save the current counter of the stream to the corresponding position of the 
    #flow_map corresponding to the stream for the calculation of the next period
    flow_map[flow_tuple_dic[flow_index]] = decounter


def Port_Access(flow_index, decounter):
    """Check whether the port is forbidden from being accessed according to the counter value of the current stream."""
    # If the counter value of the stream monitored by the task is greater than 0, it means that a packet is sent to the port, 
    # that is, the port that is forbidden to access is accessed, the counter value is reserved, and the value is set to True.
    if decounter > 0:
        port_access_result[flow_tuple_dic[flow_index]] = decounter
        port_access_alarm[flow_tuple_dic[flow_index]] = True
    else:
        port_access_result[flow_tuple_dic[flow_index]] = 0
        port_access_alarm[flow_tuple_dic[flow_index]] = ""


def One_Port_Scan(flow_index, decounter):
    """Detect whether a port scan occurs based on the counter value of the current stream."""
    # If the counter value of the stream detected by the task is greater than 0, it means that a packet is sent to the port,
    # that is, the port may be scanned. Number of scans +1, record the counter value
    if decounter > 0:
        port_scan_count[flow_tuple_dic[flow_index]] += 1
        port_scan_sum_result[flow_tuple_dic[flow_index]] += decounter
    else:
        port_scan_count[flow_tuple_dic[flow_index]] = 0
        port_scan_sum_result[flow_tuple_dic[flow_index]] = 0


def Port_Scan_Threshold():
    """After a period is over, the number of port scans is judged. If a threshold is 
    greater than a certain threshold, a port scan occurs on an ip."""
    for key, value in port_scan_count.items():
        if value > PSNUMBER:
            port_scan_result[key] = True
        else:
            port_scan_result[key] = ""


def WritePassiveMeasurementTask(stub, id, dev_id, task_type, filter_type, reportinterval, memorylimitationkb):
    """Download passive measurement tasks"""
    request = MeasurementTask_pb2.WritePassiveMeasurementTaskRequest()
    # setting req-id，device id
    request.id = id
    request.dev_id = dev_id
    # Judge task type (1：FLOW_TABLE),(2,BLOOM_FILTER)
    if task_type == 1:
        request.task_description.type = MeasurementTask_pb2.PassiveMeasurementTaskControl.FLOW_TABLE
    if task_type == 2:
        request.task_description.type = MeasurementTask_pb2.PassiveMeasurementTaskControl.BLOOM_FILTER
    # Judging the type of filtering(1:ALL),(2,SAMPLE),(3,COMPRESSION)
    if filter_type == 1:
        request.task_description.filter_type = MeasurementTask_pb2.PassiveMeasurementTaskControl.ALL
    if filter_type == 2:
        request.task_description.filter_type = MeasurementTask_pb2.PassiveMeasurementTaskControl.SAMPLE
    if filter_type == 3:
        request.task_description.filter_type = MeasurementTask_pb2.PassiveMeasurementTaskControl.COMPRESSION
    # Set the reporting period and memory limit
    request.report_control.reportinterval = reportinterval
    request.report_control.memorylimitationkb = memorylimitationkb
    response = stub.WritePassiveMeasurementTask(request)
    if response.status:
        print("task_id:%s\n" % response.id)
        return response.id
    else:
        print("error")
        return -1


def generate_request(request):
    """Generate a request to read the passive measurement result task"""
    messages = [
        request
    ]
    for msg in messages:
        print("Sending %s req_id at %s dev" % (msg.id, msg.dev_id))
        yield msg


def ReadPassiveMeasurementResult(stub, req_id, task_id, dev_id):
    """Get the flow table data from the hardware, and decode it, enter the different 
    task functions according to the flow label, and save the statistical results."""
    request = MeasurementTask_pb2.ReadPassiveMeasurementResultRequest()
    # Specify request id, person id, device id
    request.id = req_id
    request.task_ids.append(task_id)
    request.dev_id = dev_id
    responses = stub.ReadPassiveMeasurementResult(generate_request(request))
    lib = cdll.LoadLibrary("./libdecoder.so")
    lib.cpp_call.restype = StructPointer
    # Establish a connection with the server, and get all the stream data results in each cycle in the response.
    for response in responses:
        # At the beginning of each cycle, it is necessary to initialize the port to 
        #prohibit access, and the port scan task saves the result variable.
        SetDefault()
        # The current cycle, the counter of each stream is processed, from the first item of the flow table to the last item
        for i in range(len(response.passive_result)):
            # Get the counter value uploaded by the hardware: contains the stream label, and the undecoded counter value
            counter = response.passive_result[i].packet_counter
            # Call the decoder.c file in the same folder to decode the data reported by the
            # hardware, and get the stream index and the exact value of the counter.
            decoder = lib.cpp_call(counter)
            flow_index = decoder.index
            decounter = float(decoder.de_counter)
            # If the stream index is not within the scope of the flow table monitoring, proceed to the next loop
            if flow_index not in range(1, 26):
                continue
            # If it is within the monitoring range, according to the flow index, and the
            # flow label of different task monitoring, the check-in is seated.
            # The flow number is 1 to 10, and it is judged whether it is HH or HC.
            if flow_index in range(1, 11):
                Heavy_Hitter(flow_index, decounter)
                Heavy_Changer(flow_index, decounter)
            # The flow label is 10 to 16, to determine whether the port is forbidden.
            if flow_index in range(11, 16):
                Port_Access(flow_index, decounter)
            # The flow label is 16 to 25 to determine whether the current port is scanned.
            if flow_index in range(16, 26):
                One_Port_Scan(flow_index, decounter)
        # After all the flows in one cycle are processed, the statistics scanned in the port monitored
        # in the port scan task determine whether the current ip has a port scan. 
        Port_Scan_Threshold()


def RemovePassiveMeasurementTask(stub, task_id, dev_id):
    """Remove passive tasks when no passive measurements are required or when hardware stops statistics are required """
    request = MeasurementTask_pb2.RemovePassiveMeasurementTaskRequest()
    # Specify task id, device id
    request.id = task_id
    request.dev_id = dev_id
    response = stub.RemovePassiveMeasurementTask(request)
    if response.status:
        print("task_id:%s at %s dev has been removed" %
              (response.id, request.dev_id))
        return True
    else:
        print("false")
        return False


def run():
    """Run the above function via grpc"""
    # Set the ip and port connected to the server, which must be consistent with the server.
    with grpc.insecure_channel('192.168.0.11:50051') as channel:
        stub = MeasurementTask_pb2_grpc.MeasurementRuntimeStub(channel)
        print("-------------- WritePassiveMeasurementTask --------------")
        # Pass the passive measurement task, specify req-id, device id, task type, filter type,
        # reporting period, and memory limit are 0, 0, 2, 1, 1 second, 100kB respectively.
        task_id = WritePassiveMeasurementTask(stub, 0, 0, 2, 1, 1, 100)
        print("get task_id:%s " % task_id)
        print("-------------- ReadPassiveMeasurementResult --------------")
        # Enable the thread to obtain the passive measurement data result in real time,
        # specify the request id, task id, device id are 0, task_id, 0
        writeresult = threading.Thread(
            target=ReadPassiveMeasurementResult, name='StartStoreResult', args=(stub, 0, task_id,0))
        writeresult.start()
        print("------------------------ReadResult ----------------------")
        # Wait 5 seconds to get new data
        time.sleep(5)
        # Get the data result thread to write the result in real time, execute the drawing
        # program, read the result in real time, and display it dynamically
        ani = animation.FuncAnimation(fig, animate, interval=1000)
        plt.show()
        print("-------------- RemovePassiveMeasurementTask --------------")
        RemovePassiveMeasurementTask(stub,task_id,0)


if __name__ == '__main__':
    run()
