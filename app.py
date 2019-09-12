#!/opt/local/scripts/python/ftosupgrade/bin/python2.7
import os
import sys          # for handling arguments
import re            # for regular expressions
import time            # for sleep and time related functions
import logging
from optparse import OptionParser
from prepare import prepare
from upgrade import upgrade
from backout import backout
from upload import uploadbin
from utilities import utils
VERSION='1.7BETA'
BINFILEPATH='/tftpboot/Dell/'

class main():
    def __init__(self):
        """
        Takes command line variables and does 1 of the following: uploads,prepares,upgrades,backout
        """
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
            help="The number of scp sessions you want to run at once, default is 20 (only for uploads!)",default=20)
        parser.add_option("-f", "--force", dest="noforce",
            action="store_false",
            help="use -f to force scripts to run (only works with prepare at the moment)", default=True)
        parser.add_option("--test", dest="notest",
            action="store_false",
            help="use --test to run the upgrade command without reloading the switch", default=True)
        parser.add_option("-p","--binfilepath",dest="binfilepath",
            default=BINFILEPATH,
            help="The path where all your binary files are stored")
        (options, args) = parser.parse_args()
        dl = os.getcwd().split('/')
        self.options=options
        if options.type=='upload' and options.binfile is not None and (options.devices is not None or options.region is not None):
            #upload bin files to multiple devices
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
        elif options.devices is not None and options.binfile is not None:
            # prepare and upgrade devices
            self.devlist=options.devices.split(",")
            for d in self.devlist:
                m=utils(hostname=d,options=options)
                m.setupworkspace()
                if options.type=='prepare':
                    prepare(hostname=d,options=options)
                elif options.type=='backout':
                    backout(hostname=d,options=options)
                elif options.type=='upgrade':
                    p=prepare(hostname=d,options=options)
                    if len(p.errors[d]['critical'])<1:
                        u=upgrade(hostname=d,options=options)
                        if len(u.errors[d]['critical'])>0:
                            m.warning('Found Errors with upgrade...exiting!')
                            sys.exit()
                    else:
                        m.warning('Found Errors with prepare... exiting!')
                        sys.exit()


                #self.m.writeerrors()
                #if len(self.m.errors[d]['critical'])>0:
                #    self.m.warning('Critical Errors Found, exiting!\nPlease see %s/errors.log for details!' % d)
                #    sys.exit()
        else:
            print("Please specify at least 1 device and a binary file name")
            parser.print_help()


    def makeforks(self):
        """
        takes a list of devices and forks a separate process for uploading a file
        """
        #print(self.devlist)
        for d in self.devlist:
            m=utils(hostname=d,options=self.options,silent=True)
            m.setupworkspace()
            print("uploading %s to %s" % (self.options.binfile,d))
            pid=os.fork()
            if pid == 0:
                uploadbin(hostname=d,options=self.options,multi=True)
            else:
                pids = (os.getpid(), pid)
        for i in range(len(self.devlist)):
            finished = os.waitpid(0, 0)
        print("all done")

    def gethosts(self):
        """
        pulls dell tor devices down from database using region
        """
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
