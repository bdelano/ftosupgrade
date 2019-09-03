#!/opt/local/scripts/python/ftosupgrade/bin/python2.7
import json
import logging
import time
import os
from peconnect import *

class uploadbin:
    def __init__(self,**kw):
        self.hostname=kw['hostname']
        self.errors=list()
        self.binfile=kw['binfile']
        self.binfilepath=kw['binfilepath']
        self.multi=False
        self.silent=False
        if kw.has_key('multi'): self.multi=True
        if self.multi: self.silent=True
        self.path=os.getcwd()+'/'+self.hostname
        self.logfile=self.path+'/raw.log'
        print("uploading %s to %s..." % (self.binfile,self.hostname))
        if kw.has_key('logfile'): self.logfile=kw['logfile']
        self.uploadinfo={}
        if self.multi: logging.basicConfig(filename=self.logfile,level=logging.DEBUG)
        self.pe=pelogon(ip=self.hostname,debug=1,binfile=self.binfile,binfilepath=self.binfilepath,silent=silent)
        self.checkbinfile()
        if self.uploadinfo['binfilestatus'].has_key('error'):
            ferror=self.uploadinfo['binfilestatus']['error']
            if 'local' in ferror:
                logging.critical(ferror)
            else:
                logging.info(self.uploadinfo['binfilestatus']['error'])
                self.pe.scp()
                self.checkbinfile()
                logging.info(self.uploadinfo['binfilestatus'])
        else:
            logging.info(self.uploadinfo['binfilestatus'])
        self.pe.exit()
        if self.multi: os._exit(0)

    def checkbinfile(self):
        self.uploadinfo['files']=self.pe.getfilelist()
        if self.binfile:
            if path.exists('%s%s' % (self.binfilepath,self.binfile)):
                if self.uploadinfo['files'].has_key(self.binfile):
                    binres=self.pe.getCommand('verify md5 flash://%s %s' % (self.binfile,binmd5[self.binfile]))
                    if 'FAILED' in binres:
                        self.uploadinfo['binfilestatus']={'error':binres}
                    else:
                        self.uploadinfo['binfilestatus']={'succcess':'binfile (%s) exists' % self.binfile}
                else:
                    self.uploadinfo['binfilestatus']={'error':'binfile (%s) does not exist' % self.binfile}
            else:
                self.uploadinfo['binfilestatus']={'error':'cannot find local file %s%s' % (BINFILEPATH,self.binfile)}
        else:
            self.uploadinfo['binfilestatus']={'error':'binfile does not match expected format:%s' % self.binfile}
        if self.uploadinfo['binfilestatus'].has_key('error'):
            self.errors.append(self.uploadinfo['binfilestatus']['error'])
