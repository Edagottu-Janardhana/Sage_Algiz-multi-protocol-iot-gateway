"""
Sage Algiz Main - Event Driven Architecture
"""

import RPi.GPIO as GPIO
import os
import json
import sys
import time
import threading
import multiprocessing
from queue import Queue
import socket
import base64

import dbus
import dbus.mainloop.glib
from gi.repository import GLib

from commission_client import run_commission_client
from commission_server import start_commission_server
from wifi_rx import start_wifi_server
from wifi_tx import send_packet
from ble_task import ble_entry
from wifi_setup import start_ap, ensure_sta_profile, start_sta, create_ap_profile, get_downstream_ip, stop_ap
from packet_builder import build_packet, build_seq_response_packet, build_lorawan_packet
from uart_transport import send_uart_packet, receive_uart_packets
from node_server import start_node_server, get_gateway_ip, get_eth_downstream_ip
import node_server
from glow import control_led
from ble_advertiser import register_advertisement
from sage_control import register_gatt

# ---------------- CONFIG ----------------

CONFIG_FILE = "/home/rpi4/Documents/Sage_Algiz/config.json"

GPIO_FIRST  = 17
GPIO_MIDDLE = 27
GPIO_LAST   = 22

# ---------------- GLOBAL QUEUE ----------------

payload_queue = Queue()
#==========================lorawan_thread================
def lorawan_thread():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 1701))

    print("LoRa listener started")

    while True:

        data, addr = sock.recvfrom(512)
        
        print("LoRa Rx:", data)
        # Build protocol packet
        packet_bytes = build_lorawan_packet(0x01, data)
        print("LoRa Rx in bytes and packet format:", packet_bytes)
        # Send to forwarding worker
        payload_queue.put(packet_bytes)

#=============
def start_ble_stack(role):

    print("Starting BLE stack...")

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()

    register_gatt(bus, role)
    register_advertisement(bus)

    print("BLE Advertising + GATT running")

    loop = GLib.MainLoop()
    loop.run()
# ---------------- GPIO ----------------

