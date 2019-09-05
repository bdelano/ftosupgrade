import os
import logging
import json
from upload import *
from peconnect import *
from mysql import *

class prepare():
    def __init__(self,**kw):
        self.m=kw['message']
        self.hostname=self.m.hostname
        self.m.info("----------------\npreparing %s for upgrade..." % self.hostname,attrs='bold')
        self.devinfo={}
        self.loaddevinfo()
        self.bfsw=''
        #reset log files
        if (self.devinfo.has_key('prepstatus') and self.devinfo['prepstatus']=='success' and self.m.options.noforce):
            self.m.info("Looks like this device has already been prepared, moving on...",attrs='bold')
            self.m.info("please delete %s to force!" % self.m.devinfofile)
            #self.checkOG()
        else:
            self.m.resetlogs()
            self.getOGdetails()
            self.checkOG()
            self.m.info('--connecting to device via ssh')
            self.pe=pelogon(message=self.m)
            self.checkbinfile()
            if self.devinfo['binfilestatus'].has_key('error'):
                self.m.info(self.devinfo['binfilestatus']['error'])
            else:
                self.version=self.pe.bootinfo['primary']['version']
                if self.devinfo['oginfo'].has_key('mgmtip'):
                    if self.pe.prompt != self.og.prompt:
                        self.m.critial('The prompt on the opengear (%s) does not match! Please investigate!' % self.og.prompt)
                self.pe.runchecks('pre')
                self.m.info('---updating boot info, this may take a little while...')
                self.updateBoot()
                if len(self.m.errors[self.hostname]['critical'])>0:
                    self.m.info('---found errors restoring config boot order!')
                    self.pe.setBoot(self.devinfo['bootinfo']['primary']['slot'],self.devinfo['bootinfo']['secondary']['slot'])

            #closing connection
            self.pe.e.terminate()
            self.devinfo['errors']={'prepare':self.m.errors[self.hostname]}
            if len(self.m.errors[self.hostname]['critical'])>0:
                self.devinfo['prepstatus']='fail'
                self.m.warning('\nErrors found during preparation please check the logs!')
            else:
                self.devinfo['prepstatus']='success'
                self.m.info('\npreparation completed successfully feel free to upgrade',attrs='bold')
            self.m.writedevinfo(self.devinfo)


    def checkOG(self):
        """
        logs into opengear device and runs getbootinfo() function to assign a prompt
        """
        self.m.info('--checking opengear connectivity...')
        if self.devinfo['oginfo'].has_key('mgmtip'):
            self.og=pelogon(ip=self.devinfo['oginfo']['mgmtip'],port=self.devinfo['oginfo']['interface'],og=1,message=self.m)
            self.og.remlogon()
            self.devinfo['oginfo']['status']=self.og.status
            self.devinfo['oginfo']['vendor']=self.og.vendor
            self.devinfo['oginfo']['message']=self.og.message
            if self.og.status == 'success':
                self.og.getbootinfo()
                self.m.info('---opengear clean, logging out...')
            else:
                self.m.critical(self.og.message)
            self.og.e.terminate()

    def loaddevinfo(self):
        if os.path.isfile(self.m.devinfofile):
            f=open(self.m.devinfofile,'r')
            try:
                self.devinfo=json.loads(f.read())
            except:
                self.m.warning('unable to read the devinfofile:%s' % self.m.devinfofile)


    def updateBoot(self):
        """
        using the bootinfo detail from the peconnect module this function checks if the
        correct version is assigned to the alternate slot and updates it if it is not assigned
        """
        self.devinfo['bootinfo']=self.pe.bootinfo
        curprimary=self.devinfo['bootinfo']['primary']['slot']
        altslot={'A':'B','B':'A'}
        self.m.debug('BFSW:%s' % self.bfsw)
        self.m.debug('SECONDARYSW:%s' % self.devinfo['bootinfo']['secondary']['version'])
        if self.bfsw==self.devinfo['bootinfo']['secondary']['version']:
            self.m.info('----skipping sys flash upgrade as its already in place!')
        else:
            self.m.info('upgrading system flash')
            self.pe.e.logfile = sys.stdout
            self.pe.e.sendline('upgrade sys flash: %s:' % altslot[curprimary])
            self.pe.e.expect("Source file name \[\]:")
            self.pe.e.sendline(self.m.binfile)
            self.pe.e.expect(self.pe.prompt,timeout=None)
            self.pe.e.logfile=open(self.m.peclog, 'a')
            self.pe.getbootinfo()
            self.devinfo['bootinfo']=self.pe.bootinfo

        if self.bfsw==self.devinfo['bootinfo']['secondary']['version']:
            self.pe.setBoot(altslot[curprimary],curprimary)
        else:
            self.m.critical('version %s does not match the binary %s' (self.devinfo['bootinfo']['secondary']['version'],self.bfsw))


    def checkbinfile(self):
        """
        gets code version from ftos file and validates that the file is uploaded
        to the switch and md5 matches, if it is not, it tries to upload the file.
        """
        vrx=re.compile("FTOS-[\w]+-([\d]+\.[\d]+)\.([\d]+\.[\w]+)\.bin")
        self.devinfo['files']=self.pe.getfilelist()
        if self.m.binfile:
            bfm=vrx.match(self.m.binfile)
            if bfm:
                self.bfsw=bfm.group(1)+'('+bfm.group(2)+')'
                self.devinfo['binswversion']=self.bfsw
                if path.exists('%s%s' % (self.m.binfilepath,self.m.binfile)):
                    if self.devinfo['files'].has_key(self.m.binfile):
                        binres=self.pe.getCommand('verify md5 flash://%s %s' % (self.m.binfile,binmd5[self.m.binfile]))
                        if 'FAILED' in binres:
                            self.devinfo['binfilestatus']={'error':binres}
                        else:
                            self.devinfo['binfilestatus']={'succcess':'binfile (%s) exists' % self.m.binfile}
                    else:
                        self.m.info('binfile does not exist..')
                        u=uploadbin(message=self.m)
                        self.devinfo['binfilestatus']=u.uploadinfo['binfilestatus']
                else:
                    self.devinfo['binfilestatus']={'error':'cannot find local file %s%s' % (self.m.binfilepath,self.m.binfile)}
            else:
                self.devinfo['binfilestatus']={'error':'binfile does not match expected format:%s' % self.m.binfile}
            #check if an error exists
            if self.devinfo['binfilestatus'].has_key('error'):
                self.m.critical(self.devinfo['binfilestatus']['error'])


            #still need to write something to test a couple of comands

    def getOGdetails(self):
        """
        pulls opengear details from our mysql database
        """
        self.m.info('--getting opengear details...')
        self.dbh=mysql()
        sql="""
        select d.label,d.mgmtip,l.interface
        from layer2 as l join devices as d on d.id=l.hostid
        where d.label like '%oob'
        and l.description like '{hostname}'
        """.format(hostname=self.hostname)
        self.dbh.buildretdict(sql)
        if len(self.dbh.retdict)==1:
            self.devinfo['oginfo']=self.dbh.retdict[0]
        else:
            self.m.critial('ogerror:unable to get opengear details!')
            self.devinfo['oginfo']={'error':'unable to get opengear details!'}

        #print(os.path.isdir("/home/el"))
        #print(os.path.exists("/home/el/myfile.txt"))
