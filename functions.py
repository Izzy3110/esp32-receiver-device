import time
import sys
import re
from devices import device_list
from device_setup import \
    BME680Setup, \
    TSL2591Setup, \
    Vl53l1xSetup

# setup_device debug
debug_setup_devices = True


def setup_devices(i2c_instance, device_list: list, devices: list, devices_to_load: list | None = None):
    failed = []
    class_collection = []

    if devices_to_load is not None and len(devices_to_load) > 0:
        pass

    print("# DEVICES")
    for d_ in devices:
        print(d_)
    print(" ---")
    print("")

    for device_l in devices_to_load:
        if device_l in device_list.keys():
            device_name = device_l
            device_object: dict = device_list.get(device_l) if device_name in device_list else False
            if not isinstance(device_object, bool):
                import_name = device_object.get('import_name')
                class_name = device_object.get('class_name')

                # create class_type str from devive_object dict
                class_type = f"{import_name}.{class_name}"
                print(f"class_type: {class_type}")

                device_module = None
                try:
                    # get device module by name from imported libs
                    device_module = next(d[device_name] for d in devices if device_name in d)
                except StopIteration as stop_iteration:
                    print("Err: STOP ITERATION")
                    pass

                if device_module is None:
                    failed.append(import_name)

                print("")
                print(i2c_instance)
                print(device_module)
                print(device_object["class_name"])
                print("")

                # init device class
                cls_: class_type = str_to_class(
                    device_module,
                    device_object["class_name"]
                )(i2c_instance)

                str_to_class(
                    sys.modules.get("device_setup"),
                    device_object.get('init'))(cls_)

                if debug_setup_devices:
                    print(f"adding {device_name} to class collection")

                # append class to class collection
                class_collection.append({
                    device_name: cls_
                })
                
    # check and output failed list of devices
    if len(failed) > 0:
        print(f"failed: {failed}")

        # scan i2c addresses
        if i2c_instance.try_lock():
            print("Sensor I2C addresses:", [hex(x) for x in i2c_instance.scan()])
            i2c_instance.unlock()
    return class_collection, failed


def get_timezone_value_by_timezone_str(timezone_str):
    timezone_offsets = {
        "Europe/Berlin": 2,
        "UTC": 0,
        "America/New_York": -4,
        "Asia/Kolkata": 5.5,
        # Add more as needed
    }

    return timezone_offsets.get(timezone_str, 0)  # Default to 0 if not found


def ntp_to_datestr(datetime_: struct_time):
    mon = datetime_.tm_mon
    if len(str(mon)) == 1:
        mon = '0' + str(mon)

    day = datetime_.tm_mday
    if len(str(day)) == 1:
        day = '0' + str(day)

    year = datetime_.tm_year

    hour = datetime_.tm_hour
    if len(str(hour)) == 1:
        hour = '0' + str(hour)

    minutes = datetime_.tm_min
    if len(str(minutes)) == 1:
        minutes = '0' + str(minutes)
    sec = datetime_.tm_sec
    if len(str(sec)) == 1:
        sec = '0' + str(sec)

    return f"{year}-{mon}-{day} {hour}:{minutes}:{sec}"


def closest_rssi_level(rssi, rssi_levels):
    closest_level = None
    min_difference = float('inf')  # Initialize with infinity to find the minimum difference

    for level in rssi_levels:
        difference = abs(level - rssi)
        if difference < min_difference:
            min_difference = difference
            closest_level = level

    return rssi_levels[closest_level]


def str_to_class(obj, classname):
    return getattr(obj, classname)


def scan_i2c(i2c, addresses, debug=False):
    while not i2c.try_lock():
        pass

    try:
        addresses_ = i2c.scan()
        for addr in addresses_:
            addresses.append(hex(addr))
        if debug:
            print(
                "I2C addresses found:"
                , end='')
            for i2c_addr in addresses:
                print(i2c_addr)
        time.sleep(2)

    finally:  # unlock the i2c bus when ctrl-c'ing out of the loop
        i2c.unlock()

    return addresses


def load_devices(addresses, devices, debug=False):
    print("---")
    print("# load devices - addresses")
    print(addresses)
    print("---")

    # debug_load_devices
    for addr in addresses:
        for dev_name, dev_data in device_list.items():
            lib_name = dev_data["import_name"]
            if addr == hex(dev_data["i2c_addr"]):
                if debug:
                    print(f"DEBUG | load_devices: importing: {lib_name}")

                devices.append({
                    dev_name: __import__(lib_name)
                })
    return devices
