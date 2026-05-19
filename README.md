# Sage Algiz – Multi-Protocol Embedded IoT Gateway

Sage Algiz is a Raspberry Pi CM4 based event-driven embedded IoT gateway designed for reliable emergency event communication using BLE, Ethernet, Wi-Fi/BATMAN Mesh, LoRaWAN, and UART communication.

The system supports wearable beacon communication, dynamic routing, automatic node commissioning, BLE control services, and multi-interface failover for robust edge-network deployment.


## 📌 Overview

Sage Algiz is an **event-driven multi-communication IoT node system** designed to operate over:

* BLE (Bluetooth Low Energy)
* Ethernet (TCP)
* WiFi / BATMAN Mesh
* LoRa (SX1302)
* UART (STM32 communication)

It dynamically **routes packets**, **auto-configures mesh IP**, and supports **commissioning (auto sequence assignment)**.

## 🎯 Primary Use Case

Sage Algiz is designed for emergency communication and distributed IoT deployments where reliable event forwarding is critical.

Example scenarios:
- Wearable emergency beacon systems
- Industrial safety monitoring
- Fall detection systems
- Mesh-based edge communication
- Low-power event-triggered IoT devices
---
## 🔵 BLE Communication Flow

### Beacon → Gateway Communication

1. Wearable beacon advertises BLE packets containing:
   - Device ID
   - Event type
   - Status information

2. Gateway continuously scans as BLE Central.

3. Upon receiving advertisement:
   - Packet validation is performed
   - Event data is parsed
   - ACK/response is transmitted

4. If BLE communication fails for a timeout duration:
   - System switches to LoRaWAN fallback transmission

5. After transmission:
   - Beacon enters low-power sleep mode
     
## 🔄 Dual BLE Role Architecture

The gateway operates simultaneously as:

### BLE Central
- Scans nearby wearable beacon advertisements
- Receives event packets
- Handles beacon communication

### BLE Peripheral
- Advertises gateway identity
- Allows mobile application connectivity
- Accepts BLE GATT control/configuration commands
- Supports LED and device control operations

## 🛰️ LoRaWAN Fallback Logic

BLE communication is used as the primary low-power event transport mechanism.

If BLE delivery becomes unavailable:
- Beacon automatically switches to LoRaWAN transmission
- Gateway receives packets using SX1302 concentrator
- Events continue forwarding through alternate communication paths
### Forward Path Priority

  BLE Event → Ethernet → BATMAN Mesh → LoRaWAN
  
  Routing decisions are based on interface availability and communication priority.

  Priority Order:
  1. Ethernet
  2. BATMAN Mesh / Wi-Fi
  3. LoRaWAN

  This provides:
  - automatic failover
  - improved reliability
  - redundant communication paths

## 🔋 Power Reliability

The gateway supports:
- PoE (Power over Ethernet)
- Battery backup operation

If PoE power becomes unavailable:
- System automatically switches to battery power
- Communication services continue without interruption

This ensures reliable operation during power failures.

## 🧠 Block Diagram (RPI CM4 ↔ SX1302 LoRaWAN HAT ↔ Sensors)

```
                                  +-------------------+                        +----------------------+
                                  |     RPi CM4       |                        |  SX1302 LoRaWAN HAT  |
                                  |                   |                        |                      |
                                  |  - BLE (DBus)     |          SPI           |  - LoRa Gateway      |
 +------------------+             |  - Ethernet       | <--------------------> |  - Packet Forwarder  |
 |   Sensors        |             |  - WiFi / Mesh    |                        +----------------------+
 | (Future Support) |<----------->|  - UART (STM32)   |                                   
 +------------------+             |  - GPIO (LED)     |                                   
                                  +---------+---------+                                   
                                            |                                            
                                           UART
                                            |                                               
                                            v                                             
                                      +-------------+                              
                                      |   STM32     |                              
                                      | (Control)   |                              
                                      +-------------+                              
```

## 🧠 Core Architecture

### 🔹 Event Driven Flow

```
[BLE / LoRa / UART / Ethernet]
            ↓
      payload_queue
            ↓
    forwarding_worker
            ↓
 Routing Decision Engine
```

---

## ⚙️ Features

* ✅ Automatic node commissioning (SEQ assignment)
* ✅ Dynamic BATMAN mesh IP based on seq_no
* ✅ Multi-path routing (Ethernet → Mesh → LoRa fallback)
* ✅ BLE GATT control (LED + config)
* ✅ UART communication with STM32
* ✅ LoRa packet forwarding
* ✅ Event-based config change detection (watchdog)

---

## 📁 Project Structure

```
main.py                → Entry point
node_server.py         → Unified TCP server
commission_client.py   → Commission request sender
mesh_monitor.py        → Auto mesh IP updater
packet_builder.py      → Packet creation
uart_transport.py      → UART TX/RX
glow.py                → LED control
ble_advertiser.py      → BLE advertising
sage_control.py        → BLE GATT service
config_manager.py      → Config handling
```

---

## 🔌 Supported Packet Types

### 1️⃣ Control Packet

```
| SOF | CMD | LEN | CRC |
CMD: 0x03 → Request SEQ
```

---

### 2️⃣ UART Packet (Backward)

```
| SOF | CMD | SEQ | R | G | B | CRC |
CMD: 0x02 → LED control
```

---

### 3️⃣ BLE Packet (Forward)

