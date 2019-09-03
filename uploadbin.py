#!/opt/local/scripts/python/ftosupgrade/bin/python2.7
import json
import logging
import time
import os
from upload import *
from peconnect import *
from myutilities import *
from mysql import *
BINFILE='FTOS-SK-9.14.1.0.bin'
BINFILEPATH='/tftpboot/Dell/'
NUMFORKS=10
REGION='us-east'

def makeforks(mylist,child):
    print(mylist)
    for hn in mylist:
        pid=os.fork()
        if pid == 0:
            child(hostname=hn,binfile=BINFILE,binfilepath=BINFILEPATH,logfile=hn+'.log',multi=True)
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
    and d.label like '%stg' limit 10
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
