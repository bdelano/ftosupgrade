import os
import time
import json
import sys
import logging
from termcolor import colored
from terminaltables import AsciiTable

class setup:
    def __init__(self,**kw):
        """
        sets up all the variables for each device, these are shared across all classes
        I'm sure there is a better way to do this so this most likely will change
        """
        self.inittime=time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        self.errors={}
        self.timedict={}
        self.silent=False
        if kw.has_key('silent'): self.silent=kw['silent']
        self.peclog=False
        self.path=os.getcwd()
        self.hostname=kw['hostname']
        self.devpath=self.path+'/'+self.hostname+'/'
        self.setupworkspace()
        self.options=kw['options']
        self.binfile=self.options.binfile
        self.binfilepath=kw['binfilepath']
        self.errors={self.hostname:{'warning':list(),'critical':list()}}
        self.log=self.devpath+'info.log'
        self.peclog=self.devpath+'commands.log'
        self.errorlog=self.devpath+'errors.log'
        self.devinfofile=self.devpath+'devinfo.json'
        logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s',
        filename=self.log,
        level=logging.DEBUG,
        datefmt='%Y-%m-%d %H:%M:%S')
        self.logger=logging.getLogger('messages')


    def writedevinfo(self,devinfo):
        f=open(self.devinfofile,'w')
        self.info('-writing %s...' % self.devinfofile)
        f.write(json.dumps(devinfo))

    def writeerrors(self):
        f=open(self.errorlog,'w')
        for et in ['warning','critical']:
            for l in self.errors[self.hostname][et]:
                f.write("{t} : {m}\n".format(m=l['message'],t=l['tstamp']))

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

    def setupworkspace(self):
        """
        creates necessary directories and file structure for the tool to work
        """
        if not self.silent: print("--Setting up your workspace...")
        if not os.path.exists(self.devpath):
            if not self.silent: print("--creating necessary directories...")
            os.mkdir(self.devpath)
            os.mkdir(self.devpath+'/pre')
            os.mkdir(self.devpath+'/post')

    def debug(self,msg):
        self.logger.debug(msg)

    def info(self,msg,**kw):
        atlist=list()
        if kw.has_key('attrs'):
            atlist.append(kw['attrs'])
        self.logger.info(msg)
        if not self.silent: print(str(colored(msg,'green',attrs=atlist)))

    def warning(self,msg):
        m='WARNING:%s' % msg
        self.logger.warning(msg)
        if not self.silent: print(colored(m,'yellow'))
        self.addError(str(msg),'warning')

    def critical(self,msg):
        m='CRITICAL:%s' % msg
        self.logger.critical(m)
        if not self.silent: print(colored(m,'red'))
        self.addError(str(msg),'critical')

    def addError(self,m,level):
        self.errors[self.hostname][level].append({'tstamp':time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),'message':m})
