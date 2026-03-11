#!/usr/bin/env python3

import dbus
import dbus.mainloop.glib
import dbus.service
from gi.repository import GLib
import RPi.GPIO as GPIO

from config_manager import has_sequence, save_config

LED_PIN = 21
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT)

BLUEZ_SERVICE_NAME = 'org.bluez'
GATT_MANAGER_IFACE = 'org.bluez.GattManager1'
DBUS_OM_IFACE = 'org.freedesktop.DBus.ObjectManager'
DBUS_PROP_IFACE = 'org.freedesktop.DBus.Properties'
GATT_SERVICE_IFACE = 'org.bluez.GattService1'
GATT_CHRC_IFACE = 'org.bluez.GattCharacteristic1'

NODE_ROLE = None
# ---------------- Application ----------------

class Application(dbus.service.Object):
    def __init__(self, bus):
        self.path = '/'
        self.services = []
        super().__init__(bus, self.path)
        self.add_service(SageAlgizService(bus, 0))

    def add_service(self, service):
        self.services.append(service)

    @dbus.service.method(DBUS_OM_IFACE,
                         out_signature='a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        response = {}
        for service in self.services:
            response[service.get_path()] = service.get_properties()
            for ch in service.characteristics:
                response[ch.get_path()] = ch.get_properties()
        return response

# ---------------- Service ----------------

class Service(dbus.service.Object):
    PATH_BASE = '/org/sagealgiz/service'

    def __init__(self, bus, index, uuid):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.uuid = uuid
        self.primary = True
        self.characteristics = []
        super().__init__(bus, self.path)

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_characteristic(self, ch):
        self.characteristics.append(ch)

    def get_properties(self):
        return {
            GATT_SERVICE_IFACE: {
                'UUID': self.uuid,
                'Primary': self.primary,
                'Characteristics': dbus.Array(
                    [c.get_path() for c in self.characteristics],
                    signature='o')
            }
        }

    @dbus.service.method(DBUS_PROP_IFACE,
                         in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_SERVICE_IFACE:
            raise Exception('Invalid interface')
        return self.get_properties()[GATT_SERVICE_IFACE]

# ---------------- Characteristic ----------------

class Characteristic(dbus.service.Object):
    def __init__(self, bus, index, uuid, flags, service):
        self.path = service.path + '/char' + str(index)
        self.bus = bus
        self.uuid = uuid
        self.flags = flags
        self.service = service
        super().__init__(bus, self.path)

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def get_properties(self):
        return {
            GATT_CHRC_IFACE: {
                'Service': self.service.get_path(),
                'UUID': self.uuid,
                'Flags': self.flags
            }
        }

    @dbus.service.method(DBUS_PROP_IFACE,
                         in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_CHRC_IFACE:
            raise Exception('Invalid interface')
        return self.get_properties()[GATT_CHRC_IFACE]

# ---------------- Sage Algiz LED ----------------

class SageAlgizService(Service):
    UUID = '12345678-1234-5678-1234-56789abc0000'
    def __init__(self, bus, index):
        super().__init__(bus, index, self.UUID)
        self.add_characteristic(LedCharacteristic(bus, 0, self))

class LedCharacteristic(Characteristic):
    UUID = '12345678-1234-5678-1234-56789abc0001'
    def __init__(self, bus, index, service):
        super().__init__(bus, index, self.UUID, ['write'], service)

    @dbus.service.method(GATT_CHRC_IFACE,
                         in_signature='aya{sv}')
    # def WriteValue(self, value, options):
    #     cmd = bytes(value).decode().strip()
    #     print("BLE CMD:", cmd)
    #     if cmd == "1":
    #         GPIO.output(LED_PIN, GPIO.HIGH)
    #         print("LED ON")
    #     elif cmd == "0":
    #         GPIO.output(LED_PIN, GPIO.LOW)
    #         print("LED OFF")
    def WriteValue(self, value, options):

        packet = bytes(value)
        print("BLE RX:", packet.hex())

        # if len(packet) < 3:
        #     return

        sof = packet[0]
        cmd = packet[1]

        if sof != 0xAA:
            return

        # --------------------------------
        # CMD 4 → Manual SEQ assignment
        # Format: | SOF | CMD | SEQ | CRC |
        # --------------------------------
        if cmd == 0x04:

            if has_sequence():
                print("SEQ already assigned, ignoring BLE assign")
                return

            seq_no = packet[2]

            print("Assigning SEQ via BLE:", seq_no)
            print("Node role:", NODE_ROLE)

            save_config(seq_no, NODE_ROLE)

            print("SEQ saved to config.json")


# ---------------- Main ----------------

def find_adapter(bus):
    om = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, '/'),
                        DBUS_OM_IFACE)
    objects = om.GetManagedObjects()
    for path, ifaces in objects.items():
        if GATT_MANAGER_IFACE in ifaces:
            return path
    return None

# def main():
#     dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
#     bus = dbus.SystemBus()
#     adapter = find_adapter(bus)
#     if not adapter:
#         print("No BLE adapter found")
#         return

#     service_manager = dbus.Interface(
#         bus.get_object(BLUEZ_SERVICE_NAME, adapter),
#         GATT_MANAGER_IFACE)

#     app = Application(bus)
#     service_manager.RegisterApplication(app.path, {},
#         reply_handler=lambda: print("GATT registered"),
#         error_handler=lambda e: print("GATT error:", e))

#     print("BLE LED server running...")
#     GLib.MainLoop().run()

# if __name__ == '__main__':
#     main()
def register_gatt(bus, role):
    global NODE_ROLE
    NODE_ROLE = role

    adapter = find_adapter(bus)
    if not adapter:
        print("No BLE adapter found")
        return

    service_manager = dbus.Interface(
        bus.get_object("org.bluez", adapter),
        "org.bluez.GattManager1"
    )

    app = Application(bus)

    service_manager.RegisterApplication(
        app.path,
        {},
        reply_handler=lambda: print("GATT registered"),
        error_handler=lambda e: print("GATT error:", e)
    )