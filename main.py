#!/opt/local/scripts/python/ftosupgrade/bin/python2.7
import os
import sys          # for handling arguments
import re            # for regular expressions
import time            # for sleep and time related functions
from optparse import OptionParser
from messages import *
from prepare import *
from upgrade import *
from backout import *
from upload import *
VERSION='.05BETA'
BINFILEPATH='/tftpboot/Dell/'

class main():
    def __init__(self):
        parser = OptionParser("usage: ftosupgrade <options>")
        parser.add_option("-d", "--devices", dest="devices",
            help="List of devices to upgrade separated by a ','", default=None)
        parser.add_option("-t", "--type",dest="type",
            help="This can be prepare,upgrade, or backout", default='prepare')
        parser.add_option("-b","--binfile",dest="binfile",
            help="The name of the binary file you are using for the upgrade e.g. FTOS-SK-9.14.1.0.bin")
        parser.add_option("-f", "--force", dest="noforce",
            action="store_false",
            help="use -f to force scripts to run (only works with prepare at the moment)", default=True)
        (options, args) = parser.parse_args()
        self.m=message(options=options,binfilepath=BINFILEPATH)
        if options.devices is not None and options.binfile is not None:
            dl = os.getcwd().split('/')
            if dl[-1]=='ftosupgrade':
                dl=options.devices.split(",")
                for d in dl:
                    self.m.setlogging(d)
                    if options.type=='prepare':
                        prepare(message=self.m)
                    elif options.type=='backout':
                        backout(message=self.m)
                    elif options.type=='upgrade':
                        prepare(message=self.m)
                        if len(self.m.errors[d]['critical'])>0:
                            self.showerrors(self.m.errors[d]['critical'],'prepare')
                        else:
                            u=upgrade(hostname=d,options=options,message=self.m)
                            if len(self.m.errors[d]['critical'])>0:
                                self.showerrors(self.m.errors[d]['critical'],'upgrade')
            else:
                self.m.info("please create a directory called ftosupgrade:\nmkdir ftosupgrade\nchange to that directory\ncd ftosupgrade\nand re-run this command")
        else:
            self.m.info("Please specify at least 1 device and a binary file name")
            parser.print_help()

    def showerrors(self,errors,type):
        print("%s errors found..." % type)
        for e in errors:
            self.m.info(e)
        sys.exit()


if __name__ == '__main__':
    main()
