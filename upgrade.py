#!/opt/local/scripts/python/ftosupgrade/bin/python2.7
import os
import sys          # for handling arguments
import re            # for regular expressions
import time            # for sleep and time related functions
from optparse import OptionParser
from termcolor import colored
from terminaltables import AsciiTable
from prepare import *


def main():
    parser = OptionParser("usage: ftupgrade <options>")
    parser.add_option("-d", "--devices", dest="devices",
        help="List of devices to upgrade separated by a ','", default=None)
    parser.add_option("-t", "--type",dest="type",
        help="This can be prepare,upgrade", default='prepare')
    parser.add_option("-b","--binfile",dest="binfile",
        help="The name of the binary file you are using for the upgrade e.g. FTOS-SK-9.13.0.2.bin")
    parser.add_option("-f", "--force", dest="noforce",
        action="store_false",
        help="use -f to force scripts to run", default=True)
    (options, args) = parser.parse_args()

    if options.devices is not None and options.binfile is not None:
        dl = os.getcwd().split('/')
        if dl[-1]=='ftosupgrade':
            dl=options.devices.split(",")
            if options.type=='prepare':
                for d in dl:
                    p=prepare(hostname=d,options=options)
        else:
            print("please create a directory called ftosupgrade:\nmkdir ftosupgrade\nchange to that directory\ncd ftosupgrade\nand re-run this command")
    else:
        print("Please specify at least 1 device and a binary file name")
        parser.print_help()


if __name__ == '__main__':
    main()
