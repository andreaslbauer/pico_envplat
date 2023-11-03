# Raspberry pi pico Environmental Data Collector
# requires packages:
# ssd1306
# ahtx0


from machine import Pin, Timer, WDT, I2C
import time, utime
from time import sleep
from sensorhelpers import oled_display, ds18b20, cap_soil_moisture, adc_light_sensor, persistedringbuffer, interleaver
from bmp280 import *
import ahtx0
import network
import socket
from picozero import pico_temp_sensor, pico_led
import networking
from networking import connect
import gc, os, machine
import picologger
import micropython
logger = picologger.get_logger()
logger.log("############ EnvPlat is starting ############")

oled = oled_display(1, 14, 15)
oled.clear()

# set up the sensor classes
moisture_sensor = cap_soil_moisture(28)
light_sensor = adc_light_sensor(27)
temp_sensor = ds18b20(18)

# I2C for the AHT20 / BMP280 sensor
i2c_aht20_bmp280 = I2C(0, scl=Pin(21), sda=Pin(20))
aht20 = ahtx0.AHT10(i2c_aht20_bmp280)
bmp = BMP280(i2c_aht20_bmp280, addr=0x77)
bmp.use_case(BMP280_CASE_INDOOR)
sensor_count = temp_sensor.sensor_count() + 2
wdt = None

keep_running = True

# set up the ring buffers
sensor_il = interleaver(4)
savedata_il = interleaver(100)
shortterm_il = interleaver(2)
shortterm_rb = persistedringbuffer(240, "shorttermdata.txt")
midterm_il = interleaver(30)
midterm_rb = persistedringbuffer(240, "midtermdata.txt")
longterm_il = interleaver(5 * 60)
longterm_rb = persistedringbuffer(240, "longtermdata.txt")


def getTimeSeconds(timestring):
    seconds = int(timestring[0:4])
    seconds = seconds * 365 + int(timestring[5:7])
    seconds = seconds * 12 + int(timestring[8:10])
    seconds = seconds * 31 + int(timestring[11:13])
    seconds = seconds * 24 + int(timestring[14:16])
    seconds = seconds * 60 + int(timestring[17:19])
    return seconds
    

def getRateOfChange(buffer, n_back):
    d_now = buffer.getcurrent()
    d_before = buffer.getNBack(n_back)
    #print(f'getRateOfChange Now: {d_now} Before: {d_before}')
    if d_now != None and d_before != None:
        t_diff = getTimeSeconds(d_now['t']) - getTimeSeconds(d_before['t'])
        r = (d_now['v'][0] - d_before['v'][0]) / t_diff, (d_now['v'][1] - d_before['v'][1]) / t_diff, (d_now['v'][2] - d_before['v'][2]) / t_diff
        #print(r)
        return r

prev_mem_free = 0
def getSensorData():
    list = []
    temp_sensor.sensor.convert_temp()
    time.sleep(2)
    i = 0
    oled.clear()
    timestr = networking.getTimeStr()
    timedatestr = networking.getTimeDateStr()
    oled.print("At: " + timestr, 0)
    oledstr = "T:"
    for rom in temp_sensor.roms:
        temperature = round(temp_sensor.sensor.read_temp(rom), 2)
        list.append(temperature)
        oledstr +=  " " + str(temperature)
        
    oled.print(oledstr, 1 + i)
    i += 1
        
    moisture = moisture_sensor.getValue()
    list.append(moisture)
    
    brightness = light_sensor.getValue()
    list.append(brightness)
    
    # data from AHT20 sensor: temperature and humidity
    temp3 = aht20.temperature
    list.append(temp3)
    relative_humidity = aht20.relative_humidity
    list.append(relative_humidity)
    
    # data from BMP280 sensor: temperature and pressure
    temp4 = bmp.temperature
    list.append(temp4)
    pressure = bmp.pressure / 100
    list.append(pressure)
    
    # print values
    oled.print("M: " + str(moisture) + " " + str(brightness), i + 1)
    oled.print("H: " + str(round(relative_humidity, 1)) + " " + str(round(pressure, 2)), i + 2)
    oled.print("H: " + str(round(temp3, 2)) + " " + str(round(temp4, 2)), i + 3)
        
    global prev_mem_free
    mem_free = gc.mem_free()
    #logger.log(f'Memory free: {mem_free} diff: {mem_free - prev_mem_free}')
    prev_mem_free = mem_free
    
    # if we are running out of memory - restart
    if mem_free < 10000:
        logger.log(f'Out of memory, restart...')
        shortterm_rb.save()
        midterm_rb.save()
        longterm_rb.save()
        sleep(1)
        machine.reset()
        sleep(5)     
    
    return list

