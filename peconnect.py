from __future__ import print_function, unicode_literals
import sys
import pexpect
import logging
import re
import time
from paramiko import SSHClient, MissingHostKeyPolicy
from scp import SCPClient
from os import path
from localauth import *
vrx=re.compile("FTOS-[\w]+-([\d]+\.[\d]+)\.([\d]+\.[\d]+)\.bin")
#user directory is path.expandser

class IgnoreKeys(MissingHostKeyPolicy):
    def missing_host_key(self, client, hostname, key):
        return

class pelogon:
    def __init__(self,**kw):
        self.user=tcrc.creds['joyent'].username
        self.binfile=None
        self.binfilepath=None
        if kw.has_key('binfile'):
            self.binfile=kw['binfile']
        if kw.has_key('binfilepath'):
            self.binfilepath=kw['binfilepath']

        self.logfile='pexpect.log'
        if kw.has_key('logfile'): self.logfile=kw['logfile']

        self.bfsw=None
        self.debug=None
        self.prompt="#"
        self.cprompt="#"
        self.errors=list()
        if kw.has_key('debug'): self.debug=kw['debug']
        self.ip=None
        if ':' in kw['ip']:
            ipp=kw['ip'].split(':')
            self.ip='%s -p 1000%s' % (ipp[0],ipp[1])
        else:
            self.ip=kw['ip']

        if kw.has_key('customer'):
            self.customer=kw['customer']
        else:
            self.customer='spc'

        self.port=None
        self.status=None
        self.message=None
        self.vendor=None
        self.wfsdata=''
        self.wfsll=None
        self.ogu='netops'
        self.ogp=og_dict[self.customer][self.ogu]
        if kw.has_key('debug'): self.debug=kw['debug']
        if kw.has_key('port'):
            self.port=kw['port']
            self.ogu=self.ogu+':'+str(self.port)

        self.versioninfo={}
        if kw.has_key('og'):
            self.ogconnect()
        else:
            self.connect()

    def ogconnect(self):
        sshcmd="ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no -o StrictHostKeyChecking=no -o GSSAPIAuthentication=no -o CheckHostIP=no  -o UserKnownHostsFile=/dev/null -l '"+self.ogu+"' "+self.ip;
        self.e=pexpect.spawn(sshcmd)
        self.e.expect('assword.*')
        self.info("DEBUG: sending password...")
        self.e.sendline(self.ogp)
        if self.port:
            self.e.expect(".")
            self.e.sendline()
        self.e.logfile = open(self.logfile, 'a')
        exp_list=[
            'assword.*',
            'Connect to port',
            '\$','Login.*',
            '[\w] login.*',
            'Username:',
            'login.*',
            '#',
            'Press RETURN to get started',
            pexpect.TIMEOUT,
            pexpect.EOF
        ]
        self.info("list size:"+str(len(exp_list)))
        resp=self.e.expect(exp_list,timeout=5)
        noresp=True
        while noresp:
            if resp<8: #if timeout try to send another line
                noresp=False
            else:
                print("trying again... if you want break this loop hit <cntrl> c")
                self.e.sendline("\r\n")
                print("newline sent expecting response...")
                resp=self.e.expect(exp_list,timeout=5)
                print("resp:"+str(resp))
        self.info("lresp:%s" % resp)
        self.info("login to opengear complete")
        result=None
        if resp==1:
            result=['fail','invalid port',None]
        elif resp==2:
            result=['success','none','opengear']
        elif resp==3:
            result=['success','login','dell']
        elif resp==4:
            result=['success','login','dell']
        elif resp==5:
            result=['success','login','dell']
        elif resp==6:
            result=['success','noenable','dell']
        elif resp==7:
            result=['success','skip','dell']
        elif resp==8:
            result=['fail','timeout to %s@%s' % (self.u,self.ip),None]
        else:
            result=['fail','unable to logon to %s@%s' % (self.u,self.ip),None]
        (self.status,self.message,self.vendor)=result

    def remlogon(self):
        """
        login to remote device after authenticating with opengear
        """
        prompt_dict={"juniper":"@[\w].*>","dell":"#","cisco":"#","arista":"#"}
        p=up_dict[self.user]
        self.e.logfile=None
        if(prompt_dict.has_key(self.vendor)):
            self.prompt=prompt_dict[self.vendor]
            #print prompt
            if self.message=='login':
                self.e.sendline(self.user)
                resp=self.e.expect(['assword','ogin','>','#'])
                #print "resp1:%s" % resp
                if resp==1:
                    self.e.sendline(self.user)
                    resp=self.e.expect(['assword','ogin'])
                #print "resp2:%s" % resp
                #time.sleep(1)
                self.e.sendline(p)
                self.e.logfile=open(self.logfile,'a')
                resp=self.e.expect([self.prompt,'[\w]>','Last login','Login succ','Authentication failed','ogin incorrect','pam_open_session: session failure',pexpect.TIMEOUT,pexpect.EOF])
                if resp>4:
                    self.status='fail'
                    self.message='invalid response: '+self.e.before
                elif resp>2:
                    self.status='fail'
                    self.message='login failure'
                elif resp>0 and resp<4:
                    self.e.sendline()
                    resp=self.e.expect([self.prompt,'>'])
                    if resp==1 and self.vendor=='dell':
                        self.status='noenable'
                        self.message='need to jump to enable mode'
                        self.remlogon()
            elif self.message=='editmode':
                e.sendline('exit')
                e.expect(self.prompt)
            elif self.status=='noenable':
                #print("sending enable...")
                self.e.sendline('en')
                enresp=self.e.expect([self.prompt,'assword','top-level commands are available','Session expired or cancelled'])
                if enresp==1:
                    self.e.sendline(enp)
                    enpwresp=self.e.expect([self.prompt,'Last login','Login succ','assword','failure','pam_open_session: session failure',pexpect.TIMEOUT,pexpect.EOF])
                    if enpwresp>4:
                        self.status='fail'
                        self.message='invalid response: '+self.e.before
                    elif enpwresp>2:
                        self.status='fail'
                        self.message='login failure'
                elif enresp>1:
                    self.status='fail'
                    self.message='login failure'
            self.e.sendline()
            tresp=self.e.expect([self.prompt,'Error','error','Invalid','not found'])
            if tresp>0:
                self.status='fail'
                self.message=tresp
            else:
                self.status='success'
                self.message='all logged in!'
        else:
            self.status='fail'
            self.message='vendor not found'

    def waitforstream(self):
        """
        take pexpect session and wait for stream to stop, resetting timeout as needed
        """
        stopchecking=False
        data=''
        while not stopchecking:
            try:
                # default timeout for pexpect-spawn object is 30s
                data=self.e.read_nonblocking(1024, timeout=5)
                self.wfsdata=self.wfsdata+data
                time.sleep(1)
            # continue reading data from 'session' until the thread is stopped
            except pexpect.TIMEOUT:
                ls=data.split("\n")
                self.wfsll=ls[-1]
                stopchecking=True
            except Exception as exception:
                print(exception)
                break


    def connect(self):
        self.sshcmd="ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no -o StrictHostKeyChecking=no -o GSSAPIAuthentication=no -o CheckHostIP=no  -o UserKnownHostsFile=/dev/null -l '"+self.user+"' "+self.ip;
        self.e=pexpect.spawn(self.sshcmd)
        #e.delaybeforesend = 1
        #e.timeout = 15
        self.e.expect('assword.*')
        self.info("DEBUG: sending password...")
        self.e.sendline(up_dict[self.user])
        resp=self.e.expect(['assword.*','.*\$',pexpect.TIMEOUT,pexpect.EOF,'.*#'])
        self.e.logfile = open(self.logfile, 'a')
        if resp==0:
            raise("ERROR: invalid login and password")
        elif resp==1:
            raise("ERROR: not in enable mode!")
        elif resp==2:
            raise("ERROR: connection timed out")
        elif resp==3:
            raise("ERROR: invalid response")
        else:
            shver=self.e.sendline('show version | no-more')
            self.e.expect(self.prompt)
            svl=self.e.before.split("\r\n")
            self.cprompt=svl[-1]+'\(conf\)#'
            self.prompt=ll=svl[-1]+str('#')
            self.info('ll:'+ll)
            for l in svl:
                if ':' in l:
                    (k,v)=l.split(':',1)
                    self.versioninfo[k.rstrip().lstrip()]=v.lstrip().lower()

    def info(self,msg):
        if self.debug:
            logging.debug(str(msg))

    def getbootinfo(self):
        sbs=self.getCommand('show boot system stack-unit 1').split("\n")
        cols=sbs[-2].split()
        bootinfo={}
        aslot={'slot':'A','version':cols[-2]}
        bslot={'slot':'B','version':cols[-1]}
        for slot in [aslot,bslot]:
            if '[boot]' in slot['version']:
                v=slot['version'].replace('[boot]','')
                slot['version']=v
                bootinfo['primary']=slot
            else:
                bootinfo['secondary']=slot
        return bootinfo

    def restoreBoot(self,primary,secondary):
        self.addConfig([
            'boot system stack-unit 1 primary system: %s:' % primary,
            'boot system stack-unit 1 secondary system: %s:' % secondary
        ])

    def getfilelist(self):
        files={}
        dirres=self.getCommand('dir | no-more').split("\n")
        for l in dirres:
            cols=l.split()
            if len(cols)>3:
                files[cols[-1]]={'size':cols[2]}
        return files

    def exit(self):
        self.e.sendline('exit')
        self.e.expect(pexpect.EOF)
        self.e.terminate()
        #self.nm.disconnect()

    def addConfig(self,cmdlist):
        self.e.sendline('conf t')
        self.e.expect(self.cprompt)
        for cmd in cmdlist:
            self.e.sendline(cmd)
            self.e.expect(self.cprompt)
        self.e.sendline('end')
        self.e.expect(self.prompt)
        self.e.sendline('wr')
        self.e.expect(self.prompt)

    def getCommand(self,cmd):
        self.e.sendline(cmd)
        self.e.expect(self.prompt)
        output=self.e.before
        return output




    def progress(self,filename, size, sent):
        logging.debug("%s\'s progress: %.2f%%   \r" % (filename, float(sent)/float(size)*100) )

    def scpfile(self):
        self.info("Trying to upload file: %s%s" % (self.binfilepath,self.binfile))
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
