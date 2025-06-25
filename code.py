# built-in modules
import asyncio
import sys
import time
import os
import json
from asyncio import create_task, gather, run, sleep as async_sleep

# adafruit- & board-modules
import adafruit_scd30
import adafruit_vl53l1x
import adafruit_tsl2591
import adafruit_bme680
import adafruit_sht31d
import board
import neopixel
import wifi
import adafruit_connection_manager
import adafruit_requests
import adafruit_ntp
import adafruit_tca9548a

# custom modules
from devices import device_list

# custom functions & helpers
from functions import ntp_to_datestr, scan_i2c, load_devices, \
                      get_timezone_value_by_timezone_str, \
                      setup_devices, str_to_class


# device debug-variables
debug_tsl2591 = False
debug_bme680 = False
debug_scd30 = False
debug_sht30 = False

# device-id debug variable
debug_device_id = False

# netinfo debug variable
debug_netinfo = False

# --- defining local variables ---

# i2c addresses
addresses = []

# devices list
devices = []

# loaded class list
class_collection = []

# list of failed devices - device names
failed = []

# local datetime object
current_datetime = None

# loop-running variable
monitor_enabled = True


device_id = os.getenv('DEVICE_ID')
if debug_device_id:
    print(f"DEVICE-ID: {device_id}")

if debug_netinfo:
    print(f"Connecting to {os.getenv('CIRCUITPY_WIFI_SSID')}")

wifi.radio.connect(
    os.getenv("CIRCUITPY_WIFI_SSID"),
    os.getenv("CIRCUITPY_WIFI_PASSWORD")
)

if debug_netinfo:
    print(f"Connected to {os.getenv('CIRCUITPY_WIFI_SSID')}!")
    # wifi.radio.ipv4_dns = ipaddress.IPv4Address("192.168.137.64")
    print(f"ipv4_address: {wifi.radio.ipv4_address}")
    print(f"ipv4_dns: {wifi.radio.ipv4_dns}")

# setup socket-pool
pool = adafruit_connection_manager.get_radio_socketpool(wifi.radio)

# setup board-led
pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)

# setup ssl_context for requests
ssl_context = adafruit_connection_manager.get_radio_ssl_context(wifi.radio)

# setup requests obj
requests = adafruit_requests.Session(pool, ssl_context=ssl_context)

# get current rssi raw-level (dBm)
rssi = wifi.radio.ap_info.rssi

# Specify the timezone you want to get the offset for (e.g., 'Europe/Berlin')
timezone = "Europe/Berlin"

# timezone str to timezone value (int)
timezone_value = get_timezone_value_by_timezone_str(timezone)

# gmt +2 | Europe Berlin
ntp = adafruit_ntp.NTP(pool, tz_offset=timezone_value)

web_protocol = "http"
web_ip_port = "192.168.137.51:3003"
web_post_endpoint = "/sensor-post"


web_server = f"{web_protocol}://{web_ip_port}"

# POST URLs
JSON_POST_URL = f"{web_server}{web_post_endpoint}"

# init i2c
i2c = board.STEMMA_I2C()

mux_channel_num = 8

# Define a mapping from channel count to class
mux_classes = {
    4: adafruit_tca9548a.PCA9546A,
    8: adafruit_tca9548a.TCA9548A
}

# Get the correct class
mux_class = mux_classes.get(mux_channel_num)

# Check if class is valid
if mux_class is None:
    raise ValueError(f"Unsupported mux_channel_num: {mux_channel_num}")

# Instantiate the multiplexer
mux = mux_class(i2c)

channels = {}
for i in range(mux_channel_num):
    channels[str(i)] = []

address_to_sensor = {
    "0x29": "tsl2591,vl53l1x",
    "0x61": "scd30",
    "0x44": "sht30",
    "0x77": "bme680"
}

sensor_at_channel = {}

for channel in range(mux_channel_num):
    if mux[channel].try_lock():
        addresses = mux[channel].scan()
        for address in addresses:
            hex_addr = hex(address)
            if hex_addr in ["0x36", "0x70"]:
                continue  # skip these addresses

            if hex_addr not in channels[str(channel)]:
                sensor_name = address_to_sensor.get(hex_addr)
                if "," in sensor_name:
                    sensor_name = sensor_name.split(",")
                if isinstance(sensor_name, str):
                    # print(f"channel {channel}: {sensor_name}")
                    sensor_at_channel[str(channel)] = sensor_name
                if isinstance(sensor_name, list):
                    sensor_at_channel[str(channel)] = sensor_name[0]
                # else:
                #    print(f"channel {channel}: unknown sensor at {hex_addr}")

                channels[str(channel)].append(hex_addr)
        mux[channel].unlock()

# print(channels)
# print(sensor_at_channel)


failed = []
class_collection = []

debug_load_devices = True
debug_setup_devices = False

