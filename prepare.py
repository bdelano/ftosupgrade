import os
import logging
import json
from peconnect import *
from mysql import *
from ogconnect import *

class prepare():
    def __init__(self,**kw):
        self.hostname=kw['hostname']
        self.info("working on %s..." % self.hostname)
        self.binfile=kw['options'].binfile
        self.options=kw['options']
        self.path=os.getcwd()+'/'+self.hostname
        self.upinfofile=self.path+'/devinfo.json'
        self.errors=list()
        self.upinfo={}
        open(self.path+'/raw.log','w')
        logging.basicConfig(filename=self.path+'/raw.log',level=logging.DEBUG)
        self.setupworkspace()
        if self.upinfo.has_key('status') and self.upinfo['status']=='success' and self.options.noforce:
            self.info("Looks like this device has already been setup")
            self.info("please delete %s to force!" % self.upinfofile)
        else:
            self.getOGdetails()
            self.checkOG()
            self.info('--connecting to device')
            self.pe=pelogon(ip=self.hostname,binfile=self.binfile,logfile=self.path+'/raw.log')
            self.runprescripts()
            self.info('---updating boot info, this may take a little while...')
            self.pe.updateBoot()
            self.upinfo['devinfo']=self.pe.devinfo
            if len(self.pe.errors)>0 or len(self.errors)>0:
                self.info('---found errors restoring config boot order!')
                self.pe.restoreBoot()
                for e in self.pe.errors: self.uperrors.append('di'+str(e))

            #closing connection
            self.pe.e.terminate()
            if len(self.errors)>0:
                self.upinfo['status']='fail'
                self.info('preparation failed because of the following errors!')
                for e in self.errors:
                    self.info('-'+e)
                self.info('see the raw log for more details!')
                self.info('cat %s' % self.path+'/raw.log')
            else:
                f=open(self.upinfofile,'w')
                self.upinfo['status']='success'
                self.info('--writing %s...' % self.upinfofile)
                f.write(json.dumps(self.upinfo))
                self.info('preparation completed successfully feel free to upgrade')

            #finishing


    def checkOG(self):
        self.info('--checking opengear connectivity...')
        if self.upinfo['oginfo'].has_key('mgtmip'):
            self.og=oglogon(ip=self.upinfo['oginfo']['mgmtip'],port=self.upinfo['oginfo']['interface'],logfile=self.path+'/raw.log')
            self.og.remlogon()
            self.og.e.terminate()
            self.upinfo['oginfo']['status']=og.status
            self.upinfo['oginfo']['vendor']=og.vendor
            self.upinfo['oginfo']['message']=og.message
            if og.status != 'success': self.errors.append('og:'+str(message))

    def runprescripts(self):
        self.info('---running PRE commands')
        precommands=[
        {'cmd':'show alarm |no-more','fn':'shalarm'},
        {'cmd':'show vlt br |no-more','fn':'shvlt'},
        {'cmd':'show int desc |no-more','fn':'shintdescr'},
        {'cmd':'show lldp nei |no-more','fn':'shlldp'}
        ]
        for o in precommands:
            f=open(self.path+'/pre/'+o['fn']+'.cmd','w')
            self.info('----running command: %s...' % o['cmd'])
            cmdres=self.pe.getCommand(o['cmd'])
            f.write(cmdres)
            f.close()
            if o['fn']=='shvlt':
                self.checkvlt(cmdres)
            elif o['fn']=='shalarm':
                self.checkalarms(cmdres)


            #still need to write something to test a couple of comands

    def checkalarms(self,cmdres):
        if 'No minor alarms' not in cmdres:
            self.errors.append('Minor alarms found please see: shalarm.cmd')
        if  'No major alarms' not in cmdres:
            self.errors.append('Major alarms found please see: shalarm.cmd')

    def checkvlt(self,cmdres):
        resdict={}
        for l in cmdres.split("\r\n"):
            if ':' in l:
                (k,v)=l.split(':',1)
                resdict[k.rstrip().lstrip()]=v.lstrip().lower()
        keys=['ICL Link Status','HeartBeat Status','VLT Peer Status']
        for chk in keys:
            if resdict[chk] != 'up':
                self.errors.append('vlterror:%s is not up (%s)' % (chk,resdict[chk]))


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
            self.upinfo['oginfo']=self.dbh.retdict[0]
        else:
            self.errors.append('ogerror:unable to get opengear details!')
            self.upinfo['oginfo']={'error':'unable to get opengear details!'}

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
