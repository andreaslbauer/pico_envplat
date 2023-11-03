import picologger
logger = picologger.get_logger()
logger.log("############ Unit Tester is starting ############")


from micropython import const
from ustruct import unpack as unp
import utime
from machine import Pin,I2C
from bmp280 import *
import time
import ahtx0

from sensorhelpers import persistedringbuffer

# I2C for the Wemos D1 Mini with ESP8266
i2c_aht20_bmp280 = I2C(0, scl = Pin(21), sda = Pin(20))
utime.sleep_ms(100)

# Create the sensor object using I2C
sensor = ahtx0.AHT10(i2c_aht20_bmp280)
bmp = BMP280(i2c_aht20_bmp280, addr=0x77)
bmp.use_case(BMP280_CASE_INDOOR)

def scani2c(bus, sdapin, sclpin):
    sda = machine.Pin(sdapin)
    scl = machine.Pin(sclpin)
    i2c = machine.I2C(bus, sda = sda, scl = scl, freq=400000)
    devices = i2c.scan()
     
    if len(devices) == 0:
        logger.log(f"No I2C devices on bus {bus} SDA Pin {sda} SCL Pin {scl}")
    else:
      logger.log(f"Found I2C devices on bus {bus} SDA Pin {sda} SCL Pin {scl}: {len(devices)}")
     
    for device in devices:  
        logger.log(f"Address: {hex (device)}")    

def test_i2c():
    scani2c(0, 20, 21)
    scani2c(1, 14, 15)

    logger.log(f"AHT20 Temperature: {sensor.temperature}")
    logger.log(f"AHT20 Humidity: {sensor.relative_humidity}")
    logger.log(f"BMP280 Temperature: {bmp.temperature}")
    logger.log(f"BMP280 Pressure: {bmp.pressure}")
    pressure = bmp.pressure
    p_mbar = pressure / 100
    p_mmHg = pressure / 133.3224
    temperature = bmp.temperature
    logger.log(f"BMP280 Pressure: {pressure} Pa, {p_mbar} mbar, {p_mmHg} mmHg")

def test_ringbuffer():
    rb = persistedringbuffer(3, "rbtest.txt")
    print("*** New buffer")
    rb.dump()
    
    print("*** Append 1")
    rb.append(1)
    print(f'getcurrent(): {rb.getcurrent()}')
    print(f'getNBack(1): {rb.getNBack(1)}')
    print(f'getNBack(2): {rb.getNBack(2)}')
    rb.dump()
    
    print("*** Append 2")
    rb.append(2)
    print(f'getcurrent(): {rb.getcurrent()}')
    print(f'getNBack(1): {rb.getNBack(1)}')
    print(f'getNBack(2): {rb.getNBack(2)}')
    rb.dump()
    
    print("*** Append 3")
    rb.append(3)
    print(f'getcurrent(): {rb.getcurrent()}')
    print(f'getNBack(1): {rb.getNBack(1)}')
    print(f'getNBack(2): {rb.getNBack(2)}')
    rb.dump()
    
    print("*** Append 4")
    rb.append(4)
    print(f'getcurrent(): {rb.getcurrent()}')
    print(f'getNBack(1): {rb.getNBack(1)}')
    print(f'getNBack(2): {rb.getNBack(2)}')
    rb.dump()
    
    print("*** Append 5")
    rb.append(5)
    print(f'getcurrent(): {rb.getcurrent()}')
    print(f'getNBack(1): {rb.getNBack(1)}')
    print(f'getNBack(2): {rb.getNBack(2)}')
    rb.dump()

    print("*** Append 6")
    rb.append(6)
    print(f'getcurrent(): {rb.getcurrent()}')
    print(f'getNBack(1): {rb.getNBack(1)}')
    print(f'getNBack(2): {rb.getNBack(2)}')
    rb.dump()


#test_i2c()
test_ringbuffer()
    

