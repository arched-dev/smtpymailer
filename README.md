
# smtpymailer

## Introduction
`smtpymailer` is a versatile Python library designed to simplify the process of sending emails in python. It supports
and validates DKIM, DMARC, and SPF records before sending emails to avoid being marked as spam, so it is ideal for sending 
emails from your own mail server but the sender is an alternative domain.


## Features
- Login to any mail server of your choice (I maintain a postfix server for outgoing mail only, so replies are still directed to the users normal inbox).
- Send emails from different domains, provided the correct DNS settings are in place.
- Validates DNS settings like DKIM, DMARC, and SPF before sending emails to avoid being marked as spam.
- Full email functionality including `To`, `CC`, `BCC`, `Reply-To`, and attachments.
- Adds attachments with the correct MIME type.
- Optionally converts url <img> tags to inline attachments CID attachments or Base64 encoded img sources.
- Supports sending string HTML content, Jinja templates, or plain html files.
- Automatically converts HTML to plain text for email clients that do not support HTML.
- Supports environment variables and `.env` files for mail server settings.

## Installation
Install the package using `pip`:

```bash
pip install smtpymailer
```

## Usage

### Initialization

Create an instance of `SmtpyMailer` with your sender email and name. The mail server details can be passed as keyword
arguments or sourced from environment variables or a `.env` file.

```python
from smtpymailer import SmtpMailer
mailer = SmtpMailer(sender_email="foo@bar.com", sender_name="Foo Bar")
```

### Environment Variables

The following environment variables can be set or added to a `.env` file in your project root.
Alternatively you can pass as **kwargs to the `SmtpyMailer` class but this is not advised.

- `MAIL_SERVER`
- `MAIL_PORT`
- `MAIL_USE_TLS`
- `MAIL_USERNAME`
- `MAIL_PASSWORD`
- `MAIL_DKIM_SELECTOR`

### Sending an Email

Use the `send_email` method to send emails:


#### Parameters

- `recipients`: Single recipient email or a list of email addresses.
- `subject`: Email subject.
- `cc_recipients`: (Optional) Single or list of CC email addresses.
- `bcc_recipients`: (Optional) Single or list of BCC email addresses.
- `reply_to`: (Optional) Reply-to email address.
- `attachments`: (Optional) Single file path or list of file paths for attachments.
- `html_content`: (Optional) HTML content of the email (not required if using a template)
- `template`: (Optional) Template file path (using jinja), it can be just a plain html file.
- `template_directory`: (Optional) Single or list of template directories.
- `alter_img_src`: (Optional) String to download and convert img src to base64 encoded strings (either cid|base64).
- `**kwargs`: Additional arguments for jinja template, if needed.

### Example

- Send a simple email with a subject and html content.

```python
from smtpymailer import SmtpMailer
mailer = SmtpMailer(sender_email="foo@bar.com", sender_name="Foo Bar")
mailer.send_email(recipients="bar@baz.com", subject="My test email", html_content="<h1>Hello World</h1>")
```

- Send to multiple recipients, one CC, with an attachment, and a jinja template with kwargs.

```python
from smtpymailer import SmtpMailer
mailer = SmtpMailer(sender_email="foo@bar.com", sender_name="Foo Bar")
template_data = {"name": "Foo Bar", "message": "Hello Foo", "url": "https://www.foo.com"}
mailer.send_email(recipients=["bar@baz.com", "baz@bar.com"], cc_recipients="foo@baz.com", subject="My test email", template="template.html", template_directory="./templates", **template_data)
```
## Sending From Alternative Domains

You can send emails from alternative domains by setting up the correct DNS settings. Here's how to do it.
[Alt Domains Documentation](./docs/ALT_DOMAINS.md)

## License
This project is licensed under the [MIT License](LICENSE).

## TODO
- Add support for local files to be changes to CID attachments in the <img> src.
