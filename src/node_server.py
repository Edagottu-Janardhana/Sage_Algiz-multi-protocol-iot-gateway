"""
File: node_server.py
Purpose:
    Unified TCP server for:
    - Commissioning
    - Ethernet forwarding
    - Command handling
"""

import socket
import json
import threading
import os
import subprocess

SERVER_IP = "0.0.0.0"
SERVER_PORT = 5000
CONFIG_FILE = "/home/rpi4/Documents/Sage_Algiz/config.json"

lock = threading.Lock()
next_seq_no = None
NODE_ROLE = None
PAYLOAD_QUEUE = None
DOWNSTREAM_NODE_IP = None

# -------------------------------------------------
# CONFIG HELPERS
# -------------------------------------------------
def load_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(seq_no, role, downstream_ip=None):

    cfg = {
        "seq_no": seq_no,
        "role": role
    }

    if downstream_ip:
        cfg["downstream_ip"] = downstream_ip

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


# -------------------------------------------------
# NETWORK HELPER
# -------------------------------------------------
def get_gateway_ip(interface="eth0"):
    try:
        route = subprocess.check_output(["ip", "route"]).decode()
        for line in route.splitlines():
            if line.startswith("default") and interface in line:
                return line.split()[2]
    except:
        pass
    return None


# -------------------------------------------------
# COMMISSION HANDLER
# -------------------------------------------------
def init_next_seq_no():
    global next_seq_no

    if not has_sequence():
        print("No seq found. Waiting...")
        return

    my_seq = load_config()["seq_no"]
    next_seq_no = my_seq + 1
    print("Commission ready. Next seq_no =", next_seq_no)


def handle_commission(conn):
    global next_seq_no

    with lock:
        assigned_seq = next_seq_no
        next_seq_no += 1

    print("Assigned seq_no", assigned_seq)

    response = {
        "msg_type": "COMMISSION_RESPONSE",
        "assigned_seq_no": assigned_seq,
        "status": "OK"
    }

    conn.sendall(json.dumps(response).encode())



def handle_ble_data(request):
    print("Forwarding BLE data upstream")
    forward_upstream(request)

# -------------------------------------------------
# CLIENT HANDLER
# -------------------------------------------------
def handle_client(conn, addr):

    global DOWNSTREAM_NODE_IP
    DOWNSTREAM_NODE_IP = addr[0]
    print("Downstream node connected:", DOWNSTREAM_NODE_IP)
     # store it in config
    if has_sequence():
        cfg = load_config()
        save_config(cfg["seq_no"], cfg["role"], DOWNSTREAM_NODE_IP)        
    try:
        data = conn.recv(2048)
        if not data:
            return

        # Try JSON decode
        try:
            request = json.loads(data.decode())

            msg_type = request.get("msg_type")

            if msg_type == "COMMISSION_REQUEST":
                handle_commission(conn)

            elif msg_type == "BLE_DATA":
                handle_ble_data(request)

            else:
                print("Unknown JSON message")

        except UnicodeDecodeError:
            # Not JSON → treat as raw binary packet
            print("Received raw binary packet")
            handle_raw_packet(data, NODE_ROLE)

    except Exception as e:
        print("Node server error:", e)

    finally:
        conn.close()

# def handle_raw_packet(data, role):

#     print("Binary packet received:", data.hex())

#     # FIRST
#     if role == "FIRST":
#         print("Root processing locally")
#         return


#     # LAST
#     if role == "LAST":
#         print("Sending to UART")
#         send_uart_packet(data)
#         return

#     # MIDDLE
#     if role == "MIDDLE":

#         # Decide direction
#         # Example: if packet came from eth0 (upstream),
#         # forward to eth1 (downstream)

#         forward_packet(data)

def handle_raw_packet(data, role):

    print("Binary packet received:", data.hex())

    # Do NOT route here
    # Just push into routing pipeline
    PAYLOAD_QUEUE.put(data)

def forward_packet(data):

    success = False

    # 1️⃣ Try Ethernet first
    downstream_ip = get_eth_downstream_ip()

    if downstream_ip:
        success = send_eth_packet(data, downstream_ip)

    if success:
        print("Forward success")
    else:
        print("Forward failed")

# -------------------------------------------------
# START SERVER
# -------------------------------------------------
def start_node_server(role, queue):
    global NODE_ROLE, PAYLOAD_QUEUE
    NODE_ROLE = role
    PAYLOAD_QUEUE = queue
    init_next_seq_no()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((SERVER_IP, SERVER_PORT))
    server.listen(5)

    print("Node server running on port", SERVER_PORT)

    while True:
        conn, addr = server.accept()
        t = threading.Thread(target=handle_client, args=(conn, addr))
        t.daemon = True
        t.start()

# def get_eth_downstream_ip():
#     lease_file = "/var/lib/misc/dnsmasq.leases"

#     try:
#         with open(lease_file, "r") as f:
#             lines = f.readlines()

#         if not lines:
#             return None

#         # Take latest lease
#         last = lines[-1].split()
#         return last[2]  # IP address

#     except Exception:
#         return None
    
def get_eth_downstream_ip():

    lease_file = "/var/lib/misc/dnsmasq.leases"

    try:
        with open(lease_file) as f:
            lines = f.readlines()

        if not lines:
            return None

        # Take the latest lease
        last = lines[-1].split()

        ip = last[2]
        return ip

    except Exception as e:
        print("Lease read error:", e)
        return None    