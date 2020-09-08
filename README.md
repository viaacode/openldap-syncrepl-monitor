# openldap-syncrepl-monitor
REST API for monitoring the synchronicity between openldap syncrepl providers and consumers

It will automatically discover the peers of a multimaster setup if their URIs are specified in the olcServerID attribute.

```
GET /status?consumers=dg-qas-dcs-01.dg.viaa.be,do-qas-dcs-02.do.viaa.be
{
  "delay": [
    {
      "Channel": "do-qas-dcs-02.do.viaa.be - dc=hetarchief,dc=be",
      "Value": 0.0
    },
    {
      "Channel": "do-qas-dcs-m0.do.viaa.be - dc=hetarchief,dc=be",
      "Value": 0.0
    },
    {
      "Channel": "dg-qas-dcs-01.dg.viaa.be - dc=hetarchief,dc=be",
      "Value": 0.0
    },
    {
      "Channel": "do-qas-dcs-02.do.viaa.be - dc=qas,dc=viaa,dc=be",
      "Value": 0.0
    },
    {
      "Channel": "do-qas-dcs-m0.do.viaa.be - dc=qas,dc=viaa,dc=be",
      "Value": 0.0
    },
    {
      "Channel": "dg-qas-dcs-01.dg.viaa.be - dc=qas,dc=viaa,dc=be",
      "Value": 0.0
    }
  ]
}
```

Designed to run stateless on an ldap provider. Therefore
- it needs passwordless read access to
  - local ldap: configuration settings attributes olcServerID and olcSuffix
  - remote ldap: conectCSN of the backend databases' base entry
- additional consumers to be monitored must be specified as request argument `consumers`

## access to local configuration
This is achieved by using SASL EXTERNAL authentication with IPC identity format.

## access to the contextCSN of the backend databases.
Add an ACL giving anonymous read access to the *base* entry of the backend. It is important to restrict access to only the base entry by using `dn.base`:
```
olcAccess: to dn.base="<suffix>" by * read 
```
Restricting access to the contexCSN attribute in the ACL above does not work. conetxCSN apparently is not a regular attribute on which one can set an ACL. Access to base entry attributes to which unauthenticated read access is not allowed must be restricted in earlier olcAccess rules. 

