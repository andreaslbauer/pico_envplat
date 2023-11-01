import machine
import _thread
import os

rtc = machine.RTC()
picologger_instance = None
logfilename = "log.txt"

class picologger:
    
    def __init__(self):
        self.file = None
        self.lock = None

        self.lock = _thread.allocate_lock()

        statinfo = os.stat(logfilename)
        logfilesize = statinfo[6]
        if logfilesize > 25000:
           os.remove(logfilename) 

        try:
            self.file = open(logfilename, "a")

        except:
            print(f"Unable to open log file {logfilename}")

    def log(self, s):
        self.lock.acquire()
        t = rtc.datetime()
        ts = "%04d-%02d-%02d %02d:%02d:%02d"%(t[0:3] + t[4:7])
        ls = ts + " " + s
        print(ls)

        if self.file != None:
            self.file.write(ls  + '\n')
            self.file.flush()
        
        self.lock.release()
            

def get_logger():
    global picologger_instance
    if picologger_instance == None:
       picologger_instance = picologger()

    return picologger_instance 