def collectSensorData(timer):
    
    global keep_running
    if keep_running:

        try:
            gc.collect()
            gc.threshold(gc.mem_free() // 4 + gc.mem_alloc())
            
            global wdt
            wdt.feed()
            
            global sensor_il
            if (sensor_il.inc()):
                #logger.log("Aquire data from sensors...")
                t = getSensorData()
                try:
                    temps = t
                    temp_record = {
                        't': networking.getTimeDateStr(),
                        'v': t
                        }

                    if shortterm_il.inc():
                        shortterm_rb.append(temp_record)

                    if midterm_il.inc():
                        midterm_rb.append(temp_record)
                        
                    if longterm_il.inc():
                        longterm_rb.append(temp_record)
                        
                    if savedata_il.inc():
                        shortterm_rb.save()
                        midterm_rb.save()
                        longterm_rb.save()
                        logger.log(f"Sensor data has been save to FS: {temp_record}")
                                                
                    #logger.log(f"Sensor data has been stored: {temp_record}")

                except Exception as e:
                    logger.log(f'Failure collecting sensor data: {e}')

        except Exception as e:
            logger.log(f'Data collection failed: {e}')
        



def webpage_header(client):
    sendFile("header.html", client)
    
def webpage_trailer(client):
    html = """
</body>
</html>
"""
    client.send(html)


def webpage_main(client):   
    webpage_header(client) 
    sendFile("main.html", client)
    webpage_trailer(client)
    
    
def webpage_big_display(client):   
    webpage_header(client)
    data = shortterm_rb.getcurrent()
    html = f'''
<meta http-equiv="refresh" content="10">
<div class="container">
<h2>
<table class="table table table-striped ">
  <tr></tr>
  <tr><td>Time</td><td>{data["t"]}</td></tr>
  <tr><td>Temperature 1</td><td>{round(data["v"][0], 2)}</td></tr>
  <tr><td>Temperature 2</td><td> {round(data["v"][1], 2)}</td></tr>
  <tr><td>Temperature 3</td><td> {round(data["v"][4], 2)}</td></tr>
  <tr><td>Temperature 4<td> {round(data["v"][6], 2)}</td></tr>
  <tr><td>Moisture</td><td> {round(data["v"][2], 1)}</td></tr>
  <tr><td>Light</td><td> {data["v"][3]}</td></tr>
  <tr><td>Humidity</td><td> {round(data["v"][5], 1)}</td></tr> 
  <tr><td>Pressure</td><td> {round(data["v"][7], 2)}</td></tr>
</tr>
</table>
</h2>
</div>
</p>
'''
    client.send(html)
    webpage_trailer(client)
    
    
def webpage_stats(client):   
    webpage_header(client)
    s = os.statvfs('/')
    sensor_temp = machine.ADC(4)
    conversion_factor = 3.3 / (65535)
    reading = sensor_temp.read_u16() * conversion_factor 
    temperature = 27 - (reading - 0.706)/0.001721
    
    ts = 0
    d_now = shortterm_rb.getcurrent()
    d_before = shortterm_rb.getNBack(1)
    if d_now != None and d_before != None:
        #print(f'Now: {d_now} Before: {d_before}')
        ts = getTimeSeconds(d_now['t']) - getTimeSeconds(d_before['t'])
    tm = 0
    d_now = midterm_rb.getcurrent()
    d_before = midterm_rb.getNBack(1)
    if d_now != None and d_before != None:
        #print(f'Now: {d_now} Before: {d_before}')
        tm = getTimeSeconds(d_now['t']) - getTimeSeconds(d_before['t'])
    tl = 0
    d_now = longterm_rb.getcurrent()
    d_before = longterm_rb.getNBack(1)
    if d_now != None and d_before != None:
        #print(f'Now: {d_now} Before: {d_before}')
        tl = getTimeSeconds(d_now['t']) - getTimeSeconds(d_before['t'])    
    
    html = f"""
<h1>Controller and Program Stats</h1>
Shortterm data samples: {shortterm_rb.size} Capacity: {shortterm_rb.capacity} Time Diff: {ts}<br>
Midterm data samples: {midterm_rb.size} Capacity: {midterm_rb.capacity} Time Diff: {tm}<br>
Longterm data samples: {longterm_rb.size} Capacity: {longterm_rb.capacity} Time Diff: {tl}<br>
Free SSD storage: {s[0]*s[3]/1024} KB <br>
Total SSD storage: {s[0]*s[2]/1024} KB <br>
Memory: {gc.mem_free()} bytes free, {gc.mem_alloc()} bytes used <br>
CPU Freq: {machine.freq()/1000000}Mhz <br>
CPU Temperature: {temperature} <br>
"""
    client.send(html)
    webpage_trailer(client)

def make_table(dataset):
    try:
        metrics_labels = ['Temperature', 'Moisture', 'Light']
        data_table = []
        row = ['', 'Current', 'Change/3', 'Change/10', 'Average', 'Minimum', 'Maximum']
        data_table.append(row)
        ratesofchange3 = getRateOfChange(dataset, 3)
        ratesofchange10 = getRateOfChange(dataset, 10)
        
        d_now = dataset.getcurrent()
        d_before = dataset.getNBack(3)
        d3 = 0
        if d_now != None and d_before != None:
            d3 = getTimeSeconds(d_now['t']) - getTimeSeconds(d_before['t'])
            
        d_before = dataset.getNBack(10)
        d10 = 0
        if d_now != None and d_before != None:
            d10 = getTimeSeconds(d_now['t']) - getTimeSeconds(d_before['t'])
        
        row = ['Time',
               dataset.getcurrent()['t'],
               d3,
               d10,
               'N/A',
               'N/A',
               'N/A']
        data_table.append(row)
        
        for metrics_idx in range(0, 3):
            #print(ratesofchange)
            #print(ratesofchange[metrics_idx])
            row = [metrics_labels[metrics_idx],
                   dataset.getcurrent()['v'][metrics_idx],
                   ratesofchange3[metrics_idx],
                   ratesofchange10[metrics_idx],
                   dataset.getaverage(metrics_idx),
                   dataset.getmin(metrics_idx),
                   dataset.getmax(metrics_idx)]
            #print(row)
            data_table.append(row)
            
    except Exception as e:
        logger.log(f'Failure building data table: {e}')


    return data_table

def render_table(client, data_table):
    client.send('<table class="table table-striped table-dark">')
        
    for row in data_table:
        client.send('<tr>')
        row_count = 0
        for col in row:
            if row_count == 0:
                client.send('<th>' + str(col) + '</th>')
            else:
                client.send('<td>' + str(col) + '</td>')
        row_count += 1
            
    client.send('</tr>')    
    client.send('</table>')
    

def webpage_metrics(client):
    
    webpage_header(client)
    metrics_labels = ['Temperature', 'Moisture', 'Light']
    dataset_labels = ['Shortterm', 'Midterm', 'Longterm']
    html = f"""
<h1>Metrics</h1>
"""
    for dataset_idx in range(0, 3):
        
        data_table = None
        if dataset_idx == 0:
            dataset = shortterm_rb
            data_table = make_table(shortterm_rb)
        elif dataset_idx == 1:
            dataset = midterm_rb
            data_table = make_table(midterm_rb)
        elif dataset_idx == 2:
            dataset = longterm_rb
            data_table = make_table(longterm_rb)
        dataset_label = dataset_labels[dataset_idx]
        
        client.send('<h3>' + dataset_labels[dataset_idx] + '</h3>')
        render_table(client, data_table)

def sendFile(filename, client):
    try:
        with open(filename, "rb") as file:
            while chunk := file.read(1024):
                client.sendall(chunk)

            file.close()

    except Exception as e:
        logger.log(f'Unable to send file {filename}: {e}')            
                

def serve(connection):

    pico_led.off()
    temperature = 0
    while True:
        try:
            client = connection.accept()[0]
            request = client.recv(1024)
            request = str(request)         
            
            try:
                request = request.split()[1]
            except IndexError:
                pass
           
            try:
                logger.log(f'Got request: {request}')
                pico_led.on()
               
                if request == '/':
                    client.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\nAccess-Control-Allow-Origin: *\r\n\r\n')
                    webpage_main(client)
                elif request == '/stats':
                    client.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\nAccess-Control-Allow-Origin: *\r\n\r\n')
                    webpage_stats(client)         
                elif request == '/restart':
                    client.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\nAccess-Control-Allow-Origin: *\r\n\r\n')
                    global keep_running
                    keep_running = False
                    logger.log('Resetting controller...')
                    client.send('<html><h3>Controller is restarting</h3></html>')
                    client.close()
                    
                    shortterm_rb.save()
                    midterm_rb.save()
                    longterm_rb.save()
            
                    pico_led.off()
                    sleep(5)
                    machine.reset()
                    sleep(5)
                elif request == "/bigdisplay":
                    client.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\nAccess-Control-Allow-Origin: *\r\n\r\n')
                    webpage_big_display(client)
                elif request == '/metrics':
                    client.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\nAccess-Control-Allow-Origin: *\r\n\r\n')
                    webpage_metrics(client)
                elif request == '/shorttermdata.txt':
                    client.send('HTTP/1.0 200 OK\r\nContent-type: application/json\r\nAccess-Control-Allow-Origin: *\r\n\r\n')
                    shortterm_rb.d3json(client)
                elif request == '/midtermdata.txt':
                    client.send('HTTP/1.0 200 OK\r\nContent-type: application/json\r\nAccess-Control-Allow-Origin: *\r\n\r\n')
                    midterm_rb.d3json(client)
                elif request == '/longtermdata.txt':
                    client.send('HTTP/1.0 200 OK\r\nContent-type: application/json\r\nAccess-Control-Allow-Origin: *\r\n\r\n')
                    longterm_rb.d3json(client)
                elif request == b'':
                    logger.log(f'Received invalid request {request}')
                else:
                    filename = request.split('?')[0]
                    if filename == '/chart.html':
                        client.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\nAccess-Control-Allow-Origin: *\r\n\r\n')
                        sendFile('header.html', client)
                        sendFile(filename, client)
                    else:
                        sendFile(filename, client)
            
                client.close()
            
            except Exception as e:
                logger.log(f'Failure handling web request {request}: {e}')   
                client.close()
                
            pico_led.off()

        except Exception as e:
            #logger.log(f'Failure handling web request: {e}')
            pass

def main():
    # main loop
    connection = None
    global wlan
    wlan = None
    try:
        oled.clear()
        oled.print("Starting EnvPlat", 0)
        oled.print("Connect to Wifi", 1)
        ip = networking.connect()
        oled.print(str(ip), 1)
        oled.clear()
        oled.print("Starting EnvPlat", 0)
        oled.print("Get NTP time", 1)
        networking.set_clock_from_ntp()
        oled.print(networking.getTimeStr(), 2)
        logger.log("Set watchdog with 8s timeout")
        global wdt
        wdt = WDT(timeout = 8000)
        logger.log("Start data collection thread")
        gc.collect()
        timer = Timer(mode=Timer.PERIODIC, period = 4000, callback = collectSensorData)
        logger.log("Open network socket")
        connection = networking.open_socket(ip)
        logger.log("Accept web requests")
        serve(connection)
       
    except KeyboardInterrupt:
        global keep_running
        keep_running = False
        logger.log("Keyboard interupt")
        if (wlan != None):
            wlan.disconnect()
            logger.log("WLAN disconnected")
            wlan = None
        if (connection != None):
            connection.close()
            logger.log("Connection closed")
            connection = None
        else:
            logger.log("No connection to close")
            
        sleep(3)
        logger.log("Resetting controller")
        machine.reset()
             
       
    finally:
        if (wlan != None):
            wlan.disconnect()
            logger.log("WLAN disconnected")
        if (connection != None):
            connection.close()
            logger.log("Connection closed")
        
    shortterm_rb.save()
    midterm_rb.save()
    longterm_rb.save()
    
    logger.log("Exiting application")
    sleep(1)
    logger.log("Resetting controller")
    machine.reset()
    sleep(20)
        

main()
