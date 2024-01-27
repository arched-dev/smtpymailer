
## Sending From Alternative Domains with Postfix

### Set up a working postfix server

Follow a online guide to set up a working postfix server, for sending emails only. 
Personally I used this guide 

https://www.linuxbabe.com/mail-server/setup-basic-postfix-mail-sever-ubuntu

Follow steps 1-6, you can ignore anything Dovecot related and it's related to incoming mail (unless you want to receive
mail as well).

### SPF Record Configuration for Additional Domain

It's crucial to have a valid SPF (Sender Policy Framework) DNS record for the domain you're using to send emails. 
SPF records enable the receiving mail server to verify that your domain/IP is authorized to send emails on behalf 
of the specified domain.

Assuming you've already set this up for your own domain in Postfix, adding an SPF record for another domain 
involves a simple modification of their DNS TXT record. Here's how to do it:

1. **Identify the Current SPF Record:**
   - First, check the current SPF record of the domain. For example, it might be something 
     like `v=spf1 include:spf.protection.outlook.com -all`.

2. **Modify the SPF Record:**
   - Add your IP address (IPv4 or IPv6) to this record. 
   - For IPv4: If your IP is `192.0.2.1`, the modified record would be: 
     `v=spf1 include:spf.protection.outlook.com ip4:192.0.2.1 -all`.
   - For IPv6: If your IPv6 is `2001:db8::1234`, the record would be: 
     `v=spf1 include:spf.protection.outlook.com ip6:2001:db8::1234 -all`.

3. **Add Domain Variation:**
   - If you're sending from a specific domain, such as `mail.example.com`, add this using the `include` mechanism.
   - The record would then be: `v=spf1 include:spf.protection.outlook.com include:mail.example.com -all`.

4. **Update the DNS Record:**
   - Apply this modified SPF record to the domain's DNS settings.

This SPF configuration ensures that emails sent from your specified IP address or domain are recognized as legitimate, 
enhancing email deliverability and reducing the likelihood of being marked as spam.



### DKIM Records


Having a valid DKIM (DomainKeys Identified Mail) DNS record is crucial for the domain you're sending emails from. 
DKIM records provide a way for the receiving mail server to verify that emails sent from a particular domain or 
IP are authorized and legitimate. This is an essential aspect of email authentication, helping to prevent email 
spoofing and improve deliverability.

If you've already configured DKIM for your own domain in Postfix, extending this setup to another domain is 
relatively straightforward. It involves generating a new DKIM key for the additional domain and updating its 
DNS with the corresponding DKIM record. This process ensures that emails from each domain are independently verified, 
maintaining the integrity and trustworthiness of your email communication.

> NOTE: 
> 
>`mail` in all further commands will be the DKIM subdomain selector in the DNS record so this can be changed accordingly.
> 
> DKIM records needs to be applied to dns subdomains as 
> {selector}._domainkey 
> 
> So you will need to use a selector the domains DNS record doesn't already have.
> 
> Remember if you change `mail` to something else, you will need to change it in all following commands

#### Generate a DKIM key

You will need to generate a new DKIM key for the domain you want to send from, say its `foo.co.uk`. The below command 
will create private.txt and mail.txt  

```bash
cd /etc/opendkim/keys/foo.co.uk
sudo opendkim-genkey -s mail -d foo.co.uk
sudo chown opendkim:opendkim mail.private
```

Read the output of `mail.txt` (or whichever selector you chose) and add the DNS record to your domain. It will look 
like this 

```text
mail._domainkey	IN	TXT	( "v=DKIM1; h=sha256; k=rsa; "
	  "p=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA4j4SqifjwbhJcE35gKfPvueWM0fISjNhxDZAOhfQvLoaBb14xQGWjmVylhKmxK09G1mmId+u0KAkzTk6tKgnOeSM+Jtn9hIIuU13hZR5jSS4SX0RIlQV4epUAwFJy2tBiSfNz6wSZivCnLTijnzhlYK3UavrtO2KcGICgSUAGvakebOOe6Kfd8L+N5r7TShtIwOfDnr6fMu9Sh"
	  "MfYdw1Y65PRL900FOz2G/fmOE5Jfi5JMFc15dg88afawTP5/obUopt9p1aPLh38v+5vCFBK1K3Kt+Z23gBrD9pdGjNrqS5DRPxMxKKvd1HI6+72wLhNsKHC5ZnO3TrSX35RMFaswIDAQAB" )  ; ----- DKIM key mail for foo.co.uk
```

`mail._domainkey` is the subdomain selector, `TXT` is the record type, and the long string is the DKIM record.

#### Update the DKIM configs

Open `/etc/opendkim.conf` and find these lines. 

```text
KeyTable           refile:/etc/opendkim/key.table
SigningTable       refile:/etc/opendkim/signing.table
InternalHosts       /etc/opendkim/trusted.hosts
```

These all need to be updated to include the new domain. 

edit `SigningTable` and add a new line  (i.e /etc/opendkim/signing.table)

`*@foo.co.uk mail._domainkey.foo.co.uk`

edit `KeyTable` and add a new line (i.e /etc/opendkim/key.table)

`mail._domainkey.foo.co.uk foo.co.uk:mail:/etc/opendkim/keys/foo.co.uk/mail.private'

edit `InternalHosts` and add a new line (i.e /etc/opendkim/trusted.hosts)

`foo.co.uk'

#### Restart opendkim

```bash
sudo systemctl restart opendkim
```


### Configure SASL

To enable Postfix to send emails from alternative domains on your server, configuring SASL 
(Simple Authentication and Security Layer) is essential. SASL enhances security by allowing Postfix to 
authenticate against a designated authentication server, ensuring that only authorized users can send emails. 
This setup is particularly important when your server handles multiple domains, as it maintains distinct 
authentication for each domain. Proper SASL configuration prevents misuse of your mail server and helps in 
maintaining a good sending reputation, crucial for email deliverability and avoiding spam filters.

```bash
sudo apt-get install libsasl2-modules
```

Edit `/etc/postfix/main.cf` and add the following lines:

```text
smtpd_sasl_auth_enable = yes
smtpd_sasl_security_options = noanonymous, noplaintext
smtpd_sasl_local_domain = $myhostname
smtpd_sender_login_maps = hash:/etc/postfix/sender_login_maps
```
Create the SASL config file '/etc/postfix/sasl/smtpd.conf' and add the following lines:

```text
pwcheck_method: saslauthd
mech_list: PLAIN LOGIN
```

Edit `/etc/default/saslauthd` and add the following lines to start the daemon on boot:

```text
START=yes
```

Start the SASL daemon:

```bash
sudo systemctl start saslauthd
sudo systemctl enable saslauthd
```

Create the file `/etc/postfix/sender_login_maps` this will map the email address to the username and password for SASL.

The first section is the email you want to send from (not your domain) and the second is the username who you will 
be logging into the mail server as (which you will have set up while configuring postfix)

```text
@foo.co.uk bar
@foobarr.co.uk barfoo
```

Remap the sender login maps like to the db with the following command:

```bash
sudo postmap /etc/postfix/sender_login_maps
````

Restart postfix:

```bash
sudo systemctl restart postfix
```




## Validation

Once setup, use a service like https://www.mail-tester.com/ to test your outgoing mail.  
