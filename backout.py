import os
import logging
import json
from peconnect import *
from myutilities import *

class backout(utils):
    def __init__(self,**kw):
        utils.__init__(self,**kw)
        self.info("backing out of %s..." % self.hostname)
        self.devinfo={}
        self.checkworkspace()
        self.info('--connecting to device')
        self.pe=pelogon(hostname=self.hostname,options=self.options)
        self.info('---restoring boot config')
        self.pe.setBoot(self.devinfo['bootinfo']['primary']['slot'],self.devinfo['bootinfo']['secondary']['slot'])
        self.devinfo['status']='backed out'
        self.writedevinfo(self.devinfo)
        self.info('complete!')
        self.info('Please login to the switch and reload it')
        self.info('rtc %s should get you into the device via opengear' % self.hostname)
        self.pe.exit()

    def checkworkspace(self):
        self.info("--Setting up your workspace...")
        if(os.path.exists(self.devpath)):
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
