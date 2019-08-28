#!/opt/local/scripts/python/ftosupgrade/bin/python2.7
import json
import logging
import os
from peconnect import *
from mysql import *
BINFILE='FTOS-SK-9.14.1.0.bin'

def uploadbin(hostname):
    logging.basicConfig(filename='%s.log' % hostname,level=logging.DEBUG)
    pe=peconnect(ip=hostname,debug=1,binfile=BINFILE)
    if pe.devinfo['binfilestatus'].has_key('error'):
        ferror=pe.devinfo['binfilestatus']['error']
        if 'local' in ferror:
            logging.critical(ferror)
        else:
            logging.info(pe.devinfo['binfilestatus']['error'])
            pe.scpfile()
            pe.checkbinfile()
            logging.info(pe.devinfo['binfilestatus'])
    else:
        logging.info(pe.devinfo['binfilestatus'])
    pe.exit()
    os._exit(0)

def makeforks(mylist,child):
    print(mylist)
    for hn in mylist:
        pid=os.fork()
        if pid == 0:
            child(hn)
        else:
            pids = (os.getpid(), pid)
            #print("parent: %d, child: %d" % pids)
    for i in range(len(mylist)):
        finished = os.waitpid(0, 0)
        #print(finished)
    print("all done")
    print(mylist)

def gethosts():
    dbh=mysql()
    sql="""
    select trignodename
    from devices as d
    join sites as s on s.id=d.siteid
    where d.newreq='tor'
    and d.vendor='dell'
    and s.regionname='ap-southeast'
    limit 5
    """
    dbh.buildretdict(sql)
    flist=list()
    i=0
    for o in dbh.retdict:
        hn=o['trignodename']
        print hn
        print(i)
        if i<4:
            flist.append(hn)
            print(flist)
            i=i+1
        else:
            i=0
            makeforks(flist,uploadbin)
            flist=[hn]
    makeforks(flist,uploadbin)

gethosts()
#uploadbin('sin301-tor01-0310')
