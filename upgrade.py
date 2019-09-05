import os
import json
import time
import sys
import difflib
from peconnect import *
from mysql import *

class upgrade():
    def __init__(self,**kw):
        self.m=kw['message']
        self.hostname=self.m.hostname
        self.m.info("-------------\nupgrading %s..." % self.hostname)
        self.curversion=None
        self.upgraded=False
        self.devinfo={}
        self.status='fail'
        #self.test=self.m.options.noforce
        self.test=True
        self.checkworkspace()
        self.pe=pelogon(message=self.m)  #ssh into switch
        #check to see if device is already upgraded
        self.checkupgraded()
        if self.test: self.upgraded=False
        if self.status=='prepare':
            msg='ERROR: looks like the workspace is not prepared correctly please re-run the prepare script'
            self.m.critical(msg)
        elif self.upgraded:
            self.m.warning('Looks like this device was already upgraded!\nPlease make sure you are looking at the correct device!')
            self.m.info('re-running post checks')
            #self.runpostchecks()
            self.comparechecks()
            self.checkupgraded()
        else:
            self.m.info('-connecting to opengear...')
            self.og=pelogon(ip=self.devinfo['oginfo']['mgmtip'],port=self.devinfo['oginfo']['interface'],og=1,message=self.m)
            self.og.remlogon()
            time.sleep(1)
            if self.og.status=='success' and self.og.vendor=='dell':
                self.m.info('--connected, reloading device, please be patient...')
                self.m.info('--switching output to command line...')
                self.og.e.logfile=sys.stdout
                if self.test:
                    self.og.e.sendline('dir |no-more')
                    self.og.e.expect(self.og.prompt)
                    self.og.e.sendline('exit')
                    self.og.e.expect('get started')
                    self.og.e.sendline()
                    resp=0
                else:
                    self.og.e.sendline('reload')
                    resp=self.og.e.expect(['.*\[confirm yes/no\]:','Save\? \[yes/no\]:'])
                if resp==0:
                    if not self.test: self.og.e.sendline('yes')
                    resp=self.og.e.expect(['Login:',pexpect.EOF],timeout=None)
                    if resp==0:
                        self.m.info('\n--reload complete, waiting for 10 seconds...')
                        self.og.message='login' #set og message to force login
                        time.sleep(10) #sleeping to let device recover
                        self.m.info('attempting to log on via opengear...')
                        self.og.remlogon()
                        if self.og.status=='success':
                            self.m.info('--login successful dropping opengear connection')
                            self.og.e.terminate()
                            self.m.info('-attempting to log on via ssh to complete checks...')
                            self.pe=pelogon(message=self.m)
                            self.checkupgraded()
                            if self.test: self.upgraded=True #added for testing
                            self.runpostchecks()
                            self.pe.exit()
                        else:
                            self.m.critical('ERROR: unable to log back into switch!\nPlease re-run the upgrade command as sometimes it takes a little while for tacacs!')
                    else:
                        msg='unable to catch end of reload, please attempt to login manually'
                        self.m.critical(msg)
                        self.m.critical(self.og.message)
                else:
                    self.og.e.sendline('no')
                    self.og.e.expect(['.*\[confirm yes/no\]:','Save\? \[yes/no\]:'])
                    self.og.e.sendline('no')
                    self.og.e.expect(self.og.prompt)
                    self.m.critical('looks like the config has changed since being prepared, please investigate!')
                    self.m.critical('this can usually be fixed by just saving the config an re-running this script...')
            else:
                self.m.critical('unable to login to opengear:%s' % self.og.message)
            self.og.e.terminate()
        self.devinfo['errors']={'upgrade':self.m.errors[self.hostname]}
        self.pe.exit()
        if len(self.m.errors[self.hostname]['critical'])>0:
            self.devinfo['upgradestatus']='upgraded'
            self.m.warning('attempted upgrade but found some errors!')
        else:
            self.devinfo['upgradestatus']='upgraded'
            self.m.info('upgraded successfully',attrs='bold')
        self.m.writedevinfo(self.devinfo)

    def runpostchecks(self):
        if self.upgraded:
            self.m.info('--Device is now upgraded to %s' % self.curversion)
            self.pe.runchecks('post')
            self.comparechecks()
        else:
            self.m.critical('--Upgrade FAILED: current version (%s) does not match target version (%s)' % (self.curversion,self.devinfo['binswversion']))

    def comparechecks(self):
        self.m.info('-comparing pre/post')
        diffrx=re.compile("^([+-]) (.*)")
        d=difflib.Differ()
        for f in ['shintdescr','shlldp','shvltdet']:
            self.m.info('--diffing %s.cmd' % f)
            pref=open(self.m.devpath+'/pre/'+f+'.cmd','r')
            posf=open(self.m.devpath+'/post/'+f+'.cmd','r')
            difflist=list(d.compare(pref.read().split("\r\n"),posf.read().split("\r\n")))
            for l in difflist:
                diffm=diffrx.match(l)
                if diffm:
                    trdict={'-':'inpre','+':'inpost'}
                    msg=trdict[diffm.group(1)]+'=='+diffm.group(2)
                    self.m.critical(f+':diffsfound:'+msg)

    def checkupgraded(self):
        self.curversion=self.pe.bootinfo['primary']['version']
        #if self.curversion==self.devinfo['binswversion'] or self.devinfo['upgradestatus']=='upgraded':
        if self.curversion==self.devinfo['binswversion']:
            self.upgraded=True

    def checkworkspace(self):
        self.m.info("-Setting up your workspace...")
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
