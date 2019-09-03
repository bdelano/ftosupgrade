import os
import logging
import json
import time
import difflib
from peconnect import *
from mysql import *

class upgrade():
    def __init__(self,**kw):
        self.hostname=kw['hostname']
        self.info("-------------\nupgrading %s..." % self.hostname)
        self.binfile=kw['options'].binfile
        self.options=kw['options']
        self.path=os.getcwd()+'/'+self.hostname
        self.log=self.path+'/raw.log'
        self.devinfofile=self.path+'/devinfo.json'
        self.curversion=None
        self.upgraded=False
        self.errors=list()
        self.devinfo={}
        self.status='fail'
        self.test=False
        if self.options.noforce: self.test=True
        logging.basicConfig(filename=self.log,level=logging.DEBUG)
        self.checkworkspace()
        self.pe=pelogon(ip=self.hostname,logfile=self.path+'/raw.log')
        #check to see if device is already upgraded
        self.checkupgraded()
        if self.test: self.upgraded=False
        if self.status=='prepare':
            msg='ERROR: looks like the workspace is not prepared correctly please re-run the prepare script'
            self.info(msg)
            self.pe.exit()
        elif self.upgraded:
            self.info('Looks like this device was already upgraded!\nPlease make sure you are looking at the correct device!')
            self.info('running post checks')
            self.checkupgraded()
            if self.test: self.upgraded=True #added for testing
            self.pe.exit()
        else:
            self.pe.exit()
            self.info('-connecting to opengear...')
            self.og=pelogon(ip=self.devinfo['oginfo']['mgmtip'],port=self.devinfo['oginfo']['interface'],logfile=self.path+'/raw.log',og=1)
            self.og.remlogon()
            time.sleep(1)
            if self.og.status=='success' and self.og.vendor=='dell':
                self.info('--connected, reloading device, please be patient...')
                self.info('--switching output to command line...')
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
                        self.info('\n--reload complete, waiting for 5 seconds...')
                        self.og.message='login' #set og message to force login
                        time.sleep(5) #sleeping to let device recover
                        self.info('attempting to log on via opengear...')
                        self.og.remlogon()
                        if self.og.status=='success':
                            self.info('--login successful dropping opengear connection')
                            self.og.e.terminate()
                            self.info('-attempting to log on via ssh to complete checks...')
                            self.pe=pelogon(ip=self.hostname,logfile=self.path+'/raw.log')
                            self.checkupgraded()
                            if self.test: self.upgraded=True #added for testing
                            self.runpostchecks()
                            self.pe.exit()
                        else:
                            msg='ERROR: unable to log back into switch!'
                            self.info('status:%s' % self.og.status)
                            self.info(msg)
                            self.errors.append(msg)
                            self.info(self.og.message)
                    else:
                        msg='unable to catch end of reload, please attempt to login manually'
                        self.info(msg)
                        self.info('fail reason')
                        self.info(self.og.message)
                else:
                    self.og.e.sendline('no')
                    self.og.e.expect(['.*\[confirm yes/no\]:','Save\? \[yes/no\]:'])
                    self.og.e.sendline('no')
                    self.og.e.expect(self.og.prompt)
                    msg='--Upgrade FAILED: looks like the config has changed since being prepared, please investigate!'
                    self.info(msg)
                    self.errors.append(msg)
            else:
                self.errors.append('unable to login to opengear:%s' % self.og.message)
                self.info('unable to login to opengear!')
            self.og.e.terminate()
        if len(self.errors)>0:
            self.status='fail'
        self.info('finished')

    def runpostchecks(self):
        if self.upgraded:
            self.devinfo['status']='upgraded'
            self.info('--Device is now upgraded to %s' % self.curversion)
            self.pe.runchecks(type='post',path=self.path)
            self.comparechecks()
        else:
            msg='--Upgrade FAILED: current version (%s) does not match target version (%s)' % (self.curversion,self.devinfo['binswversion'])
            self.info(msg)
            self.errors.append(msg)

    def comparechecks(self):
        self.info('-comparing pre/post')
        diffrx=re.compile("^([+-]) (.*)")
        d=difflib.Differ()
        for f in ['shintdescr','shlldp','shvlt']:
        #for f in ['shlogging']:
            self.info('--diffing %s.cmd' % f)
            pref=open(self.path+'/pre/'+f+'.cmd','r')
            posf=open(self.path+'/post/'+f+'.cmd','r')
            difflist=list(d.compare(pref.read().split("\r\n"),posf.read().split("\r\n")))
            for l in difflist:
                diffm=diffrx.match(l)
                if diffm:
                    trdict={'-':'inpre','+':'inpost'}
                    msg=trdict[diffm.group(1)]+'=='+diffm.group(2)
                    self.errors.append(f+' diffs:'+msg)
                    self.info(msg)

    def checkupgraded(self):
        self.curversion=self.pe.bootinfo['primary']['version']
        if self.curversion==self.devinfo['binswversion'] or self.devinfo['status']=='upgraded':
            self.upgraded=True


    def info(self,msg):
        print(str(msg))

    def checkworkspace(self):
        self.info("-Setting up your workspace...")
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