for dev_name, dev_data in device_list.items():
    # print(f"sensor: {dev_name}")
    # print(dev_data)
    lib_name = dev_data["import_name"]
    # print(lib_name)
    if debug_load_devices:
        print("\n")
        print(f">> DEBUG | load_device classes: importing: {lib_name}")

    import_name = dev_data.get('import_name')
    class_name = dev_data.get('class_name')

    # create class_type str from devive_object dict
    class_type = f"{import_name}.{class_name}"
    # print(f"class_type: {class_type}")

    cls_: class_type = None

    # -- replacing load_devices
    devices.append({
        dev_name: __import__(lib_name),
        "import_name": import_name,
        "class_name": class_name,
        "class_type": class_type
    })

for channel, sensor in sensor_at_channel.items():
    # print(f"channel: {channel}")
    # print(f"  sensor at channel: {sensor}")

    for dev_name, dev_data in device_list.items():
        if dev_name == sensor:
            import_name = dev_data.get('import_name')
            class_name = dev_data.get('class_name')

            # create class_type str from devive_object dict
            class_type = f"{import_name}.{class_name}"
            # print(f"class_type: {class_type}")

            cls_: class_type = None

            device_module = None
            try:
                # get device module by name from imported libs
                device_module = next(d[dev_name] for d in devices if dev_name in d)
            except StopIteration as stop_iteration:
                print("Err: STOP ITERATION")
                pass

            if device_module is None:
                failed.append(import_name)

            # -- replacing setup_devices

            # init device class
            cls_: class_type = str_to_class(
                device_module,
                class_name
            )(mux[int(channel)])

            device_object: dict = device_list.get(dev_name) if dev_name in device_list else False

            str_to_class(
                sys.modules.get("device_setup"),
                device_object.get('init')
            )(cls_)

            if debug_setup_devices:
                print(f"adding {dev_name} to class collection")

            # append class to class collection
            class_collection.append({
                dev_name: cls_
            })

# print("failed:")
# print(failed)

# print("class collection:")
# print(class_collection)


current_t = None
heater_diff = 0


