import adafruit_vl53l1x
import adafruit_tsl2591
import adafruit_bme680
import adafruit_scd30
import adafruit_sht31d

from devices import device_list


class SHT30Setup:
    def __init__(self, class_object: adafruit_sht31d.SHT31D):
        pass


class SCD30Setup:
    def __init__(self, class_object: adafruit_scd30.SCD30):
        class_object.reset()


class BME680Setup:
    def __init__(self, class_object: adafruit_bme680.Adafruit_BME680_I2C):
        class_object.sea_level_pressure = 1013.25

        pass


class TSL2591Setup:
    def __init__(self, class_object: adafruit_tsl2591.TSL2591):
        # Sensor Integration Time
        class_object.integration_time = adafruit_tsl2591.INTEGRATIONTIME_600MS
        # Sensor Gain
        class_object.gain = adafruit_tsl2591.GAIN_MED


class Vl53l1xSetup:
    def __init__(self, class_object: adafruit_vl53l1x.VL53L1X):
        # Sensor Distance Mode - 2(long) 1(short)
        class_object.distance_mode = 2
        # Sensor Timing
        class_object.timing_budget = 100

        if "vl53l1x" in device_list:
            print("target_i2c_addr" in device_list["vl53l1x"])

        model_id, module_type, mask_rev = class_object.model_info

        print("VL53L1X: Model ID: 0x{:0X}".format(model_id))
        print("VL53L1X: Module Type: 0x{:0X}".format(module_type))
        print("VL53L1X: Mask Revision: 0x{:0X}".format(mask_rev))
        print("VL53L1X: Distance Mode: ", end="")

        if class_object.distance_mode == 1:
            print("SHORT")
        elif class_object.distance_mode == 2:
            print("LONG")
        else:
            print("UNKNOWN")
        print("VL53L1X: Timing Budget: {}".format(class_object.timing_budget))

