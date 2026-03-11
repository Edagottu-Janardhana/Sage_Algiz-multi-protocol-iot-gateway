"""
File: commission_server.py
Purpose:
    TCP commissioning server.
    Assigns sequence numbers based on own seq_no.
"""

import socket
import json
import threading
import os

SERVER_IP = "0.0.0.0"
SERVER_PORT = 5000
CONFIG_FILE = "/home/rpi4/Documents/Sage_Algiz/config.json"

lock = threading.Lock()
next_seq_no = None
stop_server = False


def load_my_seq_no():
    if not os.path.exists(CONFIG_FILE):
        raise RuntimeError("Config file not found")

    with open(CONFIG_FILE, "r") as f:
        cfg = json.load(f)

    if "seq_no" not in cfg:
        raise RuntimeError("seq_no missing in config")

    return cfg["seq_no"]


def init_next_seq_no():
    global next_seq_no
    my_seq = load_my_seq_no()
    next_seq_no = my_seq + 1
    print("Server initialized with next_seq_no =", next_seq_no)


def handle_client(conn, addr):
    global next_seq_no
    global stop_server

    print("Client connected from", addr)

    try:
        data = conn.recv(1024)
        if not data:
            return

        request = json.loads(data.decode())

        if request.get("msg_type") != "COMMISSION_REQUEST":
            response = {
                "msg_type": "COMMISSION_ERROR",
                "reason": "INVALID_MESSAGE"
            }
            conn.sendall(json.dumps(response).encode())
            return

        with lock:
            assigned_seq = next_seq_no
            next_seq_no += 1

        print("Assigned seq_no", assigned_seq, "to", addr)

        response = {
            "msg_type": "COMMISSION_RESPONSE",
            "assigned_seq_no": assigned_seq,
            "upstream_seq_no": assigned_seq - 1,
            "status": "OK"
        }

        conn.sendall(json.dumps(response).encode())

        ack_data = conn.recv(1024)
        if ack_data:
            ack = json.loads(ack_data.decode())
            if ack.get("msg_type") == "COMMISSION_ACK":
                print("Client confirmed seq_no", ack.get("seq_no"))
                stop_server = True

    except Exception as e:
        print("Error:", e)

    finally:
        conn.close()
        print("Client disconnected from", addr)


def start_commission_server():
    init_next_seq_no()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((SERVER_IP, SERVER_PORT))
    server.listen(5)

    server.settimeout(1)

    print("Commissioning server listening on port", SERVER_PORT)

    while not stop_server:
        try:
            conn, addr = server.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr))
            t.daemon = True
            t.start()
        except socket.timeout:
            continue

    server.close()
    print("Commissioning server stopped")


def get_eth_downstream_ip():
    lease_file = "/var/lib/misc/dnsmasq.leases"

    try:
        with open(lease_file, "r") as f:
            lines = f.readlines()

        if not lines:
            return None

        # Take latest lease
        last = lines[-1].split()
        return last[2]  # IP address

    except Exception:
        return None