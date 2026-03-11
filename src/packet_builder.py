"""
packet_builder.py
------------------
Creates protocol packet:
| SOF | CMD | LEN | PAYLOAD | CRC |
"""

def build_packet(cmd, payload_hex):

    SOF = 0xAA

    # Convert payload from hex string to bytes
    payload_bytes = bytes.fromhex(payload_hex)

    length = len(payload_bytes)

    # Build packet without CRC
    packet = bytearray()
    packet.append(SOF)
    packet.append(cmd)
    packet.append(length)
    packet.extend(payload_bytes)

    # Calculate CRC (XOR)
    crc = 0
    for b in packet:
        crc ^= b

    packet.append(crc)

    return bytes(packet)

def build_seq_response_packet(cmd, current_seq):
    SOF = 0xAA

    payload_bytes = bytes([current_seq])  # one byte payload
    length = len(payload_bytes)

    packet = bytearray()
    packet.append(SOF)
    packet.append(cmd)
    packet.append(length)
    packet.extend(payload_bytes)

    # XOR CRC
    crc = 0
    for b in packet:
        crc ^= b

    packet.append(crc)

    return bytes(packet)

def build_lorawan_packet(cmd, payload_bytes):

    SOF = 0xAA

    length = len(payload_bytes)

    packet = bytearray()
    packet.append(SOF)
    packet.append(cmd)
    packet.append(length)
    packet.extend(payload_bytes)

    crc = 0
    for b in packet:
        crc ^= b

    packet.append(crc)

    return bytes(packet)