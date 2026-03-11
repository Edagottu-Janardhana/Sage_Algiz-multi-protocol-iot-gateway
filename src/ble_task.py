"""
Single-shot BLE process
"""

# import asyncio
# from bleak import BleakScanner, BleakClient
# from packet_builder import build_packet

# TARGET_NAME = "SAGE_BLE_LORA"
# SCAN_TIME = 10

# TX_CHAR_UUID = "12345678-1234-5678-9abc-123456789abd"
# RX_CHAR_UUID = "12345678-1234-5678-9abc-123456789abe"

# found_device = None


# def detection_callback(device, advertisement_data):
#     global found_device
#     if device.name == TARGET_NAME and found_device is None:
#         found_device = device


# async def ble_once(queue):
#     global found_device
    
#     found_device = None

#     print("[BLE] Scanning...")

#     scanner = BleakScanner(detection_callback)
#     await scanner.start()

#     start = asyncio.get_event_loop().time()

#     while True:
#         if found_device:
#             break

#         if asyncio.get_event_loop().time() - start > SCAN_TIME:
#             await scanner.stop()
#             print("[BLE] Scan timeout")
#             return

#         await asyncio.sleep(0.1)

#     await scanner.stop()

#     try:
#         async with BleakClient(found_device.address, timeout=20) as client:
#             print("[BLE] Connected")

#             data = await client.read_gatt_char(TX_CHAR_UUID)

#             payload = data.hex()
#             print("Packet received in ble_task.py in hex:", payload)
#             packet_bytes = build_packet(0x01, data.hex())
#             #payload_queue.put(packet_bytes)

#             await client.write_gatt_char(RX_CHAR_UUID, b'A', response=False)

#             # Small stabilization delay
#             await asyncio.sleep(1.0)

#             print("[BLE] ACK sent")

#         print("[BLE] Disconnected")

#         queue.put(packet_bytes)

#     except EOFError:
#         pass

#     except Exception as e:
#         print("[BLE] Error:", repr(e))

# def ble_entry(queue):
#     print("=== BLE Continuous Process Started ====")

#     while True:
#         try:
#             asyncio.run(ble_once(queue))
#         except Exception as e:
#             print("[BLE] Loop error:", repr(e))

#         # Small delay before restarting scan
#         import time
#         time.sleep(0.5)

"""
Continuous BLE process
"""

import asyncio
import time
from bleak import BleakScanner, BleakClient
from packet_builder import build_packet

TARGET_NAME = "SAGE_BLE_LORA"
SCAN_TIME = 8

TX_CHAR_UUID = "12345678-1234-5678-9abc-123456789abd"
RX_CHAR_UUID = "12345678-1234-5678-9abc-123456789abe"

async def ble_once(queue):

    print("[BLE] Scanning...")

    try:
        device = await BleakScanner.find_device_by_filter(
            lambda d, ad: d.name == TARGET_NAME,
            timeout=SCAN_TIME
        )

        if not device:
            print("[BLE] Scan timeout")
            return

        print("[BLE] Found device:", device.address)
        await asyncio.sleep(0.3)
        async with BleakClient(device.address, timeout=15) as client:

            print("[BLE] Connected")

            data = await client.read_gatt_char(TX_CHAR_UUID)

            payload = data.hex()
            print("Packet received:", payload)

            packet_bytes = build_packet(0x01, payload)

            await client.write_gatt_char(RX_CHAR_UUID, b'A', response=False)

            await asyncio.sleep(0.6)

            print("[BLE] ACK sent")

        print("[BLE] Disconnected")

        queue.put(packet_bytes)

    except Exception as e:
        print("[BLE] Error:", repr(e))


def ble_entry(queue):

    print("=== BLE Continuous Process Started ===")

    while True:

        try:
            asyncio.run(ble_once(queue))
        except Exception as e:
            print("[BLE] Loop error:", repr(e))

        time.sleep(0.3)