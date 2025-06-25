import adafruit_sht31d
device_list = {
    "vl53l1x": {
        "i2c_addr": 0x29,
        "fallback_addr": 0x30,
        "class_name": "VL53L1X",
        "import_name": "adafruit_vl53l1x",
        "init": "Vl53l1xSetup"
    },
    "tsl2591": {
        "i2c_addr": 0x29,
        "class_name": "TSL2591",
        "import_name": "adafruit_tsl2591",
        "init": "TSL2591Setup"
    },
    "bme680": {
        "i2c_addr": 0x77,
        "class_name": "Adafruit_BME680_I2C",
        "import_name": "adafruit_bme680",
        "init": "BME680Setup"
    },
    "scd30": {
        "i2c_addr": 0x61,
        "class_name": "SCD30",
        "import_name": "adafruit_scd30",
        "init": "SCD30Setup"
    },
    "sht30": {
        "i2c_addr": 0x44,
        "class_name": "SHT31D",
        "import_name": "adafruit_sht31d",
        "init": "SHT30Setup"
    }
}
