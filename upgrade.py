import os
import logging
import json
from peconnect import *
from mysql import *
from ogconnect import *

class upgrade():
    def __init__(self,**kw):
        self.hostname=kw['hostname']
        self.info("upgrading %s..." % self.hostname)
        self.binfile=kw['options'].binfile
        self.options=kw['options']
        self.path=os.getcwd()+'/'+self.hostname
        self.upinfofile=self.path+'/devinfo.json'
        self.errors=list()
        self.upinfo={}
        self.status='fail'
        logging.basicConfig(filename=self.path+'/raw.log',level=logging.DEBUG)
        self.checkworkspace()
        if self.status=='prepare':
            self.info('unable to find directories, trying to run prepare script!')
        else:
            self.info('-connecting to opengear...')
            self.og=oglogon(ip=self.upinfo['oginfo']['mgmtip'],port=self.upinfo['oginfo']['interface'],logfile=self.path+'/raw.log')
            self.og.remlogon()
            time.sleep(1)
            if self.og.status=='success' and self.og.vendor=='dell':
                self.info('-connected, reloading device...')
                self.og.e.sendline('dir |no-more')
                self.og.e.logfile=sys.stdout
                self.og.waitforstream()
                self.og.e.sendline('exit')
                self.og.waitforstream()
                self.og.e.sendline()
                self.og.message='login'
                self.og.remlogon()
                print(self.og.status)
                print(self.og.message)
                self.info('data:'+self.og.wfsll)
            else:
                self.errors.append('unable to login to opengear:%s' % og.message)
                self.info('unable to login to opengear!','error')
            self.og.e.terminate()
        self.info('finished')

    def runpostscripts(self):
        self.info('---running POST commands')
        precommands=[
        {'cmd':'show alarm |no-more','fn':'shalarm'},
        {'cmd':'show vlt br |no-more','fn':'shvlt'},
        {'cmd':'show int desc |no-more','fn':'shintdescr'},
        {'cmd':'show lldp nei |no-more','fn':'shlldp'}
        ]
        for o in precommands:
            f=open(self.path+'/post/'+o['fn']+'.cmd','w')
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
