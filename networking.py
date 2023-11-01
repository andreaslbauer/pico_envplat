import network
import socket
from machine import Timer
import machine
from time import sleep
import time, utime
import struct
import picologger
logger = picologger.get_logger()

ssid = 'MayzieNet'
password = 'Alexander5'
ip_str = ""
rtc = machine.RTC()
wlan = None

def connect():
    # Connect to WLAN
    status = False
    wlan = None
    # attempt until we are connected
    while status == False:
        wlan = network.WLAN(network.STA_IF)
        #wlan.disconnect()
        wlan.active(True)
        sleep(2)
        wlan.connect(ssid, password)
        c = 1
        
        # wait up to 10s then retry
        while wlan.isconnected() == False and c < 10:
            logger.log(f'Waiting for connection... {c}')
            sleep(1)
            c += 1
    
        if c < 10:
            ip = wlan.ifconfig()[0]
            global ip_str
            ip_str = str(ip)
            status = True

    logger.log(f'Wifi Connected on address: {ip}')

    return ip
   
def open_socket(ip):
    # Open a socket
    address = (ip, 80)
    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    connection.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    #connection.settimeout(10.0)
    connection.bind(address)
    connection.listen(3)
    return connection


def getTimeDateStr():
    t = rtc.datetime()
    return "%04d-%02d-%02d %02d:%02d:%02d"%(t[0:3] + t[4:7])

def getTimeStr():
    t = rtc.datetime()
    return "%02d:%02d:%02d"%(t[4:7])

# connect to an NTP server, obtain the current time and set our clock to that time
def set_clock_from_ntp():
    
    # first check whether RTC is already set from IDE
    t = rtc.datetime()
    logger.log(f'RTC time: {t}')
    if (t[0] >= 2023):
        # year is greater 2023 - no need to get NTP time
        logger.log('No need to get time from NTP...')
        return True
    
    status = False
    
    NTP_EST_ADJUST = 4 * 60 * 60
    NTP_DELTA = 2208988800 + NTP_EST_ADJUST
    
    hosts = ["pool.ntp.org",
             "216.229.4.66",
             "0.pool.ntp.org",
             "1.pool.ntp.org",
             "2.pool.ntp.org"]
    hostsIndex = 0
    
    status = False
    attempts = 0
    while status == False and attempts < 3:
        attempts += 1
        host = hosts[hostsIndex]
        hostsIndex += 1
        if hostsIndex >= len(hosts):
            hostsIndex = 0
            
        logger.log(f'Attempt to get time from {host}')
      
        NTP_QUERY = bytearray(48)
        NTP_QUERY[0] = 0x1B
        s = None
        try:
            addr = socket.getaddrinfo(host, 123)[0][-1]
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        except Exception as e:
            logger.log(f'Unable to get time from NTP server - getaddrinfo/socket error: {e}')

        if s != None:
            try:
                s.settimeout(6)
                res = s.sendto(NTP_QUERY, addr)
                msg = s.recv(48)
                
                val = struct.unpack("!I", msg[40:44])[0]
                t = val - NTP_DELTA    
                tm = time.gmtime(t)
                machine.RTC().datetime((tm[0], tm[1], tm[2], tm[6] + 1, tm[3], tm[4], tm[5], 0))
                logger.log(f'Clock set from NTP at {host}, time is: {getTimeStr()}')
                
                status = True
                success = True
                
            except Exception as e:
                logger.log(f'Unable to get time from NTP server: {e}')
                
            finally:
                s.close()
                
        sleep(1)
        
    return status