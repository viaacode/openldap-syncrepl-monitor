import connexion
from syncreplinfo import LdapServer, LdapProvider

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
#
