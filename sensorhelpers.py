from ssd1306 import SSD1306_I2C
from machine import Pin, I2C, ADC
from picozero import pico_temp_sensor
import onewire, ds18x20
import ujson
import _thread
import picologger
logger = picologger.get_logger()

# helper class for the OLED display with 1306 chip
class oled_display:
    
    def __init__(self, i2c_id, sda_pin, scl_pin):
        self.i2c_id = i2c_id
        self.sda_pin = sda_pin
        self.scl_pin = scl_pin
        self.i2c = None
        self.oled = None

        try:
            #self.i2c = I2C(1, scl=Pin(15), sda=Pin(14), freq=400000)
            self.i2c = I2C(self.i2c_id, sda = Pin(self.sda_pin), scl = Pin(self.scl_pin), freq = 400000)
            self.oled = SSD1306_I2C(128, 64, self.i2c)
            logger.log("OLED 1306 display found and initialized")
            self.oled.text("OLED1306", 0, 0)
            self.oled.text("Found and", 0, 16)
            self.oled.text("initilized", 0, 32) 
            self.oled.show()

        except:
            logger.log("Unable to access OLED 1306 display")

    # print a string at the given row (0 through 5)
    def print(self, s, row):
        if (self.oled != None):
            #print("OLED: ", s)
            try:
                offset = 0
                if row > 0:
                    offset = (row - 1) * 12 + 16
                self.oled.text(s, 0, offset)
                self.oled.show()

            except:
                logger.log(f'Unable to print to OLED: {s}')

    # clear the display
    def clear(self):
        try:
            if (self.oled != None):
                self.oled.fill(0)
                self.oled.show()
                
        except Exception as e:
                logger.log(f'Unable to clear OLED: {e}')
            
# helper class for the DS18B20 temperature sensor
class ds18b20:
    
    def __init__(self, pin_id):
        self.sensor_pin = Pin(pin_id, Pin.IN)
        self.sensor = ds18x20.DS18X20(onewire.OneWire(self.sensor_pin))
        self.roms = self.sensor.scan()
        for sensor in self.roms:
            hexstr = bytes(sensor).hex()
            logger.log(f'DS18B20 Sensor found: {hexstr}')
        
    def sensor_count(self):
        return len(self.roms)
    
    def sensor(self):
        return self.sensor
    
    def roms(self):
        return self.roms

# helper for capacitive moisture sensor that is connected to ADC
class cap_soil_moisture:
    
    def __init__ (self, pin_id):
        self.pin_id = pin_id
        self.adc = ADC(Pin(self.pin_id))
        # Calibraton values
        self.min_moisture = 0
        self.max_moisture = 65535
        
    def getValue(self):
        return round((self.max_moisture - self.adc.read_u16()) * 100 /
                     (self.max_moisture - self.min_moisture), 2)

# helper for LDR that is connected to ADC   
class adc_light_sensor:
    
    def __init__ (self, pin_id):
        self.pin_id = pin_id
        self.adc = ADC(Pin(self.pin_id))
        # Calibraton values
        self.min_moisture = 0
        self.max_moisture = 65535
        
    def getValue(self):
        return self.adc.read_u16()
    
# ringbuffer class    
class ringbuffer:
    def __init__(self, capacity):
        self.capacity = capacity
        self.data = [None] * capacity
        self.size = 0
        self.head = 0

    def __len__(self):
        return self.size

    def append(self, item):
        if self.size < self.capacity:
            self.size += 1
        
        self.head = (self.head + 1) % self.capacity
        self.data[self.head] = item
        
    def __getitem__(self, idx):
        if idx < 0 or idx >= self.size:
            raise IndexError('Index out of range')
        return self.data[(self.head - self.size + idx + 1) % self.capacity]


