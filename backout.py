import os
import logging
import json
from peconnect import *
from myutilities import *

class backout():
    def __init__(self,**kw):
        self.m=kw['message']
        self.hostname=self.m.hostname
        self.m.info("backing out of %s..." % self.hostname)
        self.devinfo={}
        self.checkworkspace()
        self.m.info('--connecting to device')
        self.pe=pelogon(message=self.m)
        self.m.info('---restoring boot config')
        self.pe.setBoot(self.devinfo['bootinfo']['primary']['slot'],self.devinfo['bootinfo']['secondary']['slot'])
        self.devinfo['status']='backed out'
        self.m.writedevinfo(self.devinfo)
        self.m.info('complete!')
        self.m.info('Please login to the switch and reload it')
        self.m.info('rtc %s should get you into the device via opengear' % self.hostname)

    def checkworkspace(self):
        self.m.info("--Setting up your workspace...")
        if(os.path.exists(self.m.devpath)):
            if os.path.isfile(self.m.devinfofile):
                f=open(self.m.devinfofile,'r')
                try:
                    self.devinfo=json.loads(f.read())
                except:
                    self.status='prepare'
            else:
                self.status='prepare'
        else:
            self.status='prepare'
