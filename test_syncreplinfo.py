import pytest
import syncreplinfo

from mockldap.mockldap import MockLdap

import datetime
import re


ldapservers = [
        {
            'hostname': 'master-1.example.com',
            'id': 50,
            'year': 2021
            },
        {
            'hostname': 'master-2',
            'id': 9,
            'year': 2020
            },
        {
            'hostname': 'master-3.example.com',
            'id': 16,
            'year': 2019
            },
        ]

suffixmonth = {
        'dc=suffix1,dc=be': 5,
        'dc=suffix2,dc=be': 6
        }

# Directory contents for our mocked ldap servers in a
# n-way multi-provider setup.
# In order to test if the code attributes the contextCSNs correctly, the
# contextCSNs of each provider are in the same year as per the variable
# ldapservers.
# In order to test if the code identifies the correct contextCSN for a given
# suffix, the contextCSN of each suffix are in the same month as per the
# variable suffixmonth.
@pytest.fixture(scope='class')
def dit(olcserverid):
    d = {
        'cn=config': {
            'objectClass': [ b'olcGlobal']
            },
        'olcDatabase={1}bdb,cn=config': {
            'objectClass': [ b'olcDatabaseConfig' ],
            'olcSuffix': [ b'dc=suffix1,dc=be' ],
            },
        'olcDatabase={2}bdb,cn=config': {
            'objectClass': [ b'olcDatabaseConfig' ],
            'olcSuffix': [ b'dc=suffix2,dc=be' ],
            },
        'dc=suffix1,dc=be': {
            'objectClass': [ b'domain' ],
            'contextCSN': [ b'20210522090920.512119Z#000000#032#000000', b'20200501000000.423865Z#000000#009#000000', b'20190512232324.423865Z#000000#010#000000'  ]
            },
        'dc=suffix2,dc=be': {
            'objectClass': [ b'domain' ],
            'contextCSN': [ b'20210622090920.512119Z#000000#032#000000', b'20200601000000.423865Z#000000#009#000000', b'20190612164521.423865Z#000000#010#000000' ]
            }
        }
    if olcserverid: d['cn=config']['olcServerID'] = olcserverid
    return d

@pytest.fixture(scope='class')
def ldapmock(dit):
    myldap = MockLdap(dit)
    myldap.start()
    yield myldap
    myldap.stop()

class TestProviderMulti:

    # The id's and hiostnames much match the ldapserver variable above in order
    # for the tests to succeed.
    @pytest.fixture(scope='class')
    def olcserverid(self):
        return list(map(lambda x: x.encode(),
            [
                "50 ldaps://master-1.example.com",
                "9 ldaps://master-2",
                "16 ldap://master-3.example.com"
                ]
            ))

    @pytest.fixture(params=ldapservers)
    def provider(self, mocker, ldapmock, request):
        self.master = request.param['hostname']
        self.id = request.param['id']
        self.year = request.param['year']
        mocker.patch.object(syncreplinfo.LdapServer,'FQDN', request.param['hostname'])
        return syncreplinfo.LdapProvider()

    def test_id(self, provider):
        assert provider.id == self.id

    def test_peers(self, provider):
        peers = provider.peers
        assert type(peers) is set
        assert self.master not in peers
        assert len(peers) == 2
        assert len(list(filter(lambda x: re.match(r'master-\d+(\.example.com)?$', x), peers))) == 2

    def test_backends(self, provider):
        assert type(provider.backends) is list
        assert len(provider.backends) == 2
        assert 'dc=suffix1,dc=be' in provider.backends
        assert 'dc=suffix2,dc=be' in provider.backends

    @pytest.mark.parametrize('suffix',suffixmonth.keys())
    def test_csn(self, provider, suffix):
        assert isinstance(provider.get_csn(suffix),datetime.datetime)
        assert provider.get_csn(suffix).year == self.year
        assert provider.get_csn(suffix).month == suffixmonth[suffix]

class TestProviderSingle:
    @pytest.fixture(scope='class')
    def olcserverid(self):
        return [ str(9).encode() ]

    @pytest.fixture
    def provider(self, ldapmock):
        return syncreplinfo.LdapProvider()

    def test_id(self, provider):
        assert provider.id == 9

    def test_peers(self, provider):
        assert provider.peers == set([])

    @pytest.mark.parametrize('suffix',suffixmonth.keys())
    def test_csn(self, provider, suffix):
        assert isinstance(provider.get_csn(suffix),datetime.datetime)
        assert provider.get_csn(suffix).year == 2020
        assert provider.get_csn(suffix).month == suffixmonth[suffix]

class TestProviderNone:
    @pytest.fixture(scope='class')
    def olcserverid(self):
        return None

    @pytest.fixture
    def provider(self, ldapmock):
        return syncreplinfo.LdapProvider()

    def test_peers(self, provider):
        assert provider.peers == set([])

    def test_id(self, provider):
        assert provider.id == None
