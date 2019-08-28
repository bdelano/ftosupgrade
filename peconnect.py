from __future__ import print_function, unicode_literals
import sys
import pexpect
import logging
from paramiko import SSHClient, MissingHostKeyPolicy
from scp import SCPClient
from os import path
from localauth import *
BINFILEPATH='/tftpboot/Dell/'
#user directory is path.expandser

class IgnoreKeys(MissingHostKeyPolicy):
    def missing_host_key(self, client, hostname, key):
        return

class peconnect:
    def __init__(self,**kw):
        self.user=tcrc.creds['joyent'].username
        self.binfile=None
        self.debug=None
        self.prompt="#"
        if kw.has_key('debug'): self.debug=kw['debug']
        self.ip=kw['ip']
        self.devinfo={}
        self.connect()
        if kw.has_key('binfile'):
            self.binfile=kw['binfile']
            self.checkbinfile()

    def checkbinfile(self):
        self.getfilelist()
        if self.binfile:
            if path.exists('%s%s' % (BINFILEPATH,self.binfile)):
                if self.devinfo['files'].has_key(self.binfile):
                    binres=self.getCommand('verify md5 flash://%s %s' % (self.binfile,binmd5[self.binfile]))
                    if 'FAILED' in binres:
                        self.devinfo['binfilestatus']={'error':binres}
                    else:
                        self.devinfo['binfilestatus']={'succcess':'binfile (%s) exists' % self.binfile}
                else:
                    self.devinfo['binfilestatus']={'error':'binfile (%s) does not exist' % self.binfile}
            else:
                self.devinfo['binfilestatus']={'error':'cannot find local file %s%s' % (BINFILEPATH,self.binfile)}


    def connect(self):
        self.sshcmd="ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no -o StrictHostKeyChecking=no -o GSSAPIAuthentication=no -o CheckHostIP=no  -o UserKnownHostsFile=/dev/null -l '"+self.user+"' "+self.ip;
        self.e=pexpect.spawn(self.sshcmd)
        #e.delaybeforesend = 1

        #e.timeout = 15
        self.e.expect('assword.*')
        self.info("DEBUG: sending password...")
        self.e.sendline(up_dict[self.user])
        resp=self.e.expect(['assword.*','.*\$',pexpect.TIMEOUT,pexpect.EOF,'.*#'])
        if self.debug: self.e.logfile = open(self.ip+'.log', 'w')
        if resp==0:
            raise("ERROR: invalid login and password")
        elif resp==1:
            raise("ERROR: not in enable mode!")
        elif resp==2:
            raise("ERROR: connection timed out")
        elif resp==3:
            raise("ERROR: invalid response")
        else:
            shver=self.getCommand('show version | no-more')
            svl=shver.split("\r\n")
            self.prompt=ll=svl[-1]+str('#')
            self.info('ll:'+ll)
            for l in svl:
                if ':' in l:
                    (k,v)=l.split(':',1)
                    self.devinfo[k]=v

    def info(self,msg):
        if self.debug:
            logging.debug(str(msg))

    def getfilelist(self):
        self.devinfo['files']={}
        dirres=self.getCommand('dir | no-more').split("\n")
        for l in dirres:
            cols=l.split()
            if len(cols)>3:
                self.devinfo['files'][cols[-1]]={'size':cols[2]}


    def exit(self):
        self.info('Exiting Device')
        self.e.sendline('exit')
        self.e.expect(pexpect.EOF)
        #self.nm.disconnect()

    def getCommand(self,cmd):
        self.e.sendline(cmd)
        self.info('waiting on:'+str(self.prompt))
        self.e.expect(self.prompt)
        output=self.e.before
        return output

    def progress(self,filename, size, sent):
        logging.debug("%s\'s progress: %.2f%%   \r" % (filename, float(sent)/float(size)*100) )

    def scpfile(self):
        self.info("Trying to upload file: %s%s" % (BINFILEPATH,self.binfile))
        try:
            ssh=SSHClient()
            ssh.set_missing_host_key_policy(IgnoreKeys())
            ssh.connect(hostname=self.ip,username=self.user,password=up_dict[self.user],look_for_keys=False)
            self.info('connected via scp...')
            #scp=SCPClient(ssh.get_transport(), progress=self.progress)
            scp=SCPClient(ssh.get_transport())
            self.info('attempting upload %s..' % self.binfile)
            scp.put(BINFILEPATH+self.binfile,self.binfile)
            self.info('upload complete!')
            scp.close()
        except:
            self.devinfo['binfilestatus']={'uploaderror':'unable to scp file up!'}
