import sys          # for handling arguments
import pexpect      # for expect script
import re            # for regular expressions
import time            # for sleep and time related functions
from localauth import *

class oglogon:
    def __init__(self,**kw):
        """
        logs onto the opengear shell or directly to a port
        required options: ip
        """
        ogu='netops'
        self.ip=None
        if ':' in kw['ip']:
            ipp=kw['ip'].split(':')
            self.ip='%s -p 1000%s' % (ipp[0],ipp[1])
        else:
            self.ip=kw['ip']
        if kw.has_key('user'):
            self.user=kw['user']
        else:
            self.user=tcrc.creds['joyent'].username

        if kw.has_key('customer'):
            self.customer=kw['customer']
        else:
            self.customer='spc'
        if kw.has_key('logfile'):
            self.logfile=kw['logfile']
        else:
            self.logfile=sys.stdout
        auth_dict=og_dict[self.customer]
        self.ogp=auth_dict[ogu]
        self.debug=None
        self.port=None
        self.status=None
        self.message=None
        self.vendor=None
        self.wfsdata=''
        self.wfsll=None
        if kw.has_key('debug'): self.debug=kw['debug']
        if kw.has_key('port'):
            self.port=kw['port']
            ogu=ogu+':'+str(self.port)
        self.sshcmd="ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no -o StrictHostKeyChecking=no -o GSSAPIAuthentication=no -o CheckHostIP=no  -o UserKnownHostsFile=/dev/null -l '"+ogu+"' "+self.ip;
        self.info(self.sshcmd)
        self.logon()

    def info(self,msg):
        if self.debug:
            print str(msg)

    def logon(self):
        self.e=pexpect.spawn(self.sshcmd)
        #e.delaybeforesend = 1

        #e.timeout = 15
        self.e.expect('assword.*')
        self.info("DEBUG: sending password...")
        self.e.sendline(self.ogp)
        if self.port:
            self.e.expect(".")
            self.e.sendline()
        self.e.logfile = open(self.logfile, 'a')
        exp_list=['assword.*','Connect to port','\$','Login.*','[\w] login.*','Username:','login.*','Big Monitoring Fabric','barracuda.com','Peakflow',':\/#','IPv4 address','\@[\w-]+>','\@[\w-]+#',':>','>','#','Press RETURN to get started',pexpect.TIMEOUT,pexpect.EOF]
        self.info("list size:"+str(len(exp_list)))
        resp=self.e.expect(exp_list,timeout=5)
        noresp=True
        while noresp:
            if resp<17: #if timeout try to send another line
                noresp=False
            else:
                print "trying again... if you want break this loop hit <cntrl> c"
                self.e.sendline("\r\n")
                print "newline sent expecting response..."
                resp=e.expect(exp_list,timeout=5)
                print "resp:"+str(resp)
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
            result=['success','login','juniper']
        elif resp==7:
            result=['success','skip','BMF']
        elif resp==8:
            result=['success','skip','barracuda']
        elif resp==9:
            result=['success','skip','arbor']
        elif resp==10:
            result=['success','skip','arbor']
        elif resp==11:
            result=['success','skip','unknown']
        elif resp==12:
            result=['success','skip','juniper']
        elif resp==13:
            result=['success','editmode','juniper']
        elif resp==14:
            result=['success','skip','HSM']
        elif resp==15:
            result=['success','noenable','dell']
        elif resp==16:
            result=['success','skip','dell']
        elif resp==17:
            result=['fail','timeout to %s@%s' % (self.u,self.ip),None]
        else:
            result=['fail','unable to logon to %s@%s' % (self.u,self.ip),None]
        (self.status,self.message,self.vendor)=result

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
                print("timeout reached")
                ls=data.split("\n")
                self.wfsll=ls[-1]
                stopchecking=True
            except Exception as exception:
                print(exception)
                break

    def remlogon(self):
        """
        login to remote device after authenticating with opengear
        """
        prompt_dict={"juniper":"@[\w].*>","dell":"#","cisco":"#","arista":"#"}
        p=up_dict[self.user]
        if(prompt_dict.has_key(self.vendor)):
            prompt=prompt_dict[self.vendor]
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
                resp=self.e.expect([prompt,'[\w]>','Last login','Login succ','Authentication failed','ogin incorrect','pam_open_session: session failure',pexpect.TIMEOUT,pexpect.EOF])
                if resp>4:
                    self.status='fail'
                    self.message='invalid response: '+self.e.before
                elif resp>2:
                    self.status='fail'
                    self.message='login failure'
                elif resp>0 and resp<4:
                    self.e.sendline()
                    resp=self.e.expect([prompt,'>'])
                    if resp==1 and self.vendor=='dell':
                        self.status='noenable'
                        self.message='need to jump to enable mode'
                        self.remlogon()
            elif self.message=='editmode':
                e.sendline('exit')
                e.expect(prompt)
            elif self.status=='noenable':
                print "sending enable..."
                self.e.sendline('en')
                enresp=self.e.expect([prompt,'assword','top-level commands are available','Session expired or cancelled'])
                if enresp==1:
                    self.e.sendline(enp)
                    enpwresp=self.e.expect([prompt,'Last login','Login succ','assword','failure','pam_open_session: session failure',pexpect.TIMEOUT,pexpect.EOF])
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
            tresp=self.e.expect([prompt,'Error','error','Invalid','not found'])
            if tresp>0:
                self.status='fail'
                self.message=tresp
            else:
                self.status='success'
                self.message='all logged in!'
        else:
            self.status='fail'
            self.message='vendor not found'
