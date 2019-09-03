import os
import logging
import json
from peconnect import *
from myutilities import *

class backout():
    def __init__(self,**kw):
        self.hostname=kw['hostname']
        self.info("backing out of %s..." % self.hostname)
        self.binfile=kw['options'].binfile
        self.options=kw['options']
        self.path=os.getcwd()+'/'+self.hostname
        self.devinfofile=self.path+'/devinfo.json'
        self.errors=list()
        self.devinfo={}
        logging.basicConfig(filename=self.path+'/raw.log',level=logging.DEBUG)
        self.checkworkspace()
        self.info('--connecting to device')
        self.pe=pelogon(ip=self.hostname,binfile=self.binfile,logfile=self.path+'/raw.log')
        self.info('---restoring boot config')
        self.pe.setBoot(self.devinfo['bootinfo']['primary']['slot'],self.devinfo['bootinfo']['secondary']['slot'])
        self.devinfo['status']='backed out'
        f=open(self.devinfofile,'w')
        self.info('--writing %s...' % self.devinfofile)
        f.write(json.dumps(self.devinfo))
        self.info('complete')

    def checkworkspace(self):
        self.info("--Setting up your workspace...")
        if(os.path.exists(self.path)):
            if os.path.isfile(self.devinfofile):
                f=open(self.devinfofile,'r')
                try:
                    self.devinfo=json.loads(f.read())
                except:
                    self.status='prepare'
            else:
                self.status='prepare'
        else:
            self.status='prepare'


    def info(self,msg):
        print(str(msg))