def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(GPIO_FIRST, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(GPIO_MIDDLE, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(GPIO_LAST, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def read_role_from_jumper():
    first  = GPIO.input(GPIO_FIRST) == GPIO.LOW
    middle = GPIO.input(GPIO_MIDDLE) == GPIO.LOW
    last   = GPIO.input(GPIO_LAST) == GPIO.LOW

    selected = [first, middle, last].count(True)

    if selected != 1:
        print("Invalid jumper configuration")
        sys.exit(1)

    if first:
        return "FIRST"
    if middle:
        return "MIDDLE"
    if last:
        return "LAST"

# ---------------- CONFIG ----------------

def send_eth_packet(data, target_ip):

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        sock.connect((target_ip, 5000))
        sock.sendall(data)
        sock.close()
        print("Forward success via Ethernet")
        return True

    except Exception as e:
        print("Ethernet send failed:", e)
        return False
    
def load_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(seq_no, role):
    cfg = {"seq_no": seq_no, "role": role}
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)
def has_sequence():
    if not os.path.exists(CONFIG_FILE):
        return False

    try:
        cfg = load_config()
        return "seq_no" in cfg
    except:
        return False

# ---------------- PRODUCERS ----------------

def start_ble_process():
    ipc_queue = multiprocessing.Queue()

    ble_process = multiprocessing.Process(
        target=ble_entry,
        args=(ipc_queue,),
        daemon=True
    )
    ble_process.start()

    def monitor_ble():
        while True:
            payload = ipc_queue.get()  
            print("BLE Payload:", payload)
            payload_queue.put(payload)

    threading.Thread(target=monitor_ble, daemon=True).start()


def start_wifi_rx_thread(role, seq_no):

    if role == "FIRST":
        return  # FIRST does not receive upstream

    profile = ensure_sta_profile(seq_no)
    start_sta(profile)

    def wifi_receiver():
        while True:
            data = receive_packet()  
            if not data:
                continue
            payload = data
            print("WiFi RX Payload:", payload)
            payload_queue.put(payload)

    threading.Thread(target=wifi_receiver, daemon=True).start()

# ---------------- CONSUMER ----------------
def forwarding_worker(role, my_seq):

    while True:

        packet = payload_queue.get()
        success = False

        if len(packet) < 4:
            continue

        sof = packet[0]

        # ----------------------------------
        # CONTROL PACKET
        # | SOF | CMD | LEN | CRC |
        # ----------------------------------
        if len(packet) == 4:

            cmd = packet[1]
            length = packet[2]

            print("Control Packet | CMD:", cmd)

            if cmd == 0x03:
                print("CMD 3 received → sending my SEQ_NO")

                response = build_seq_response_packet(0x03, my_seq)
                send_uart_packet(response)

            continue

        # -----------------------------
        # UART PACKET (Backward)
        # | SOF | CMD | SEQ | R | G | B | CRC |
        # -----------------------------
        if len(packet) == 7:

            cmd      = packet[1]
            dest_seq = packet[2]
            R        = packet[3]
            G        = packet[4]
            B        = packet[5]

            print("UART Packet | Dest:", dest_seq, "| CMD:", cmd)

            # Backward routing
            if cmd == 0x02:

                # If reached destination
                if dest_seq == my_seq:
                    print("Reached destination → controling Algiz_Glow")
                    control_led(R, G, B)
                    continue

                # Otherwise forward upstream
                print("Forwarding upstream")

                upstream_ip = get_gateway_ip("eth0")

                if upstream_ip:
                    success = send_eth_packet(packet, upstream_ip)

                if not success:
                    print("Ethernet failed, trying LORA")
                    success = send_uart_packet(packet)

                continue

        # -----------------------------
        # BLE PACKET (Forward)
        # | SOF | CMD | LEN | ... |
        # -----------------------------
        else:

            cmd = packet[1]

            print("BLE Packet | CMD:", cmd)

            if cmd != 0x01:
                print("Unknown BLE CMD")
                continue

            # LAST → Send to UART
            if role == "LAST":
                print("LAST → Sending to UART")
                send_uart_packet(packet)
                continue

            # FIRST or MIDDLE → Forward downstream
            if role == "FIRST" or role == "MIDDLE":

                downstream_ip = node_server.DOWNSTREAM_NODE_IP

                if not downstream_ip:
                    cfg = load_config()
                    downstream_ip = cfg.get("downstream_ip")
                    
                print("Downstream IP:", downstream_ip)
                if downstream_ip:
                    success = send_eth_packet(packet, downstream_ip)

                if not success:
                    print("Ethernet failed, trying LORA")
                    success = send_uart_packet(packet)
                    print("Forward success")

                continue

        # 2️⃣ WiFi Forward
        print("Forwarding via WiFi")

        if role == "MIDDLE":

            create_ap_profile(role, seq_no)
            start_ap(role, seq_no)

            success = send_packet(packet_bytes)

            stop_ap(seq_no)

            profile = ensure_sta_profile(seq_no)
            start_sta(profile)

        elif role == "FIRST":
            start_ap(role, seq_no)
            time.sleep(2)  # wait for client to connect

            downstream_ip = get_downstream_ip()

            if downstream_ip:
                success = send_packet(packet_bytes, downstream_ip)
            else:
                print("No downstream connected")
             

        if success:
            print("Forward success")
        else:
            print("Forward failed")
# ---------------- COMMISSIONING ----------------

def commissioning_mode(role):

    print("Entering commissioning mode...")

    # FIRST always root
    if role == "FIRST":

        if not has_sequence():
            save_config(1, "FIRST")
            print("FIRST assigned SEQ = 1")

        return

    # For MIDDLE / LAST
    # Try Ethernet commissioning in parallel
    while not has_sequence():

        print("Trying Ethernet commissioning...")
        success = run_commission_client(role)

        if has_sequence():
            break

        print("Waiting for BLE or Ethernet assignment...")
        time.sleep(3)

    print("Commissioning completed.")
# ---------------- NORMAL OPERATION ----------------

def normal_operation(role):

    cfg = load_config()
    seq_no = cfg["seq_no"]

    #Persistent WiFi mode
    # if role == "FIRST":
    #     create_ap_profile(role, seq_no)

    #1️⃣  Start producers
    start_ble_process()

    #2️⃣ Lorawan sx1302_hal 
    #lora_thread = threading.Thread(target=lorawan_thread,daemon=True)

    #lora_thread.start()

    #if role != "FIRST":
    #   start_wifi_server(payload_queue)

        # Start UART RX only on LAST
    #if role == "LAST":
    #threading.Thread(target=receive_uart_packets,args=(payload_queue,),daemon=True).start()

    # Start consumer
    #threading.Thread(target=forwarding_worker,args=(role, seq_no),daemon=True).start()

# ---------------- MAIN ----------------

def main():
    try:
        setup_gpio()
        role = read_role_from_jumper()
        print("Role:", role)



        #Ble tread for commissionning and control Algiz Glow
        #threading.Thread(target=start_ble_stack,args=(role,),daemon=True).start()

        # 2️⃣ Commission if needed
        if not has_sequence():
            commissioning_mode(role)

            while not has_sequence():
                time.sleep(1)

        # 1️⃣ Start Ethernet Node Server ALWAYS
        #threading.Thread(target=start_node_server,args=(role, payload_queue),daemon=True).start()

        # 3️⃣ Normal operation
        normal_operation(role)

        while True:
            time.sleep(10)

    except KeyboardInterrupt:
        print("Shutting down")

    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    main()
