import os
import inspect
import time
import logging
import json
from termcolor import colored
from terminaltables import AsciiTable

class message:
    def __init__(self,**kw):
        self.inittime=time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        self.errors={}
        self.timedict={}
        self.peclog=False
        self.path=os.getcwd()
        self.options=kw['options']
        self.binfile=self.options.binfile
        self.binfilepath=kw['binfilepath']

    def setlogging(self,hostname):
        self.hostname=hostname
        self.errors={hostname:{'warning':list(),'critical':list()}}
        self.devpath=self.path+'/'+hostname+'/'
        self.log=self.devpath+'info.log'
        self.peclog=self.devpath+'commands.log'
        self.devinfofile=self.devpath+'devinfo.json'
        logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s',
        filename=self.log,
        level=logging.DEBUG,
        datefmt='%Y-%m-%d %H:%M:%S')

    def writedevinfo(self,devinfo):
        f=open(self.devinfofile,'w')
        self.info('-writing %s...' % self.devinfofile)
        f.write(json.dumps(devinfo))

    def resetlogs(self):
        open(self.log,'w')
        open(self.peclog,'w')

    def getelapse(self,key):
        if self.timedict.has_key(key):
            start=self.timedict[key]['start']
            end=time.timer()
            elapse=end-start
            self.timedict[key]={'start':start,'end':end,'elapse':elapse}
        else:
            self.timedict[key]={'start':time.timer()}

    def debug(self,m):
        logging.debug(str(m))

    def info(self,m):
        logging.info(m)
        print(str(m))

    def warning(self,m):
        logging.warning(m)
        print('WARNING:'+str(m))
        self.addError(str(m),'warning')

    def critical(self,m):
        logging.critical(m)
        print('CRITICAL:'+str(m))
        self.addError(str(m),'critical')

    def addError(self,m,level):
        self.errors[self.hostname][level].append({'tstamp':time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),'message':m})