```
| SOF | CMD | LEN | PAYLOAD | CRC |
CMD: 0x01 → Forward data
```

---

### 4️⃣ LoRa Packet

```
| SOF | CMD | LEN | RAW_LORA_DATA | CRC |
```

---

## 🔄 Routing Logic

### Forward Path (BLE → Gateway)

```
BLE → Ethernet → BATMAN → LoRa
```

### Backward Path (Gateway → Node)

```
Ethernet → BATMAN → LoRa → UART
```

---

## 🧾 Commissioning Flow

### FIRST Node

* Always assigned:

```
SEQ = 1
```

### MIDDLE / LAST Node

1. Send TCP request:

```
COMMISSION_REQUEST
```

2. Receive:

```
COMMISSION_RESPONSE → assigned_seq_no
```

3. Save in:

```
config.json
```

---

## 📡 Mesh Networking (BATMAN)

### 🔹 Auto IP Mapping

```
seq_no → IP

1 → 192.168.10.1
2 → 192.168.10.2
3 → 192.168.10.3
...
```

---

### 🔹 Mesh Scripts

#### mesh_init.sh

```
sudo nmcli device set wlan0 managed no
sudo ip addr flush dev wlan0
sudo ip link set wlan0 down
sudo iw dev wlan0 set type ibss
sudo ip link set wlan0 up
sudo iw dev wlan0 ibss join mesh_net 5180
sudo batctl if add wlan0
sudo ip link set up dev bat0
```

---

#### mesh_set_ip.sh

```
sudo ip addr flush dev bat0
sudo ip addr add <IP>/24 dev bat0
```

---

## 🔍 Mesh Monitor (Auto IP Update)

* Watches `config.json`
* Detects `seq_no` changes
* Executes:

```
init_mesh()
update_mesh_ip(seq_no)
```

---

## 📶 BLE Features

### Advertising Name

```
ALGIZ-<MAC_ADDRESS>
```

---

### GATT Commands

#### CMD 4 → Assign SEQ

```
| SOF | CMD | SEQ | FIRST | MIDDLE | LAST |
```

#### CMD 5 → LED Control

```
| SOF | CMD | SEQ | R | G | B |
```

---

## 🔌 UART Communication

### TX

```
send_uart_packet(packet)
```

### RX

```
receive_uart_packets(queue)
```

---

## 📡 LoRa Integration

* Uses:

```
sx1302_hal packet_forwarder
```

* UDP Listener:

```
127.0.0.1:1701
```

---

## 💡 LED Control

```
control_led(R, G, B)
```

* Any value > 0 → ON
* 0 → OFF

---

## 🧪 Running the Project

### Step 1: Activate venv

```
source venv/bin/activate
```

### Step 2: Run main

```
sudo venv/bin/python main.py
```

---

## 🔧 Command Reference (Quick Overview)

* CMD 0x01 → Forward data packet (BLE → downstream routing)
  Full Packet Format: | SOF (0xAA) | CMD (0x01) | LEN | PAYLOAD | CRC |

* CMD 0x02 → Backward packet for LED control (destination-based routing)
  Full Packet Format: | SOF (0xAA) | CMD (0x02) | SEQ | R | G | B | CRC |

* CMD 0x03 → Request / respond with SEQ number over UART
  Full Packet Format: | SOF (0xAA) | CMD (0x03) | LEN | SEQ | CRC |

* CMD 0x04 → Manual SEQ assignment via BLE (includes role flags: FIRST / MIDDLE / LAST)
  Full Packet Format: | SOF (0xAA) | CMD (0x04) | SEQ | FIRST_FLAG | MIDDLE_FLAG | LAST_FLAG |

* CMD 0x05 → LED control via BLE (RGB values with destination SEQ)
  Full Packet Format: | SOF (0xAA) | CMD (0x05) | SEQ | R | G | B |

* BLE → Handles Bluetooth Low Energy communication for control and data input

* UART → Serial communication with STM32 for packet transmission and reception

* Ethernet (TCP) → Primary wired communication between nodes

* BATMAN Mesh → Wireless mesh networking fallback using dynamic IP routing

* LoRa → Long-range communication fallback using SX1302 packet forwarder

* Commissioning → Assigns sequence number (SEQ) to nodes during setup

* GATT → BLE service used for configuration and LED control

* Advertisement → Broadcasts device identity over BLE

* Payload Queue → Central buffer for all incoming packets

* Forwarding Worker → Core routing engine deciding packet path

* Mesh Monitor → Watches config changes and updates mesh IP dynamically

## 🔄 Runtime Flow

### 🚀 Startup

1. Read jumper → role
2. Start BLE stack
3. Commission if needed
4. Start node server
5. Start producers (BLE, LoRa, UART)
6. Start forwarding worker
7. Start mesh monitor

---

### 🔁 During Runtime

* Incoming data → queue
* Routing decision
* Failover handling
* Config changes → auto mesh update

---

## ⚠️ Failover Priority

### Forward:

```
Ethernet → BATMAN → LoRa
```

### Backward:

```
Ethernet → BATMAN → LoRa → UART
```

---

## 🧹 Stop the Program

```
pkill -f main.py
```

---

## 📌 Notes

* Mesh IP updates dynamically (no reboot required)
* Commissioning is one-time unless config is deleted
* Watchdog handles live config changes
* BLE + UART + LoRa run concurrently

---

## 🔥 Future Improvements

* MQTT integration
* integrating with sensors

---