# ringbuffer class    
class persistedringbuffer:
    def __init__(self, capacity, name):
        self.capacity = capacity
        self.name = name
        self.data = [None] * capacity
        self.size = 0
        self.head = 0
        self.load()

    def __len__(self):
        return self.size

    def save(self):
        try:
            filename = self.name
            file = open(filename, "w")
            idx = self.head
            ujson.dump(self.__dict__, file)                
            file.close()

        except Exception as e:
            logger.log(f'Unable to save data file {self.name}: {e}')


    def load(self):
        try:
            saved_capacity = self.capacity
            filename = self.name
            props = None
            with open(filename, "r") as file:
                props = ujson.load(file)

            for k,v in props.items():
                if (k != "lock"):
                    setattr(self, k, v)
            
            # fill up ring buffer with empty slots if needed
            for i in range(self.capacity, saved_capacity):
                self.data.append(None)
            
            self.capacity = saved_capacity                  
            file.close()
            
            logger.log(f'Loaded data file {self.name} with {self.size} data rows')

        except Exception as e:
            logger.log(f'Unable to load data file {self.name}: {e}')
        
        
    def json(self):
        json = ujson.dumps(self.__dict__)
        return json
    
    def d3json(self, client = None):
        try:
            if client == None:
                l = []
                idx = self.head
                for c in range(0, self.size):
                    try:
                        #idx = (idx + 1) % self.capacity
                        data = self.__getitem__(c)
                        r = {}
                        r['D'] = data['t']
                        r['T1'] = data['v'][0]
                        r['T12'] = data['v'][1]
                        r['M1'] = data['v'][2]
                        r['L1'] = data['v'][3]
                        r['T13'] = data['v'][4]
                        r['H1'] = data['v'][5]
                        r['T14'] = data['v'][6]
                        r['P1'] = data['v'][7]
                        l.append(r)
                    
                    except:
                        print("Unable to get data at ", c)
                    
                json = ujson.dumps(l)
                return json
            else:
                client.send('[')
                idx = self.head
                firstItem = True
                #print(self)
                for c in range(0, self.size):
                    data = self.__getitem__(c)
                    #print(data)
                    if data != None:
                        r = {}
                        r['D'] = data['t']
                        r['T1'] = data['v'][0]
                        r['T2'] = data['v'][1]
                        r['M'] = data['v'][2]
                        r['L'] = data['v'][3]
                        r['T3'] = data['v'][4]
                        r['H'] = data['v'][5]
                        r['T4'] = data['v'][6]
                        r['P'] = data['v'][7]
                        json = ujson.dumps(r)
                        #print(json)
                        if firstItem == False:
                            client.send(',')
                        firstItem = False
                        client.send(json + '\n')
                                    
                client.send(']')
                
        except Exception as e:
            logger.log(f'Unable to stream buffer as json: {self.name}: {e}')
            

    def append(self, item):
        try:
            if self.size < self.capacity:
                self.size += 1
            
            self.data[self.head] = item
            self.head = (self.head + 1) % self.capacity
            
            #logger.log(f'Appending data to ringbuffer {self.name} at {self.head} with size {self.size}')
            #logger.log(f'Data: {self.data}')

        except Exception as e:
            logger.log(f'Unable to append data item to ring buffer {self.name}: {e}')

    
    def getcurrent(self):
        return self.__getitem__(self.size - 1) 
    
    def dump(self):
        print(f'Size: {self.size}  Capacity: {self.capacity} Head: {self.head}')
        i = 0
        c = 0
        while i < self.capacity:
            data = self.data[c]
            if c == self.head:
                print(data['t'], data['v'], "<---- Head")
            else:
                print(data['t'], data['v'])
            c += 1
            if c >= self.size:
                c = 0
            i += 1
    
    def getNBack(self, n):
        if (n > self.size):
            return None
        
        idx = self.head - n - 1
        if (idx < 0):
            idx = idx + self.size
            
        return self.data[idx]
    
    def getrateofchange(self, col, r):
        print("----------------------------------")
        self.dump()
        data = self.__getitem__(0)
        t_now = data['t']
        print("Current: ", data['t'], data['v'])
        data = self.getNBack(2)
        if data != None:
            print("2 back: ", data['t'], data['v'])
            t_before = data['t']
            print(f'{t_now} - {t_before}')
        data = self.getNBack(5)
        if data != None:
            print("5 back: ", data['t'], data['v'])
                      
        return 0
        
    def getaverage(self, col):
        idx = self.head
        sum = 0.0
        count = 0.0
        for c in range(0, self.size):
            data = self.__getitem__(c)
            v = data['v'][col]
            count += 1.0
            sum += v
            
        return sum / count

    def getmin(self, col):
        idx = self.head
        minimum = 10000000.0
        for c in range(0, self.size):
            data = self.__getitem__(c)
            if data['v'][col] < minimum:
                minimum = data['v'][col]
            
        return minimum

    def getmax(self, col):
        idx = self.head
        maximum = -10000000.0
        for c in range(0, self.size):
            data = self.__getitem__(c)
            if data['v'][col] > maximum:
                maximum = data['v'][col]
            
        return maximum

    def __getitem__(self, idx):      
        idx = idx % self.capacity
        if idx < 0 or idx >= self.size:
            ringbuffer_lock.release()
            raise IndexError('Index out of range')
        
        returndata = self.data[(self.head - self.size + idx)]
        
        return returndata

class interleaver():
    
    def __init__(self, interleave):
        self.interleave_count = 0
        self.interleave = interleave
        
    def inc(self):
        r = (self.interleave_count == 0)
        self.interleave_count = (self.interleave_count + 1) % self.interleave
        return r
    
