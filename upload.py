#!/opt/local/scripts/python/ftosupgrade/bin/python2.7
import json
import logging
import time
import os
from utilities import utils
from peconnect import *

class uploadbin(utils):
    def __init__(self,**kw):
        utils.__init__(self,**kw)
        self.multi=False
        if kw.has_key('multi'): self.multi=True
        if self.multi: self.silent=True
        self.info("uploading %s to %s..." % (self.binfile,self.hostname))
        self.uploadinfo={}
        self.pe=pelogon(hostname=self.hostname,options=self.options,silent=self.silent)
        if self.multi:
            self.checkbinfile()
            if self.uploadinfo['binfilestatus'].has_key('error'):
                ferror=self.uploadinfo['binfilestatus']['error']
                if 'local' in ferror:
                    self.warning(ferror)
                else:
                    self.warning(self.uploadinfo['binfilestatus']['error'])
                    self.pe.scp()
                    self.checkbinfile()
                    self.info(self.uploadinfo['binfilestatus'])
            else:
                self.info(self.uploadinfo['binfilestatus'])
        else:
            self.pe.scp()
            self.checkbinfile()
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
