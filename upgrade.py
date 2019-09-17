import os
import json
import time
import sys
import difflib
import pexpect
import re
from utilities import utils
from peconnect import pelogon

class upgrade(utils):
    def __init__(self,**kw):
        """
        check if the switch is upgraded, if so re-run post tests
        if not login to opengear and reload
        check everything is reachable and run post tests
        """
        utils.__init__(self,**kw)
        self.info("-------------\nupgrading %s..." % self.hostname,attrs='bold')
        self.curversion=None
        self.upgraded=False
        self.loaddevinfo()
        self.pe=pelogon(hostname=self.hostname,options=self.options)  #ssh into switch, automatically retrieves bootinfo
        self.pe.getbootinfo()
        #check to see if device is already upgraded
        self.checkupgraded()
        if not self.options.notest: self.upgraded=False # if testing pretend its not upgraded already
        if self.upgraded:
            self.warning('Looks like this device was already upgraded!\nPlease make sure you are looking at the correct device!')
            self.info('re-running post checks')
            self.runpostchecks()
            self.checkupgraded()
        else:
            self.info('-connecting to opengear...')
            self.og=pelogon(hostname=self.hostname,options=self.options,ip=self.devinfo['oginfo']['mgmtip'],port=self.devinfo['oginfo']['interface'],og=1)
            self.og.remlogon()
            time.sleep(1)
            if self.og.status=='success' and self.og.vendor=='dell':
                self.info('--connected, reloading device, please be patient...')
                self.info('--switching output to command line...')
                self.og.e.logfile=sys.stdout
                if self.options.notest:
                    self.og.e.sendline('reload')
                    self.debug('sending reload command now!')
                    resp=self.og.e.expect(['.*\[confirm yes/no\]:','Save\? \[yes/no\]:'])
                else:
                    self.og.e.sendline('dir |no-more')
                    self.og.e.expect(self.og.prompt)
                    self.og.e.sendline('exit')
                    self.og.e.expect('get started')
                    self.og.e.sendline()
                    resp=0

                if resp==0:
                    if self.options.notest: self.og.e.sendline('yes')
                    self.devinfo['upgradestatus']='upgraded'
                    resp=self.og.e.expect(['Login:',pexpect.EOF],timeout=None)
                    if resp==0:
                        self.info('\n--reload complete, waiting for 10 seconds...')
                        self.og.message='login' #set og message to force login
                        if self.options.notest: time.sleep(10) #sleeping to let device recover
                        self.info('-attempting to log on via opengear...')
                        self.og.remlogon()
                        if self.og.status=='success':
                            self.info('-login successful dropping opengear connection')
                            self.og.e.terminate()
                            self.info('-attempting to connect via ssh to complete checks...')
                            self.pe=pelogon(hostname=self.hostname,options=self.options)
                            self.pe.getbootinfo()
                            self.debug('after upgrade swversion:%s' % self.pe.bootinfo['primary']['version'])
                            self.checkupgraded()
                            if not self.options.notest: self.upgraded=True #added for testing
                            self.info('--waiting for 120 seconds for interfaces to come back before running post checks...')
                            if self.options.notest: time.sleep(120)
                            self.runpostchecks() #checks if swversion is correct and runs post checks
                        else:
                            self.critical('ERROR: unable to log back into switch!')
                            self.warning('this can usually be fixed by just re-running this script as tacacs may not be reachable...')
                    else:
                        self.critical('unable to catch end of reload, please attempt to login manually')
                        self.critical(self.og.message)
                else:
                    self.og.e.sendline('no')
                    self.og.e.expect(['.*\[confirm yes/no\]:','Save\? \[yes/no\]:'])
                    self.og.e.sendline('no')
                    self.og.e.expect(self.og.prompt)
                    self.critical('looks like the config has changed since being prepared, please investigate!')
                    self.warning('this can usually be fixed by just saving the config an re-running this script...')
                    self.devinfo['upgradestatus']='failed'
            else:
                self.critical('unable to login to opengear:%s' % self.og.message)
                self.devinfo['upgradestatus']='failed'
            self.og.e.terminate()
            
        self.checkMGG()
        self.combineerrors(self.pe.errors[self.hostname])
        self.devinfo['errors']={'upgrade':self.errors[self.hostname]}
        self.info('--exiting device...')
        self.pe.exit()
        if len(self.errors[self.hostname]['critical'])>0:
            self.warning('attempted upgrade but found some errors!')
        else:
            self.info('upgraded successfully',attrs='bold')
        self.writedevinfo()

    def runpostchecks(self):
        """
        check if device successfully upgraded
        run post checks and check for errors and run diffs
        """
        if self.upgraded:
            self.info('--Device is now upgraded to %s' % self.curversion)
            self.pe.runchecks('post')
            self.comparechecks()
        else:
            self.critical('--Upgrade FAILED: current version (%s) does not match target version (%s)' % (self.curversion,self.devinfo['binswversion']))

    def comparechecks(self):
        """
        run diffs on commands who's output you wouldn't expect to change
        """
        self.info('--comparing pre/post')
        diffrx=re.compile("^([+-]) (.*)")
        d=difflib.Differ()
        for f in ['shintdescr','shlldp','shvltdet']:
            self.info('---diffing %s.cmd' % f)
            pref=open(self.devpath+'/pre/'+f+'.cmd','r')
            posf=open(self.devpath+'/post/'+f+'.cmd','r')
            difflist=list(d.compare(pref.read().split("\r\n"),posf.read().split("\r\n")))
            for l in difflist:
                diffm=diffrx.match(l)
                if diffm:
                    trdict={'-':'inpre','+':'inpost'}
                    msg=trdict[diffm.group(1)]+'=='+diffm.group(2)
                    self.critical(f+':diffsfound:'+msg)

    def checkupgraded(self):
        """
        check if current software matches upgrade target
        """
        self.curversion=self.pe.bootinfo['primary']['version']
        if self.curversion==self.devinfo['binswversion']:
            self.upgraded=True

    def checkMGG(self):
        self.getMGG()
        if len(self.mgg)>0:
            for mgg in self.mgg:
                self.info('checking for blocked ports on %s...' % mgg)
                mggpe=pelogon(hostname=mgg,options=self.options,logfile=self.peclog)
                mggpe.checkBlocked()
                mggpe.exit()
                if len(mggpe.errors[mgg]['critical'])>0:
                        self.combineerrors(mggpe.errors[mgg])
