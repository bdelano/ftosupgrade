import os
import logging
import json
from upload import *
from peconnect import *
from mysql import *

class prepare():
    def __init__(self,**kw):
        self.hostname=kw['hostname']
        self.info("----------------\npreparing %s for upgrade..." % self.hostname)
        self.binfilepath=kw['binfilepath']
        self.binfile=kw['options'].binfile
        self.options=kw['options']
        self.path=os.getcwd()+'/'+self.hostname
        self.log=self.path+'/raw.log'
        self.devinfofile=self.path+'/devinfo.json'
        self.errors=list()
        self.devinfo={}
        self.bfsw=''
        self.setupworkspace()
        open(self.path+'/raw.log','w')
        logging.basicConfig(filename=self.log,level=logging.DEBUG)
        if self.devinfo.has_key('status') and self.devinfo['status']=='success' and self.options.noforce:
            self.info("Looks like this device has already been setup")
            self.info("please delete %s to force!" % self.devinfofile)
        else:
            self.getOGdetails()
            self.checkOG()
            self.info('--connecting to device')
            self.pe=pelogon(ip=self.hostname,logfile=self.path+'/raw.log')
            self.checkbinfile()
            if self.devinfo['binfilestatus'].has_key('error'):
                self.info(self.devinfo['binfilestatus']['error'])
            else:
                self.version=self.pe.bootinfo['primary']['version']
                if self.devinfo['oginfo'].has_key('mgmtip'):
                    if self.pe.prompt != self.og.prompt:
                        self.errors.append('The prompt on the opengear does not match! Please investigate!')
                self.pe.runchecks(path=self.path,type='pre')
                self.info('---updating boot info, this may take a little while...')
                self.updateBoot()
                if len(self.pe.errors)>0 or len(self.errors)>0:
                    self.info('---found errors restoring config boot order!')
                    self.pe.setBoot(self.devinfo['bootinfo']['primary']['slot'],self.devinfo['bootinfo']['secondary']['slot'])
                    for e in self.pe.errors: self.uperrors.append('di'+str(e))

            #closing connection
            self.pe.e.terminate()
            self.errors=self.errors+self.pe.errors
            if len(self.errors)>0:
                self.devinfo['status']='fail'
                self.info('preparation failed because of the following errors!')
                for e in self.errors:
                    self.info('-'+e)
                self.info('see the raw log for more details!')
                self.info('cat %s' % self.path+'/raw.log')
            else:
                f=open(self.devinfofile,'w')
                self.devinfo['status']='success'
                self.info('--writing %s...' % self.devinfofile)
                f.write(json.dumps(self.devinfo))
                self.info('preparation completed successfully feel free to upgrade')
        print('----------------')


    def checkOG(self):
        self.info('--checking opengear connectivity...')
        if self.devinfo['oginfo'].has_key('mgmtip'):
            self.og=pelogon(ip=self.devinfo['oginfo']['mgmtip'],port=self.devinfo['oginfo']['interface'],logfile=self.path+'/raw.log',og=1)
            self.og.remlogon()
            self.devinfo['oginfo']['status']=self.og.status
            self.devinfo['oginfo']['vendor']=self.og.vendor
            self.devinfo['oginfo']['message']=self.og.message
            if self.og.status != 'success':
                self.errors.append('og:'+str(self.og.message))
            else:
                self.og.getbootinfo()
            self.og.e.terminate()



    def updateBoot(self):
        self.devinfo['bootinfo']=self.pe.bootinfo
        curprimary=self.devinfo['bootinfo']['primary']['slot']
        altslot={'A':'B','B':'A'}
        print(self.devinfo['bootinfo']['secondary']['version'])
        print(self.devinfo['bootinfo'])
        if self.bfsw==self.devinfo['bootinfo']['secondary']['version']:
            self.info('----skipping sys flash upgrade as its already in place!')
        else:
            self.pe.e.sendline('upgrade sys flash: %s:' % altslot[curprimary])
            self.pe.e.expect("Source file name \[\]:")
            self.pe.e.sendline(self.binfile)
            self.pe.e.expect(self.pe.prompt,timeout=None)
            self.devinfo['bootinfo']=self.pe.getbootinfo()

        if self.bfsw==self.devinfo['bootinfo']['secondary']['version']:
            self.pe.setBoot(altslot[curprimary],curprimary)
        else:
            self.errors.append('version %s does not match the binary %s' (self.devinfo['bootinfo']['secondary']['version'],self.bfsw))


    def checkbinfile(self):
        vrx=re.compile("FTOS-[\w]+-([\d]+\.[\d]+)\.([\d]+\.[\d]+)\.bin")
        self.devinfo['files']=self.pe.getfilelist()
        if self.binfile:
            bfm=vrx.match(self.binfile)
            if bfm:
                self.bfsw=bfm.group(1)+'('+bfm.group(2)+')'
                self.devinfo['binswversion']=self.bfsw
                if path.exists('%s%s' % (self.binfilepath,self.binfile)):
                    if self.devinfo['files'].has_key(self.binfile):
                        binres=self.pe.getCommand('verify md5 flash://%s %s' % (self.binfile,binmd5[self.binfile]))
                        if 'FAILED' in binres:
                            self.devinfo['binfilestatus']={'error':binres}
                        else:
                            self.devinfo['binfilestatus']={'succcess':'binfile (%s) exists' % self.binfile}
                    else:
                        self.info('binfile does not exist..')
                        self.info('uploading %s to %s, please be patient...')
                        u=uploadbin(hostname=self.hostname,binfile=self.binfile,binfilepath=self.binfilepath)
                        print(json.dumps(u.uploadinfo,indent=4))
                        self.devinfo['binfilestatus']=u.uploadinfo['binfilestatus']
                        #self.devinfo['binfilestatus']={'error':'binfile (%s) does not exist' % self.binfile}
                else:
                    self.devinfo['binfilestatus']={'error':'cannot find local file %s%s' % (self.binfilepath,self.binfile)}
            else:
                self.devinfo['binfilestatus']={'error':'binfile does not match expected format:%s' % self.binfile}
            if self.devinfo['binfilestatus'].has_key('error'):
                self.errors.append(self.devinfo['binfilestatus']['error'])


            #still need to write something to test a couple of comands



    def info(self,msg):
        print(str(msg))

    def getOGdetails(self):
        self.info('--getting opengear details...')
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
            self.errors.append('ogerror:unable to get opengear details!')
            self.devinfo['oginfo']={'error':'unable to get opengear details!'}

    def setupworkspace(self):
        self.info("--Setting up your workspace...")
        if(os.path.exists(self.path)):
            if os.path.isfile(self.devinfofile):
                f=open(self.devinfofile,'r')
                try:
                    self.devinfo=json.loads(f.read())
                except:
                    logging.warning('unable to read the devinfofile:%s' % self.devinfofile)
                    self.errors.append('unable to read the devinfofile:%s' % self.devinfofile)
                    self.devinfo={}
        else:
            self.info("--creating necessary directories...")
            os.mkdir(self.path)
            os.mkdir(self.path+'/pre')
            os.mkdir(self.path+'/post')
        #print(os.path.isdir("/home/el"))
        #print(os.path.exists("/home/el/myfile.txt"))
