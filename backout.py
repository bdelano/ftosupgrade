import os
import logging
import json
from peconnect import *

class backout():
    def __init__(self,**kw):
        self.hostname=kw['hostname']
        self.info("backing out of %s..." % self.hostname)
        self.binfile=kw['options'].binfile
        self.options=kw['options']
        self.path=os.getcwd()+'/'+self.hostname
        self.upinfofile=self.path+'/devinfo.json'
        self.errors=list()
        self.upinfo={}
        logging.basicConfig(filename=self.path+'/raw.log',level=logging.DEBUG)
        self.checkworkspace()
        self.info('--connecting to device')
        self.pe=pelogon(ip=self.hostname,binfile=self.binfile,logfile=self.path+'/raw.log')
        self.pe.devinfo=self.upinfo['devinfo']
        self.info('---restoring boot config')
        self.pe.restoreBoot()
        self.upinfo['status']='backed out'
        f=open(self.upinfofile,'w')
        self.info('--writing %s...' % self.upinfofile)
        f.write(json.dumps(self.upinfo))
        self.info('complete')

    def checkworkspace(self):
        self.info("--Setting up your workspace...")
        if(os.path.exists(self.path)):
            if os.path.isfile(self.upinfofile):
                f=open(self.upinfofile,'r')
                try:
                    self.upinfo=json.loads(f.read())
                except:
                    self.status='prepare'
            else:
                self.status='prepare'
        else:
            self.status='prepare'


    def info(self,msg):
        print(str(msg))


    def setupworkspace(self):
        self.info("--Setting up your workspace...")
        if(os.path.exists(self.path)):
            if os.path.isfile(self.upinfofile):
                f=open(self.upinfofile,'r')
                try:
                    self.upinfo=json.loads(f.read())
                except:
                    logging.warning('unable to read the upinfofile:%s' % self.upinfofile)
                    self.errors.append('unable to read the upinfofile:%s' % self.upinfofile)
                    self.upinfo={}
        else:
            self.info("--creating necessary directories...")
            os.mkdir(self.path)
            os.mkdir(self.path+'/pre')
            os.mkdir(self.path+'/post')
        #print(os.path.isdir("/home/el"))
        #print(os.path.exists("/home/el/myfile.txt"))
