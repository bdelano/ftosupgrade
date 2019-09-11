from __future__ import print_function, unicode_literals
import sys
import pexpect
import re
import time
from utilities import utils
from localauth import og_dict, up_dict, tcrc

class pelogon(utils):
    def __init__(self,**kw):
        utils.__init__(self,**kw)
        self.user=tcrc.creds['joyent'].username
        self.logfile='pecommands.log'
        if self.peclog: self.logfile=self.peclog
        self.prompt="#"
        self.cprompt="#"
        self.bootinfo={}
        self.ip=None
        if kw.has_key('ip'):
            if ':' in kw['ip']:
                ipp=kw['ip'].split(':')
                self.ip='%s -p 1000%s' % (ipp[0],ipp[1])
            else:
                self.ip=kw['ip']
        else:
            self.ip=self.hostname

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
        if kw.has_key('port'):
            self.port=kw['port']
            self.ogu=self.ogu+':'+str(self.port)
        self.versioninfo={}
        if kw.has_key('scponly'):
            self.scp()
        elif kw.has_key('og'):
            self.ogconnect()
        else:
            self.connect()

    def ogconnect(self):
        sshcmd="ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no -o StrictHostKeyChecking=no -o GSSAPIAuthentication=no -o CheckHostIP=no  -o UserKnownHostsFile=/dev/null -l '"+self.ogu+"' "+self.ip;
        self.debug(sshcmd)
        self.e=pexpect.spawn(sshcmd)
        self.e.expect('assword.*')
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
        resp=self.e.expect(exp_list,timeout=5)
        noresp=True
        while noresp:
            if resp<8: #if timeout try to send another line
                noresp=False
            else:
                self.warning("trying again... if you want break this loop hit <cntrl> c")
                self.e.sendline("\r\n")
                self.warning("newline sent expecting response...")
                resp=self.e.expect(exp_list,timeout=5)
                self.debug("resp:"+str(resp))
        self.debug("login to opengear complete")
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
            self.critical('unable to logon to %s@%s' % (self.u,self.ip))
        (self.status,self.message,self.vendor)=result
        self.debug('oglogon status:%s message:%s' % (self.status,self.message))

    def remlogon(self):
        """
        login to remote device after authenticating with opengear
        """
        prompt_dict={"juniper":"@[\w].*>","dell":"#","cisco":"#","arista":"#"}
        p=up_dict[self.user]
        self.e.logfile=open(self.logfile,'a')
        if(prompt_dict.has_key(self.vendor)):
            self.prompt=prompt_dict[self.vendor]
            if self.message=='login':
                self.e.logfile=None
                self.e.sendline(self.user)
                resp=self.e.expect(['assword','ogin','>','#'])
                if resp==1:
                    self.e.sendline(self.user)
                    resp=self.e.expect(['assword','ogin'])
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
                enresp=self.e.expect([self.prompt,'assword','top-level commands are available','Session expired or cancelled',pexpect.TIMEOUT])
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
                    self.message='login failure: '+self.e.before
            self.e.sendline()
            tresp=self.e.expect([self.prompt,'Error','error','Invalid','not found',pexpect.TIMEOUT])
            if tresp>0:
                self.status='fail'
                self.message=self.e.before
            else:
                self.status='success'
                self.message='all logged in!'
        else:
            self.status='fail'
            self.message='vendor not found'
        self.debug('remlogon status:%s message:%s' % (self.status,self.message))
        if self.status=='fail':
            self.critical(self.message)

    def waitforstream(self):
        """
        take pexpect session and wait for stream to stop, resetting timeout as needed
        """
        stopchecking=False
        data=''
        while not stopchecking:
            try:
                # default timeout for pexpect-spawn object is 30s
                data=self.e.read_nonblocking(1024, timeout=30)
                self.wfsdata=self.wfsdata+data
                self.debug("wfsdata\nSTART:%s:END" % data)
                time.sleep(1)
            # continue reading data from 'session' until the thread is stopped
            except pexpect.TIMEOUT:
                self.status='success'
                ls=data.rstrip().split("\n")
                self.wfsll=ls[-1]
                stopchecking=True
            except Exception as exception:
                self.status='fail'
                self.msg=exception
                break


    def connect(self):
        sshcmd="ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no -o StrictHostKeyChecking=no -o GSSAPIAuthentication=no -o CheckHostIP=no  -o UserKnownHostsFile=/dev/null -l '"+self.user+"' "+self.ip;
        self.e=pexpect.spawn(sshcmd)
        self.debug(sshcmd)
        #e.delaybeforesend = 1
        #e.timeout = 15
        self.e.expect('assword.*')
        self.e.sendline(up_dict[self.user])
        resp=self.e.expect(['assword.*','.*\$',pexpect.TIMEOUT,pexpect.EOF,'.*#'])
        self.e.logfile = open(self.logfile, 'a')
        if resp==0:
            self.critical("ERROR: %s invalid login and password" % self.hostname)
        elif resp==1:
            self.critical("ERROR: %s not in enable mode!" % self.hostname)
        elif resp==2:
            self.critical("ERROR: %s connection timed out" % self.hostname)
        elif resp==3:
            self.critical("ERROR: %s invalid response %s" % self.hostname,self.e.before)
        else:
            self.getbootinfo()

    def getbaseinfo(self):
        shver=self.getCommand('show version | no-more')
        svl=shver.split("\r\n")
        self.cprompt=svl[-1]+'\(conf\)#'
        self.prompt=ll=svl[-1]+str('#')
        for l in svl:
            if ':' in l:
                (k,v)=l.split(':',1)
                self.versioninfo[k.rstrip().lstrip()]=v.lstrip().lower()

    def getbootinfo(self):
        """
        grabs the boot information from the switch and sets the
        prompts
        """
        sbs=self.getCommand('show boot system stack-unit 1')
        sbsl=list()
        if 'FLASH BOOT' in sbs:
            sbsl=sbs.split("\r\n")
        else:
            self.warning('show boot system stack-unit 1 failed, waiting 5 and trying again...')
            time.sleep(5)
            sbs=self.getCommand('show boot system stack-unit 1')
            sbsl=sbs.split("\r\n")

        self.cprompt=sbsl[-1]+'\(conf\)#'
        self.prompt=ll=sbsl[-1]+str('#')
        cols=sbsl[-2].split()
        aslot={'slot':'A','version':cols[-2]}
        bslot={'slot':'B','version':cols[-1]}
        for slot in [aslot,bslot]:
            if '[boot]' in slot['version']:
                v=slot['version'].replace('[boot]','')
                slot['version']=v
                self.bootinfo['primary']=slot
            else:
                self.bootinfo['secondary']=slot

    def setBoot(self,primary,secondary):
        """
        sets the boot parameters
        """
        self.addConfig([
            'boot system stack-unit 1 primary system: %s:' % primary,
            'boot system stack-unit 1 secondary system: %s:' % secondary
        ])

    def getfilelist(self):
        """
        pulls files using the 'dir' command and pushes them into a dictionary
        """
        files={}
        dirres=self.getCommand('dir | no-more').split("\n")
        for l in dirres:
            cols=l.split()
            if len(cols)>3:
                files[cols[-1]]={'size':cols[2]}
        return files

    def exit(self):
        """
        exits the device and terminates the ssh connection
        """
        self.e.sendline('exit')
        self.e.expect(pexpect.EOF)
        self.e.terminate()
        #self.nm.disconnect()

    def upgradesysflash(self,altslot):
        self.e.logfile = sys.stdout
        self.e.sendline('upgrade sys flash: %s:' % altslot)
        self.e.expect("Source file name \[\]:")
        self.e.sendline(self.binfile)
        self.e.expect(self.prompt,timeout=None)
        self.getbootinfo()
        self.e.logfile=open(self.peclog, 'a')

    def addConfig(self,cmdlist):
        """
        takes a list of commands and adds them to the configuration then saves the configuration
        """
        self.e.sendline('conf t')
        self.e.expect(self.cprompt)
        error=None
        for cmd in cmdlist:
            self.e.sendline(cmd)
            self.e.expect(self.cprompt)
            if '% Error:' in self.e.before:
                error=True
                self.warning('Config Error command:%s\n%s%s' % (cmd,self.cprompt,self.e.before))
        self.e.sendline('end')
        self.e.expect(self.prompt)
        if error:
            self.warning('found error with configuration, skipping config save!')
        else:
            self.e.sendline('wr')
            self.e.expect(self.prompt)

    def getCommand(self,cmd):
        """
        takes a command and returns the output
        """
        self.debug('sending command:'+cmd)
        self.e.sendline(cmd)
        self.e.expect(self.prompt)
        self.debug('command complete!')
        output=self.e.before
        if '% Error:' in output:
            self.warning('Command Error command:%s\n%s%s' % (cmd,self.prompt,output))
        return output

    def runchecks(self,type):
        """
        runs a list of commands and adds them to either a pre or post directory
        certain command output will get analyzed for errors
        """
        self.info('---running %s commands' % type)
        su=1;
        if re.match("^8.*",self.bootinfo['primary']['version']):
            su=0
        commands=[
            {'cmd':'show alarm |no-more','fn':'shalarm'},
            {'cmd':'show vlt br |no-more','fn':'shvlt'},
            {'cmd':'show int desc |no-more','fn':'shintdescr'},
            {'cmd':'show run |no-more','fn':'shrun'},
            {'cmd':'show logging |no-more','fn':'shlogging'},
            {'cmd':'show hardware stack-unit %s unit 0 execute-shell-cmd "ps" |no-more' % su,'fn':'shhwstack'},
            {'cmd':'show lldp nei |no-more','fn':'shlldp'},
            {'cmd':'show vlt detail |no-more','fn':'shvltdet'}
        ]
        for o in commands:
            f=open(self.devpath+type+'/'+o['fn']+'.cmd','w')
            self.info('----running command: %s...' % o['cmd'])
            cmdres=self.getCommand(o['cmd'])
            f.write(cmdres)
            f.close()
            if o['fn']=='shvlt':
                self.checkvlt(cmdres)
            elif o['fn']=='shalarm':
                self.checkalarms(cmdres)
            elif o['fn']=='shhwstack':
                self.checkhwstack(cmdres)

    def checkhwstack(self,cmdres):
        """
        checks the shhwstack command for an STP bug
        """
        for l in cmdres.split("\r\n"):
            cols=l.lstrip().split()
            if len(cols)>7:
                (port,link,state)=(cols[0]+cols[1],cols[2].lower(),cols[7].lower())
                self.debug("p:%s l:%s s:%s" % (port,link,state))
                if state=='block' and state=='up':
                    self.critical('stperror: %s %s %s' % (port,link,state))

    def checkalarms(self,cmdres):
        """
        checks the shalarm command to see if any exist
        """
        if 'No minor alarms' not in cmdres:
            self.critical('Minor alarms found please see: shalarm.cmd')
        if  'No major alarms' not in cmdres:
            self.critical('Major alarms found please see: shalarm.cmd')

    def checkvlt(self,cmdres):
        """
        checks VLT to see if anything is in a not 'Up' state
        """
        resdict={}
        for l in cmdres.split("\r\n"):
            if ':' in l:
                (k,v)=l.split(':',1)
                resdict[k.rstrip().lstrip()]=v.lstrip().lower()
        keys=['ICL Link Status','HeartBeat Status','VLT Peer Status']
        for chk in keys:
            if resdict[chk] != 'up':
                self.critical('vlterror:%s is not up (%s)' % (chk,resdict[chk]))


    def scp(self):
        """
        uses scp to push a file up to a device
        """
        quiet=''
        if self.silent: quiet=' -q'
        sshcmd="scp{quiet} -o PreferredAuthentications=password -o PubkeyAuthentication=no -o StrictHostKeyChecking=no -o GSSAPIAuthentication=no -o CheckHostIP=no  -o UserKnownHostsFile=/dev/null {binfilepath} {user}@{ip}:{binfile}".format(quiet=quiet,binfilepath=self.binfilepath+self.binfile,user=self.user,ip=self.ip,binfile=self.binfile)
        self.debug(sshcmd)
        self.info("starting upload of %s" % self.binfilepath+self.binfile)
        e=pexpect.spawn(sshcmd)
        e.logfile = None
        e.expect('assword.*')
        e.sendline(up_dict[self.user])
        if not self.silent: e.logfile = sys.stdout
        e.expect(pexpect.EOF,timeout=None)
        if 'scp:' in e.before:
            self.critical('unable to upload file to %s: %s' % (self.ip,e.before))
        else:
            self.info("upload complete!")
