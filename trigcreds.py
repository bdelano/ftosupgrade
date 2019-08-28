import pwd
import os
from os.path import expanduser
from collections import namedtuple
from base64 import decodestring, encodestring
from cryptography.hazmat.backends.openssl import backend as openssl_backend
from cryptography.hazmat.primitives import ciphers
Credentials = namedtuple('Credentials', 'username password realm')

def _perl_unhex_old(c):
    """
    Emulate Crypt::TripleDES's bizarre handling of keys, which relies on
    the fact that you can pass Perl's pack('H*') a string that contains
    anything, not just hex digits.  "The result for bytes "g".."z" and
    "G".."Z" is not well-defined", says perlfunc(1).  Smash!

    This function can be safely removed once GPG is fully supported.
    """
    if 'a' <= c <= 'z':
        return (ord(c) - ord('a') + 10) & 0xf
    if 'A' <= c <= 'Z':
        return (ord(c) - ord('A') + 10) & 0xf
    return ord(c) & 0xf

def _perl_pack_Hstar_old(s):
    """
    Used with _perl_unhex_old(). Ghetto hack.

    This function can be safely removed once GPG is fully supported.
    """
    r = ''
    while len(s) > 1:
        r += chr((_perl_unhex_old(s[0]) << 4) | _perl_unhex_old(s[1]))
        s = s[2:]
    if len(s) == 1:
        r += _perl_unhex_old(s[0])
    return r

class getcreds():
    def __init__(self):
        self.file_name=expanduser("~")+str('/.tacacsrc')
        self.userinfo = pwd.getpwuid(os.getuid())
        self.username = self.userinfo.pw_name
        self.user_home = self.userinfo.pw_dir
        self.key = self._get_key_old('/etc/trigger/.tackf')
        self.rawdata = self._read_file_old()
        self.creds = self._parse_old()


    def _decrypt_old(self, s):
            """Decodes using the old method. Strips newline for you."""
            des = ciphers.algorithms.TripleDES(self.key)
            cipher = ciphers.Cipher(des, ciphers.modes.ECB(), backend=openssl_backend)
            decryptor = cipher.decryptor()
            # rstrip() to undo space-padding; unfortunately this means that
            # passwords cannot end in spaces.
            return decryptor.update(decodestring(s)).rstrip(' ') + decryptor.finalize()

    def _read_file_old(self):
        """Read old style file and return the raw data."""
        with open(self.file_name, 'r') as f:
            return f.readlines()

    def _get_key_nonce_old(self):
        """Yes, the key nonce is the userid.  Awesome, right?"""
        return pwd.getpwuid(os.getuid())[0] + '\n'

    def _get_key_old(self, keyfile):
        '''Of course, encrypting something in the filesystem using a key
        in the filesystem really doesn't buy much.  This is best referred
        to as obfuscation of the .tacacsrc.'''
        try:
            with open(keyfile, 'r') as kf:
                key = kf.readline().strip()
        except IOError as err:
            msg = 'Keyfile at %s not found. Please create it.' % keyfile
            raise CouldNotParse(msg)

        if not key:
            msg = 'Keyfile at %s must contain a passphrase.' % keyfile
            raise CouldNotParse(msg)

        key += self._get_key_nonce_old()
        key = _perl_pack_Hstar_old((key + (' ' * 48))[:48])
        assert(len(key) == 24)
        return key

    def _parse_old(self):
            """Parses .tacacsrc and returns dictionary of credentials."""
            data = {}
            creds = {}

            # Cleanup the rawdata
            for idx, line in enumerate(self.rawdata):
                line = line.strip() # eat \n
                lineno = idx + 1 # increment index for actual lineno

                # Skip blank lines and comments
                if any((line.startswith('#'), line == '')):
                    #log.msg('skipping %r' % line, debug=True)
                    continue
                #log.msg('parsing %r' % line, debug=True)

                if line.count(' = ') > 1:
                    raise CouldNotParse("Malformed line %r at line %s" % (line, lineno))

                key, sep, val = line.partition(' = ')
                if val == '':
                    continue # Don't add a key with a missing value
                    raise CouldNotParse("Missing value for key %r at line %s" % (key, lineno))

                # Check for version
                if key == 'version':
                    if val != self.version:
                        raise VersionMismatch('Bad .tacacsrc version (%s)' % v)
                    continue

                # Make sure tokens can be parsed
                realm, token, end = key.split('_')
                if end != '' or (realm, token) in data:
                    raise CouldNotParse("Could not parse %r at line %s" % (line, lineno))

                data[(realm, token)] = self._decrypt_old(val)
                del key, val, line

            # Store the creds, if a password is empty, try to prompt for it.
            for (realm, key), val in data.iteritems():
                if key == 'uname':
                    try:
                        #creds[realm] = Credentials(val, data[(realm, 'pwd')])
                        creds[realm] = Credentials(val, data[(realm, 'pwd')], realm)
                    except KeyError:
                        print '\nMissing password for %r, initializing...' % realm
                        self.update_creds(creds=creds, realm=realm, user=val)
                        #raise MissingPassword('Missing password for %r' % realm)
                elif key == 'pwd':
                    pass
                else:
                    raise CouldNotParse('Unknown .tacacsrc entry (%s_%s)' % (realm, val))

            self.data = data
            return creds
