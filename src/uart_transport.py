"""
File: uart_transport.py
Purpose:
    UART transmission for LAST node.
    Sends already-built packet bytes over serial.
"""

import serial

UART_PORT = "/dev/serial0"
BAUDRATE = 115200
PKT_SIZE=4
ser = serial.Serial(UART_PORT, BAUDRATE, timeout=1)

def send_uart_packet(packet_bytes):
    """
    packet_bytes must be raw bytes (not hex string)
    """
    try:
        ser.write(packet_bytes)
        print("UART TX:", packet_bytes.hex())
        return True
    except Exception as e:
        print("UART send failed:", e)
        return False

def receive_uart_packets(queue):

    while True:
        packet = ser.read(PKT_SIZE)

        # if len(packet) != PKT_SIZE:
        #     continue

        # if packet[0] != 0xAA:
        #     continue
        queue.put(packet)
        # if calculate_checksum(packet) != packet[6]:
        #     print("Checksum error")
        #     continue

        # seq_no = packet[1]
        # cmd = packet[2]

        # print("UART Packet | Dest:", seq_no, "| CMD:", cmd)

        # Only backward packets go into routing
        #if cmd == 0x02:
        