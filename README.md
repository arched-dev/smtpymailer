
# smtpymailer

## Introduction
`smtpymailer` is a versatile Python library designed to simplify the process of sending emails from various domains. Its primary functionality allows users to log in to a chosen mail server and send emails from different domains, given that the sending domain has the correct DNS settings (DKIM, DMARC, SPF, etc.). The library ensures that these settings are validated before any email is sent to avoid being marked as spam.

The main goal was to send emails from my mailserver for my customers, on their behalf without the worry of passwords changing or tokens expiring etc.

## Features
- Login to any mail server of your choice (I maintain a postfix server for outgoing mail only, so replies are still directed to the users normal inbox).
- Send emails from different domains, provided the correct DNS settings are in place.
- Full email functionality including `To`, `CC`, `BCC`, `Reply-To`, and attachments.
- Validates DNS settings like DKIM, DMARC, and SPF before sending emails to avoid being marked as spam.

## Installation
Install the package using `pip`:

```bash
pip install smtpymailer
```

## Usage

### Initialization
Create an instance of `SmtpyMailer` with your sender email and name. The mail server details can be passed as keyword arguments or sourced from environment variables or a `.env` file.

```python
mailer = SmtpMailer(sender_email="foo@bar.com", sender_name="Foo Bar")
```

### Environment Variables
The following environment variables can be set:

- `MAIL_SERVER`
- `MAIL_PORT`
- `MAIL_USE_TLS`
- `MAIL_USERNAME`
- `MAIL_PASSWORD`
- `MAIL_DKIM_SELECTOR`

### Sending an Email
Use the `send_email` method with the following parameters:

```python
mailer.send_email(
    recipients,
    subject,
    cc_recipients=None,
    bcc_recipients=None,
    reply_to=None,
    attachments=None,
    html_content=None,
    template=None,
    template_directory=None,
    **kwargs
)
```

### Parameters
- `recipients`: Single recipient email or a list of email addresses.
- `subject`: Email subject.
- `cc_recipients`: (Optional) Single or list of CC email addresses.
- `bcc_recipients`: (Optional) Single or list of BCC email addresses.
- `reply_to`: (Optional) Reply-to email address.
- `attachments`: (Optional) Single file path or list of file paths for attachments.
- `html_content`: (Optional) HTML content of the email (not required if using a template).
- `template`: (Optional) Template file path.
- `template_directory`: (Optional) Single or list of template directories.
- **kwargs: Additional arguments for jinja template, if needed.


## License
This project is licensed under the [MIT License](LICENSE).

## TODO

- [ ] Add SPF tests
- [ ] Add DMARC tests
