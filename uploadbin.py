#!/opt/local/scripts/python/ftosupgrade/bin/python2.7
import json
import logging
import time
import os
from peconnect import *
from myutilities import *
from mysql import *
BINFILE='FTOS-SK-9.14.1.0.bin'
BINFILEPATH='/tftpboot/Dell/'
NUMFORKS=10
REGION='us-east'

class uploadbin:
    def __init__(self,hostname):
        print("working on %s..." % hostname)
        self.binfile=BINFILE
        self.binfilepath=BINFILEPATH
        self.devinfo={}
        logging.basicConfig(filename='%s.log' % hostname,level=logging.DEBUG)
        self.pe=pelogon(ip=hostname,debug=1,binfile=self.binfile,binfilepath=self.binfilepath)
        self.checkbinfile()
        if self.devinfo['binfilestatus'].has_key('error'):
            ferror=self.devinfo['binfilestatus']['error']
            if 'local' in ferror:
                logging.critical(ferror)
            else:
                logging.info(self.devinfo['binfilestatus']['error'])
                pe.scpfile()
                self.checkbinfile()
                logging.info(self.devinfo['binfilestatus'])
        else:
            logging.info(self.devinfo['binfilestatus'])
        self.pe.exit()
        os._exit(0)

    def checkbinfile(self):
        self.devinfo['files']=self.pe.getfilelist()
        if self.binfile:
            if bfm:
                if path.exists('%s%s' % (self.binfilepath,self.binfile)):
                    if self.devinfo['files'].has_key(self.binfile):
                        binres=self.pe.getCommand('verify md5 flash://%s %s' % (self.binfile,binmd5[self.binfile]))
                        if 'FAILED' in binres:
                            self.devinfo['binfilestatus']={'error':binres}
                        else:
                            self.devinfo['binfilestatus']={'succcess':'binfile (%s) exists' % self.binfile}
                    else:
                        self.devinfo['binfilestatus']={'error':'binfile (%s) does not exist' % self.binfile}
                else:
                    self.devinfo['binfilestatus']={'error':'cannot find local file %s%s' % (BINFILEPATH,self.binfile)}
            else:
                self.devinfo['binfilestatus']={'error':'binfile does not match expected format:%s' % self.binfile}
            if self.devinfo['binfilestatus'].has_key('error'):
                self.errors.append(self.devinfo['binfilestatus']['error'])



def testchild(hostname):
    print("working on hostname:%s" % hostname)
    time.sleep(10)
    os._exit(0)

def makeforks(mylist,child):
    print(mylist)
    for hn in mylist:
        pid=os.fork()
        if pid == 0:
            child(hn)
        else:
            pids = (os.getpid(), pid)
    for i in range(len(mylist)):
        finished = os.waitpid(0, 0)
    print("all done")

def gethosts():
    dbh=mysql()
    sql="""
    select trignodename
    from devices as d
    join sites as s on s.id=d.siteid
    where d.newreq='tor'
    and d.vendor='dell'
    and s.regionname='{region}'
    and d.label like '%stg' limit 1
    """.format(region=REGION)
    dbh.buildretdict(sql)
    flist=list()
    i=0
    for o in dbh.retdict:
        hn=o['trignodename']
        if i<int(NUMFORKS):
            flist.append(hn)
            i=i+1
        else:
            i=0
            makeforks(flist,uploadbin)
            flist=[hn]
    makeforks(flist,uploadbin)

gethosts()
