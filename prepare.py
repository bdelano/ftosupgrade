import os
import logging
import json
import re
import sys
from utilities import utils
from upload import uploadbin
from peconnect import pelogon
from localauth import binmd5

class prepare(utils):
    def __init__(self,**kw):
        """
        get opengear connection from mysql and test connection
        check that binary file is valid (on device md5 matches)
        run pre-checks and check for errors
        update the alternate boot loader and change the configuration so next reload upgrades
        """
        utils.__init__(self,**kw)
        self.info("----------------\npreparing %s for upgrade..." % self.hostname,attrs='bold')
        self.loaddevinfo()
        self.bfsw=''
        self.mgg=None
        #reset log files
        if (self.devinfo.has_key('prepstatus') and self.devinfo['prepstatus']=='success' and self.options.noforce):
            self.info("Looks like this device has already been prepared, moving on...",attrs='bold')
            self.info("please delete %s to force!" % self.devinfofile)
            #self.checkOG()
        else:
            self.resetlogs()
            self.getOGdetails()
            if 'error' not in self.devinfo['oginfo']:
                self.checkOG()
                self.checkMGG()
                self.info('--connecting to device via ssh')
                self.pe=pelogon(hostname=self.hostname,options=self.options)
                self.pe.getbootinfo()
                self.devinfo['bootinfo']=self.pe.bootinfo
                self.checkbinfile()
                if self.bfsw==self.devinfo['bootinfo']['primary']['version'] and self.options.noforce:
                    self.critical("Looks like this switch is already running %s, please check you are looking at the correct switch!" % self.bfsw)
                elif self.devinfo['binfilestatus'].has_key('error'):
                    self.info(self.devinfo['binfilestatus']['error'])
                else:
                    self.version=self.pe.bootinfo['primary']['version']
                    if self.devinfo['oginfo'].has_key('mgmtip'):
                        if self.pe.prompt != self.og.prompt:
                            self.critical('The prompt on the opengear (%s) does the one on the switch (%s)! Please investigate!' % (self.og.prompt,self.pe.prompt))
                        else:
                            self.pe.runchecks('pre')
                            if len(self.pe.errors[self.hostname]['critical'])<1:
                                self.info('---updating boot info, this may take a little while...')
                                self.updateBoot()
                #closing connection
                self.info('--exiting device...')
                self.pe.exit()
                self.combineerrors(self.pe.errors[self.hostname])
            self.devinfo['errors']={'prepare':self.errors[self.hostname]}
            if len(self.errors[self.hostname]['critical'])>0:
                self.devinfo['prepstatus']='fail'
                self.warning('\nErrors found during preparation please check the logs!')
            else:
                self.devinfo['prepstatus']='success'
                self.info('\npreparation completed successfully feel free to upgrade',attrs='bold')
            self.writedevinfo()


    def checkOG(self):
        """
        logs into opengear device and runs getbootinfo() function to assign a prompt
        """
        self.info('--checking opengear connectivity...')
        if self.devinfo['oginfo'].has_key('mgmtip'):
            self.og=pelogon(hostname=self.hostname,options=self.options,ip=self.devinfo['oginfo']['mgmtip'],port=self.devinfo['oginfo']['interface'],og=1)
            self.og.remlogon()
            self.devinfo['oginfo']['status']=self.og.status
            self.devinfo['oginfo']['vendor']=self.og.vendor
            self.devinfo['oginfo']['message']=self.og.message
            if self.og.status == 'success':
                self.og.getbootinfo()
                self.info('---opengear clean, logging out...')
            else:
                self.critical(self.og.message)
            self.og.e.terminate()

    def updateBoot(self):
        """
        using the bootinfo detail from the peconnect module this function checks if the
        correct version is assigned to the alternate slot and updates it if it is not assigned
        """
        curprimary=self.devinfo['bootinfo']['primary']['slot']
        altslot={'A':'B','B':'A'}
        self.debug('BFSW:%s' % self.bfsw)
        self.debug('SECONDARYSW:%s' % self.devinfo['bootinfo']['secondary']['version'])
        if self.bfsw==self.devinfo['bootinfo']['secondary']['version']:
            self.info('----skipping sys flash upgrade as its already in place!')
        else:
            self.info('upgrading system flash')
            self.pe.upgradesysflash(altslot[curprimary])
            self.devinfo['bootinfo']=self.pe.bootinfo

        if self.bfsw==self.devinfo['bootinfo']['secondary']['version']:
            self.info('---setting boot configuration...')
            self.pe.setBoot(altslot[curprimary],curprimary)
        else:
            self.critical('version %s does not match the binary %s' (self.devinfo['bootinfo']['secondary']['version'],self.bfsw))


    def checkbinfile(self):
        """
        gets code version from ftos file and validates that the file is uploaded
        to the switch and md5 matches, if it is not, it tries to upload the file.
        """
        vrx=re.compile("FTOS-[\w]+-([\d]+\.[\d]+)\.([\d]+\.[\w]+)\.bin")
        self.devinfo['files']=self.pe.getfilelist()
        if self.binfile:
            bfm=vrx.match(self.binfile)
            if bfm:
                self.bfsw=bfm.group(1)+'('+bfm.group(2)+')'
                self.devinfo['binswversion']=self.bfsw
                if os.path.exists('%s%s' % (self.binfilepath,self.binfile)):
                    if self.devinfo['files'].has_key(self.binfile):
                        binres=self.pe.getCommand('verify md5 flash://%s %s' % (self.binfile,binmd5[self.binfile]))
                        if 'FAILED' in binres:
                            self.devinfo['binfilestatus']={'error':binres}
                        else:
                            self.devinfo['binfilestatus']={'succcess':'binfile (%s) exists' % self.binfile}
                    else:
                        self.info('binfile does not exist..')
                        u=uploadbin(hostname=self.hostname,options=self.options)
                        self.devinfo['binfilestatus']=u.uploadinfo['binfilestatus']
                else:
                    self.devinfo['binfilestatus']={'error':'cannot find local file %s%s' % (self.binfilepath,self.binfile)}
            else:
                self.devinfo['binfilestatus']={'error':'binfile does not match expected format:%s' % self.binfile}
            #check if an error exists
            if self.devinfo['binfilestatus'].has_key('error'):
                self.critical(self.devinfo['binfilestatus']['error'])


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