async def monitor_sensors():
    global current_datetime, monitor_enabled, device_id, current_t, heater_diff
    while monitor_enabled:
        try:
            datetime = ntp.datetime
            if datetime != current_datetime:
                current_datetime = datetime

        except OSError as e:
            print(e)
            time.sleep(30)
            # microcontroller.reset()
            pass

        for device_class in class_collection:
            for device_name, module_class in device_class.items():
                if device_name == "vl53l1x":
                    module_class: adafruit_vl53l1x.VL53L1X = module_class

                    module_class.start_ranging()

                    await async_sleep(.1)

                    if module_class.data_ready:

                        distance = module_class.distance

                        data_json = {
                            "sensor": device_name,
                            "data": f"{distance} cm",
                            "datetime": ntp_to_datestr(current_datetime)
                        }

                        # print debug sensor json
                        print(data_json)

                        try:
                            with requests.post(JSON_POST_URL, data=data_json, timeout=1) as response:
                                if response.status_code == 200:
                                    print(f"{ntp_to_datestr(current_datetime)}: {device_name}: POST: OK")

                        except RuntimeError as e:
                            print(f"Exception: {e}")
                            time.sleep(5)
                            # microcontroller.reset()

                        except Exception as e:
                            print(f"Exception: {e}")
                            time.sleep(2)
                            # microcontroller.reset()
                        module_class.clear_interrupt()
                    else:
                        print("not ready")

                    await async_sleep(.5)

                elif device_name == "scd30":
                    # noinspection PyTypeChecker
                    # because it's the expected Type
                    module_class: adafruit_scd30.SCD30 = module_class
                    module_class.measurement_interval = 10

                    data_ready = module_class.data_available
                    if data_ready:
                        sensor_data: dict = {
                            "co2": module_class.CO2,
                            "temperature": module_class.temperature,
                            "temperature_offset": module_class.temperature_offset,
                            "measurement_interval": module_class.measurement_interval,
                            "self_calibration_enabled": module_class.self_calibration_enabled,
                            "ambient_pressure": module_class.ambient_pressure,
                            "altitude": module_class.altitude
                        }

                        data_json = {
                            "device_id": device_id,
                            "sensor": device_name,
                            "data": json.dumps(sensor_data),
                            "datetime": ntp_to_datestr(current_datetime)
                        }

                        if debug_scd30:
                            print(data_json)

                        try:
                            with requests.post(JSON_POST_URL, data=data_json, timeout=1) as response:
                                if response.status_code == 200:
                                    print(f"{ntp_to_datestr(current_datetime)}: {device_name}: POST: OK")
                                else:
                                    print(f"other than 200: {response.status_code}")

                        except RuntimeError as e:
                            print(f"RException: {e}")
                            # time.sleep(5)

                        except Exception as e:
                            print(f"Exception: {e}")
                            # time.sleep(2)

                elif device_name == "bme680":
                    # noinspection PyTypeChecker
                    # because it's the expected Type
                    module_class: adafruit_bme680.Adafruit_BME680_I2C = module_class

                    temperature_offset = -5

                    bme680_temperature = module_class.temperature + temperature_offset
                    bme680_gas = module_class.gas
                    bme680_relative_humidity = module_class.relative_humidity
                    bme680_pressure = module_class.pressure
                    bme680_altitude = module_class.altitude

                    sensor_data = {
                        "temperature": bme680_temperature,
                        "gas": bme680_gas,
                        "relative_humidity": bme680_relative_humidity,
                        "pressure": bme680_pressure,
                        "altitude": bme680_altitude
                    }

                    data_json = {
                        "device_id": device_id,
                        "sensor": device_name,
                        "data": json.dumps(sensor_data),
                        "datetime": ntp_to_datestr(current_datetime)
                    }

                    """
                    data_json = {
                        "device_id": device_id,
                        "sensor": device_name,
                        "data": json.dumps(sensor_data),
                        "datetime": ntp_to_datestr(current_datetime)
                    }
                    """

                    if debug_bme680:
                        print(data_json)

                    try:
                        with requests.post(JSON_POST_URL, data=data_json, timeout=1) as response:
                            if response.status_code == 200:
                                print(f"{ntp_to_datestr(current_datetime)}: {device_name}: POST: OK")
                            else:
                                print(f"other than 200: {response.status_code}")

                    except RuntimeError as e:
                        print(f"Exception: {e}")
                        time.sleep(5)

                    except Exception as e:
                        print(f"Exception: {e}")
                        time.sleep(2)

                elif device_name == "sht30":
                    data_json = {
                        "device_id": device_id,
                        "sensor": device_name,
                        "data": json.dumps({
                            "relative_humidity": module_class.relative_humidity,
                            "temperature": module_class.temperature,
                        }),
                        "datetime": ntp_to_datestr(current_datetime)
                    }
                    if current_t is None:
                        current_t = time.time()
                    if current_t is not None:
                        # print("heater diff:")
                        # print(heater_diff)
                        heater_diff = time.time() - current_t
                        if heater_diff >= 10:
                            # print(f"diff: {heater_diff}")

                            # print("-- >>>> heater on-off")
                            # print(">> heater on")
                            module_class.heater = True
                            time.sleep(1)
                            # print("<< heater off")
                            module_class.heater = False

                            current_t = time.time()
                            heater_diff = 0

                    if debug_sht30:
                        print(">> SHT30")
                        print(data_json)

                    try:
                        with requests.post(JSON_POST_URL, data=data_json, timeout=1) as response:
                            if response.status_code == 200:
                                print(f"{ntp_to_datestr(current_datetime)}: {device_name}: POST: OK")
                            else:
                                print(f"other than 200: {response.status_code}")

                    except RuntimeError as e:
                        print(f"Exception: {e}")
                        time.sleep(5)

                    except Exception as e:
                        print(f"Exception: {e}")
                        time.sleep(2)

                elif device_name == "tsl2591":
                    # noinspection PyTypeChecker
                    # because it's the expected Type
                    module_class: adafruit_tsl2591.TSL2591 = module_class

                    try:
                        lux = module_class.lux

                        if debug_tsl2591:
                            print("TSL2591: Total light: {0}lux".format(lux))

                        infrared = module_class.infrared

                        if debug_tsl2591:
                            print("TSL2591: Infrared light: {0}".format(infrared))
                            # Infrared levels range from 0-65535 (16-bit)

                        visible = module_class.visible

                        if debug_tsl2591:
                            print("TSL2591: Visible light: {0}".format(visible))
                            # Visible-only levels range from 0-2147483647 (32-bit)

                        full_spectrum = module_class.full_spectrum
                        if debug_tsl2591:
                            print("TSL2591: Full spectrum (IR + visible) light: {0}".format(full_spectrum))
                            # Full spectrum (visible + IR) also range from 0-2147483647 (32-bit)

                        gain = module_class.gain
                        data_json = {
                            "device_id": device_id,
                            "sensor": device_name,
                            "data": json.dumps({
                                "total_light_lux": lux,
                                "infrared": infrared,
                                "visible": visible,
                                "full_spectrum": full_spectrum,
                                "gain": gain
                            }),
                            "datetime": ntp_to_datestr(current_datetime)
                        }

                        # print sensor json if debug switch enabled
                        if debug_tsl2591:
                            print(data_json)

                        try:
                            with requests.post(JSON_POST_URL, data=data_json, timeout=1) as response:
                                if response.status_code == 200:
                                    print(f"{ntp_to_datestr(current_datetime)}: {device_name}: POST: OK")
                                else:
                                    print(f"other than 200: {response.status_code}")

                        except RuntimeError as e:
                            print(f"Exception: {e}")
                            time.sleep(5)

                        except Exception as e:
                            print(f"Exception: {e}")
                            time.sleep(2)

                    except RuntimeError as e:
                        print(f"tsl2591 error: {e}")
                        if "Try to reduce" in str(e):
                            module_class.gain = adafruit_tsl2591.GAIN_LOW

        await async_sleep(3)


async def main():
    await gather(
        create_task(
            monitor_sensors()
        )
    )


if __name__ == '__main__':
    if len(failed) == 0:
        run(main())
