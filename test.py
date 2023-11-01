import picologger
logger = picologger.get_logger()
logger.log("############ Sensor tester is starting ############")


from micropython import const
from ustruct import unpack as unp
import utime
from machine import Pin,I2C
from bmp280 import *
import time
import ahtx0

# I2C for the Wemos D1 Mini with ESP8266
i2c_aht20_bmp280 = I2C(0, scl=Pin(21), sda=Pin(20))
utime.sleep_ms(100)

# Create the sensor object using I2C
sensor = ahtx0.AHT10(i2c_aht20_bmp280)
bmp = BMP280(i2c_aht20_bmp280, addr=0x77)
bmp.use_case(BMP280_CASE_INDOOR)


while True:
    print("\nAHT20 Temperature: %0.2f C" % sensor.temperature)
    print("AHT20 Humidity: %0.2f %%" % sensor.relative_humidity)
    #print("BMP280 Temperature: ", bmp.temperature)
    #print("BMP280 Pressure: ", bmp.pressure)
    pressure = bmp.pressure
    p_mbar = pressure / 100
    p_mmHg = pressure / 133.3224
    temperature = bmp.temperature
    print("Temperature: {} C".format(temperature))
    print("Pressure: {} Pa, {} mbar, {} mmHg".format(pressure, p_mbar, p_mmHg))

    #print(bme.values)
    utime.sleep(1)

