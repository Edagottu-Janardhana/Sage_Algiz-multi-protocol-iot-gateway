#!/usr/bin/env python3
"""
Minimal BLE Advertiser for BlueZ (Raspberry Pi OS Lite)

- Uses LEAdvertisingManager1
- No unregister bug
- Works with BlueZ >= 5.6x
"""

import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib

BLUEZ_SERVICE_NAME = "org.bluez"
LE_ADVERTISING_MANAGER_IFACE = "org.bluez.LEAdvertisingManager1"
DBUS_PROP_IFACE = "org.freedesktop.DBus.Properties"

AD_PATH = "/com/sagealgiz/advertisement0"


class Advertisement(dbus.service.Object):
    def __init__(self, bus):
        self.path = AD_PATH
        self.bus = bus
        super().__init__(bus, self.path)

    def get_properties(self):
        return {
            "org.bluez.LEAdvertisement1": {
                "Type": "peripheral",
                "LocalName": "SAGE_ALGIZ_CONTROL",
                "ServiceUUIDs": ["12345678-1234-5678-1234-56789abcdef0"],
                "IncludeTxPower": True,
            }
        }

    @dbus.service.method(DBUS_PROP_IFACE,
                         in_signature="s",
                         out_signature="a{sv}")
    def GetAll(self, interface):
        if interface != "org.bluez.LEAdvertisement1":
            return {}
        return self.get_properties()["org.bluez.LEAdvertisement1"]


# def main():
#     dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
#     bus = dbus.SystemBus()

#     adapter_path = "/org/bluez/hci0"
#     ad_manager = dbus.Interface(
#         bus.get_object(BLUEZ_SERVICE_NAME, adapter_path),
#         LE_ADVERTISING_MANAGER_IFACE
#     )

#     advertisement = Advertisement(bus)

#     ad_manager.RegisterAdvertisement(
#         advertisement.path,
#         {},
#         reply_handler=lambda: print("✅ Advertisement registered"),
#         error_handler=lambda e: print("❌ Failed:", e)
#     )

#     print("📡 Advertising… Ctrl+C to stop")
#     GLib.MainLoop().run()


# if __name__ == "__main__":
#     main()
def register_advertisement(bus):

    adapter_path = "/org/bluez/hci0"

    ad_manager = dbus.Interface(
        bus.get_object("org.bluez", adapter_path),
        "org.bluez.LEAdvertisingManager1"
    )

    advertisement = Advertisement(bus)

    ad_manager.RegisterAdvertisement(
        advertisement.path,
        {},
        reply_handler=lambda: print("Advertisement registered"),
        error_handler=lambda e: print("Advertisement failed:", e)
    )