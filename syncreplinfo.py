import re
from socket import getfqdn
from dateutil import parser as dateparser
import ldap

# Ldap Reader object intended to be read from using the pyhton with statement
class LdapReader:
    def __init__(self, uri):
        self.uri = uri
        self.connection = ldap.initialize(uri)

    def __enter__(self):
        if re.match('ldapi:', self.uri):
            self.connection.sasl_external_bind_s()
        else:
            self.connection.bind_s('','')
        return(self.connection)

    def __exit__(self, typ, val, traceback):
        self.connection.unbind_s()

class LdapServer:
    ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
    ldap.set_option(ldap.OPT_DEBUG_LEVEL, 0)
    FQDN = getfqdn() # The fully quallified name of our host

    def __init__(self, uri):
        self.uri = uri

    # gets the csn of the base DSE for the given suffix and provider serverID
    def get_csn(self, suffix, pid):
        with LdapReader(self.uri) as conn:
            result = conn.search_s(suffix, ldap.SCOPE_BASE, attrlist=['contextCSN'])
        contextCSNs = [ self.parse_csn(x.decode()) for x in result[0][1]['contextCSN'] ]
        timestamp = [ t for (s,t) in contextCSNs if s == pid ][0]
        return dateparser.parse(timestamp)

    def get_backends(self):
        with LdapReader(self.uri) as conn:
            result = conn.search_s('cn=config', ldap.SCOPE_SUBTREE,
                   filterstr='(objectClass=olcDatabaseConfig)', attrlist=['olcSuffix'])
        return [ y['olcSuffix'][0].decode() for x,y in result if y.get('olcSuffix') ]

    @staticmethod
    def host2uri(uri):
       return re.match(r'ldap\w*://(\S*)', uri).group(1)

    @staticmethod
    def parse_csn(csn):
        m = re.match(r'(?P<timestamp>\d+).\d+(?P<timezone>[\w:+-])*#\d+#(?P<sid>\d+)#\d+', csn)
        # sid in contextCSN is hex
        return (int(m.group('sid'),16), m.group('timestamp') + m.group('timezone'))

class LdapProvider(LdapServer):

    def __init__(self):
        super().__init__('ldapi:///')
        self.id = self.get_id()
        self.backends = self.get_backends()
        self.peers = self.get_peers()

    # Returns the olcServerID attribute as a list of tuples (id, uri)
    def serverids(self):
        with LdapReader(self.uri) as conn:
            result = conn.search_s('cn=config', ldap.SCOPE_BASE, attrlist=['olcServerID'])
        return [ tuple(x.decode().split()) for x in result[0][1]['olcServerID'] ]

    # Returns the id of the ldapserver on our host as an integer
    # olcServerID can have a value with or without uri:
    #   - with uri: the serverid of the instance is in the olcServerID
    #     attribute with uri == fqdn of the our host
    #   - without uri (len of the serverids tuple is 1): the current serverid
    #     is the value of the olcServerID attribute.
    def get_id(self):
        sid = [ s[0] for s in self.serverids() if len(s) == 1 or self.host2uri(s[1]) == self.FQDN ]
        return int(sid[0])

    # If the uris in a multimaster setup are specified in the
    # olcServerID attribute, then get_peers returns the peers of our host as a set
    def get_peers(self):
        peers = [ self.host2uri(uri) for (sid, uri) in self.serverids() ]
        return set(filter(lambda h: h != self.FQDN, peers))

    # The provider's own csn
    def get_csn(self, suffix):
        return super().get_csn(suffix,self.id)

