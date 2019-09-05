#!/opt/local/scripts/python/ftosupgrade/bin/python2.7
import os
import sys          # for handling arguments
import re            # for regular expressions
import time            # for sleep and time related functions
import logging
from optparse import OptionParser
from messages import *
from prepare import *
from upgrade import *
from backout import *
from upload import *
VERSION='1.0BETA'
BINFILEPATH='/tftpboot/Dell/'

class main():
    def __init__(self):
        parser = OptionParser("usage: ftosupgrade <options>")
        parser.add_option("-d", "--devices", dest="devices",
            help="List of devices to upgrade separated by a ','", default=None)
        parser.add_option("-r", "--region", dest="region",
            help="Any region e.g us-east (for uploads only!)", default=None)
        parser.add_option("-t", "--type",dest="type",
            help="This can be prepare,upgrade,backout, or upload",
            choices=['upload','prepare','upgrade','backout'],
            default='prepare')
        parser.add_option("-b","--binfile",dest="binfile",
            help="The name of the binary file you are using for the upgrade e.g. FTOS-SK-9.14.1.0.bin")
        parser.add_option("-n","--numforks",dest="numforks",
            help="The number of scp sessions you want to run at once, defautl is 20",default=20)
        parser.add_option("-f", "--force", dest="noforce",
            action="store_false",
            help="use -f to force scripts to run (only works with prepare at the moment)", default=True)
        (options, args) = parser.parse_args()
        #check that we are in a directory called ftosupgrade
        dl = os.getcwd().split('/')
        self.options=options
        if dl[-1]=='ftosupgrade':
            if options.type=='upload' and options.binfile is not None and (options.devices is not None or options.region is not none): #upload bin files to multiple devices
                self.devlist=list()
                self.sqllist=list()
                if options.devices:
                    self.devlist=options.devices.split(',')
                    self.makeforks()
                else:
                    self.region=options.region
                    self.gethosts()
                    i=1
                    for hn in self.sqllist:
                        if i<=int(options.numforks):
                            self.devlist.append(hn)
                            i=i+1
                        else:
                            i=0
                            self.makeforks()
                            self.devlist=[hn]
                    self.makeforks()
            elif options.devices is not None and options.binfile is not None: # prepare and upgrade devices
                self.devlist=options.devices.split(",")
                for d in self.devlist:
                    self.m=message(hostname=d,options=options,binfilepath=BINFILEPATH)
                    if options.type=='prepare':
                        prepare(message=self.m)
                    elif options.type=='backout':
                        backout(message=self.m)
                    elif options.type=='upgrade':
                        prepare(message=self.m)
                        if len(self.m.errors[d]['critical'])<1:
                            u=upgrade(hostname=d,options=options,message=self.m)

                    self.m.writeerrors()
                    if len(self.m.errors[d]['critical'])>0:
                        self.m.warning('Critical Errors Found, exiting!\nPlease see %s/errors.log for details!' % d)
                        sys.exit()
            else:
                print("Please specify at least 1 device and a binary file name")
                parser.print_help()

        else:
            print("please create a directory called ftosupgrade:\nmkdir ftosupgrade\nchange to that directory\ncd ftosupgrade\nand re-run this command")


    def showerrors(self,errors,type):
        print("%s errors found..." % type)
        for e in errors:
            self.m.info(e)
        sys.exit()

    def makeforks(self):
        print(self.devlist)
        for hn in self.devlist:
            print("uploading %s to %s" % (self.options.binfile,hn))
            self.m=message(hostname=hn,options=self.options,binfilepath=BINFILEPATH,silent=True)
            pid=os.fork()
            if pid == 0:
                uploadbin(message=self.m,logfile=hn+'.log',multi=True)
            else:
                pids = (os.getpid(), pid)
        for i in range(len(self.devlist)):
            finished = os.waitpid(0, 0)
        print("all done")

    def gethosts(self):
        dbh=mysql()
        sql="""
        select trignodename
        from devices as d
        join sites as s on s.id=d.siteid
        where d.newreq='tor'
        and d.vendor='dell'
        and s.regionname='{region}'
        """.format(region=self.region)
        print sql
        dbh.buildretdict(sql)
        flist=list()
        i=0
        for o in dbh.retdict:
            self.sqllist.append(o['trignodename'])


if __name__ == '__main__':
    main()
