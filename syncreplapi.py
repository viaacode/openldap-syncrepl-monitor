import re
from socket import getfqdn
from dateutil import parser
import connexion
import ldap

# Every ldapquery opensig

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
    FQDN = getfqdn()
    RE_CSN = re.compile('(?P<timestamp>\d+).\d+(?P<timezone>[\w:+-])*#\d+#(?P<sid>\d+)#\d+')

    def __init__(self, uri):
        self.uri = uri

    # gets the csn of the base DSE for the given suffix and provider serverID
    def get_csn(self, suffix, sid):
        with LdapReader(self.uri) as conn:
            result = conn.search_s(suffix, ldap.SCOPE_BASE, attrlist=['contextCSN'])
            contextCSNs = [ x.decode() for x in result[0][1]['contextCSN'] ]
            for contextCSN in contextCSNs:
                m = self.RE_CSN.match(contextCSN)
                # sid in contextCSN is hex
                if int(m.group('sid'),16) != sid: continue
                csn = parser.parse(m.group('timestamp') + m.group('timezone'))
                break
        return(csn)

    def get_backends(self):
        with LdapReader(self.uri) as conn:
            result = conn.search_s('cn=config', ldap.SCOPE_SUBTREE,
                   filterstr='(objectClass=olcDatabaseConfig)', attrlist=['olcSuffix'])
            backends = [ y['olcSuffix'][0].decode() for x,y in result if y.get('olcSuffix')]
        return backends

    @staticmethod
    def host2uri(uri):
       return(re.match('ldap\w*://(\S*)',uri).group(1))

class LdapProvider(LdapServer):
    RE_SID = re.compile('(?P<sid>\d+)\s*(?P<uri>[\S]*)')

    def __init__(self):
        super().__init__('ldapi:///')
        self.id = self.get_id()
        self.backends = self.get_backends()
        self.peers = self.get_peers()

    def serverid_list(self):
        with LdapReader(self.uri) as conn:
            result = conn.search_s('cn=config', ldap.SCOPE_BASE, attrlist=['olcServerID'])
            serverIDs = [ self.RE_SID.match(x.decode()).groups() for x in result[0][1]['olcServerID'] ]
        return serverIDs

    def get_id(self):
        serverids = self.serverid_list()
        id = [ sid for (sid,uri) in serverids if uri == '' or self.host2uri(uri) == self.FQDN ]
        return int(id[0])

    def get_peers(self):
        serverids = [ (sid, self.host2uri(uri)) for (sid, uri) in self.serverid_list() ]
        return set( [ host for (sid,host) in serverids if host != self.FQDN ] )

    def get_csn(self, suffix):
        return super().get_csn(suffix,self.id)


def get_status(consumers):
    my_consumers = provider.peers.union(consumers)
    result = []
    for backend in provider.backends:
        master_csn = provider.get_csn(backend)
        for server in my_consumers:
            consumer = LdapServer('ldaps://{}/'.format(server))
            try:
                # the consumer could be more recent than the provider if data is
                # being replicated during this call. Put the delay to 0 in that
                # case.
                delay = max( (master_csn - consumer.get_csn(backend, provider.id)).total_seconds() / 3600, 0 )
                result.append({
                    'Channel': '{} - {}'.format(server, backend),
                    'Value': delay,
                    })
            except ldap.LDAPError:
                pass
    print(result)
    return {'delay': result}


provider = LdapProvider()
app = connexion.App(__name__)
app.add_api('swagger.yaml')
app.run(port=8080)

