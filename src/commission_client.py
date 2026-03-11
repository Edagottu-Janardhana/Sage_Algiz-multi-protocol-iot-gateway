"""
File: commission_client.py
Purpose:
    TCP commissioning client.
    Runs on MIDDLE and LAST nodes.
    Requests sequence number from upstream node.
"""

import socket
import json
import os
import subprocess
#SERVER_IP = "192.168.50.1"
SERVER_PORT = 5000

CONFIG_FILE = "/home/rpi4/Documents/Sage_Algiz/config.json"
TIMEOUT_SEC = 5

def get_gateway_ip(interface="eth0"):
    route = subprocess.check_output(["ip", "route"]).decode()
    for line in route.splitlines():
        if line.startswith("default") and interface in line:
            return line.split()[2]
    return None

def has_sequence():
    if not os.path.exists(CONFIG_FILE):
        return False

    try:
        with open(CONFIG_FILE, "r") as f:
            cfg = json.load(f)
        return "seq_no" in cfg
    except Exception:
        return False


def save_config(seq_no, role):
    cfg = {
        "seq_no": seq_no,
        "role": role
    }

    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


def run_commission_client(role):
    if has_sequence():
        print("Sequence already exists, skipping commissioning")
        return

    SERVER_IP = get_gateway_ip()

    if not SERVER_IP:
        print("No upstream gateway found")
        return

    print("Connecting to upstream server", SERVER_IP)

    request = {
        "msg_type": "COMMISSION_REQUEST",
        "device_id": "ALGIZ-UNKNOWN",
        "role": role,
        "firmware_version": "1.0"
    }

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(TIMEOUT_SEC)

    try:
        sock.connect((SERVER_IP, SERVER_PORT))
        print("Connected to server")

        sock.sendall(json.dumps(request).encode())
        print("Commission request sent")

        data = sock.recv(1024)
        if not data:
            raise RuntimeError("Empty response from server")

        response = json.loads(data.decode())

        if response.get("msg_type") != "COMMISSION_RESPONSE":
            raise RuntimeError("Invalid response type")

        seq_no = response["assigned_seq_no"]
        save_config(seq_no, role)

        print("Commissioning successful")
        print("Assigned seq_no:", seq_no)

    except Exception as e:
        print("Commissioning failed:", e)

    finally:
        sock.close()
        print("Connection closed")


