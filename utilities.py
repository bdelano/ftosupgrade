import os
from os.path import expanduser
import time
import json
import sys
import logging
import datetime
import re
from mysql import mysql
from termcolor import colored
from terminaltables import AsciiTable

class utils:
    def __init__(self,**kw):
        """
        set of tools which can be used by all classes
        """
        self.options=kw['options']
        self.hostname=kw['hostname']
        self.binfilepath=self.options.binfilepath
        self.binfile=self.options.binfile
        self.silent=False
        if kw.has_key('silent'): self.silent=kw['silent']
        self.inittime=time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        self.timedict={}
        self.devinfo={}
        self.path=expanduser("~")+'/ftosupgrade'
        self.devpath=self.path+'/'+self.hostname+'/'
        self.devinfofile=self.devpath+'devinfo.json'
        self.errors={self.hostname:{'warning':list(),'critical':list()}}
        self.log=self.devpath+'info.log'
        self.peclog=self.devpath+'commands.log'
        self.errorlog=self.devpath+'errors.log'
        self.logger=logging.getLogger('messages')
        self.dbh=mysql()

    def writedevinfo(self):
        """
        write devinfo to .json file (saves state)
        """
        f=open(self.devinfofile,'w')
        self.info('-writing %s...' % self.devinfofile)
        f.write(json.dumps(self.devinfo))

    def writeerrors(self):
        """
        write errors to a log
        """
        f=open(self.errorlog,'w')
        for et in ['warning','critical']:
            for l in self.errors[self.hostname][et]:
                f.write("{t} : {m}\n".format(m=l['message'],t=l['tstamp']))

    def resetlogs(self):
        """
        just clears the logs (every time prepare is fully run)
        """
        open(self.log,'w')
        open(self.peclog,'w')

    def getelapse(self,key):
        """
        used for tracking how long a task takes, can be run by just starting a
        timer with a key and then rnning again.. results pulled from dictionary
        """
        if self.timedict.has_key(key):
            start=self.timedict[key]['start']
            end=time.timer()
            elapse=end-start
            self.timedict[key]={'start':start,'end':end,'elapse':elapse}
        else:
            self.timedict[key]={'start':time.timer()}

    def setupworkspace(self):
        """
        creates necessary directories and file structure for the tool to work
        """
        if not os.path.exists(self.devpath):
            if not self.silent: print("-Setting up your workspace...")
            if not self.silent: print("--creating necessary directories...")
            if not os.path.exists(self.path):
                if not self.silent: print("---creating %s" % self.path)
                os.mkdir(self.path)
            if not self.silent: print("---creating %s" % self.devpath)
            os.mkdir(self.devpath)
            if not self.silent: print("---creating %spre" % self.devpath)
            os.mkdir(self.devpath+'pre')
            if not self.silent: print("---creating %spost" % self.devpath)
            os.mkdir(self.devpath+'post')
        self.setLogging()

    def loaddevinfo(self):
        """
        load device state information from json file
        """
        if os.path.isfile(self.devinfofile):
            f=open(self.devinfofile,'r')
            try:
                self.devinfo=json.loads(f.read())
            except:
                self.warning('unable to read the devinfofile:%s' % self.devinfofile)

    def setLogging(self):
        log=logging.getLogger()
        for hdlr in log.handlers[:]: log.removeHandler(hdlr)
        logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s',
        filename=self.devpath+'/info.log',
        level=logging.DEBUG,
        datefmt='%Y-%m-%d %H:%M:%S')

    def writetoinfo(self,msg,type):
        ts=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        m="%s:%s:%s\n" % (ts,type,msg)
        self.logger.write(m)


    def debug(self,msg):
        self.logger.debug(msg)

    def info(self,msg,**kw):
        atlist=list()
        if kw.has_key('attrs'):
            atlist.append(kw['attrs'])
        self.logger.info(msg)
        if not self.silent: print(str(colored(msg,'green',attrs=atlist)))

    def warning(self,msg):
        m='WARNING:%s' % msg
        self.logger.warning(msg)
        if not self.silent: print(colored(m,'yellow'))
        self.addError(str(msg),'warning')

    def critical(self,msg):
        m='CRITICAL:%s' % msg
        self.logger.critical(m)
        print(colored(m,'red'))
        self.addError(str(msg),'critical')

    def addError(self,m,level):
        self.errors[self.hostname][level].append({'tstamp':time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),'message':m})

    def combineerrors(self,remerrors):
        for et in ['warning','critical']:
            for e in remerrors[et]:
                self.errors[self.hostname][et].append(e)

    def getMGG(self):
        """
        checks devinfo for previous list if its not there...
        it gets partial name for mgg and uses it to search db
        """
        if 'mgglist' in self.devinfo:
            self.debug('found mgglist in devinfo!')
            self.mgg=self.devinfo['mgglist']
        else:
            mggpfrx=re.compile("^([\w]{3})(([\d])[\d]+)-.*")
            self.info('--searching for nearest mgg switches')
            mggpfm=mggpfrx.match(self.hostname)
            if mggpfm:
                mgg=mggpfm.group(1)+mggpfm.group(3)+'%mgg%'
                self._findMGG(mgg)
            else:
                self.warning('Unable to match name prefix for mgg, no mgg found!')


    def _findMGG(self,mgg):
        """
        finds the nearest mgg to check for looped port bug.
        """
        self.mgg=list()
        sql="select trignodename from devices where trignodename like '{mgg}' and label not like '%lab%'".format(mgg=mgg)
        self.debug('mggsql:%s' % sql)
        self.dbh.buildretdict(sql)
        if len(self.dbh.retdict)>0:
            for o in self.dbh.retdict:
                self.mgg.append(o['trignodename'])
            self.devinfo['mgglist']=self.mgg
        else:
            self.warning('No MGG switches could be found, please check manually!')



    def getOGdetails(self):
        """
        pulls opengear details from our mysql database
        """
        self.info('--getting opengear details...')
        sql="""
        select d.label,d.mgmtip,l.interface
        from layer2 as l
        join devices as d on l.hostid=d.id
        left outer join devices as rp on rp.id=l.ifid
        where d.label like '%-oob'
        and rp.trignodename='{hostname}'
        """.format(hostname=self.hostname)
        self.dbh.buildretdict(sql)
        if len(self.dbh.retdict)==1:
            self.devinfo['oginfo']=self.dbh.retdict[0]
        else:
            self.critical('ogerror:unable to get opengear details!')
            self.devinfo['oginfo']={'error':'unable to get opengear details!'}
