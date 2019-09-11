import os
import logging
import json
from peconnect import pelogon
from utilities import utils

class backout(utils):
    def __init__(self,**kw):
        utils.__init__(self,**kw)
        self.info("backing out of %s..." % self.hostname)
        self.loaddevinfo()
        self.info('--connecting to device')
        self.pe=pelogon(hostname=self.hostname,options=self.options)
        self.info('---restoring boot config')
        self.pe.setBoot(self.devinfo['bootinfo']['primary']['slot'],self.devinfo['bootinfo']['secondary']['slot'])
        self.devinfo['prepstatus']='backed out'
        self.writedevinfo()
        self.info('complete!')
        self.info('Please login to the switch and reload it')
        self.info('rtc %s should get you into the device via opengear' % self.hostname)
        self.pe.exit()
