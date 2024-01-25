from dotenv import load_dotenv
import datetime
import os
import smtplib
from email import encoders
from email.message import EmailMessage
from email.mime.base import MIMEBase
from email.utils import formatdate, make_msgid
from typing import Union, Optional

from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader, select_autoescape

from smtpymailer.functions import validate_user_email, convert_html_to_plain_text
import pydig
import dmarc

class Contact():

    email: str
    name: Optional[str]

    def __init__(self, email, name, validate_email:bool = True):
        """
        Creates a contact object to send an email from or to
        Args:
            email (str): email address
            name optional(str): name
            validate_email (bool, optional): whether to validate the email address

        Raises:
            EmailNotValidError: if the email address is not valid

        """
        self.email = email
        self.name = name

        if validate_email:
            validate_user_email(self.email)

    def __repr__(self):
        if self.name:
            return f"{self.name} <{self.email}>"
        else:
            return f"{self.email}"


class SmtpyMailer:

    recipients: Union[str, list]
    subject: str
    sender: str
    html_content: Optional[str] = None
    attachments: Optional[Union[str, list]] = None
    template: Optional[str] = None
    kwargs: Optional[dict]
    mail_server: str
    mail_port : int
    mail_use_tls : bool
    mail_username : str
    mail_password : str

    def __init__(self, recipients, subject, sender, html_content=None, attachments=None, template=None, **kwargs):
        """
        Sends emails, from alternative domains, with HTML content. Uses SMTP, but the sending mail server must be
        configured on the sending domains dns.

        DNS records for the sending domain must include:
        - SPF record for your mail server
        - DKIM record for your mail server
        - DMARC record for your mail server

         Email server auth details will check the os.environ and a .dotenv file for the following - but these can be supplied in the kwargs:
            MAIL_SERVER
            MAIL_PORT
            MAIL_USE_TLS
            MAIL_USERNAME
            MAIL_PASSWORD

        Args:
            recipients (str, list): Email address(es) to send to
            subject (str): Email subject
            sender (str): Email address to send from
            html_content (str): HTML content of the email if not using a template
            attachments (str, list): Path to file(s) to attach
            template (str): Template filename(s) to render with jinja, if html_content is not supplied
            **kwargs (dict): optional mail_server (str), mail_port (int), mail_use_tls (bool), mail_username (str), mail_password (str)

        """
        self.recipients = recipients
        self.subject = subject
        self.sender = sender
        self.html_content = html_content
        self.attachments = attachments
        self.template = template
        self.kwargs = kwargs

    def validate_auth_setup(self):
        """
        Validates the setup of the email server. Checks for the following:
            - sender - validated email
            - SPF record for your mail server
            - DKIM record for your mail server
            - DMARC record for your mail server

        Returns:
            bool

        Raises:
            Exception: if the setup is not valid

        """
        resolver = pydig.Resolver(nameservers = ['1.1.1.1','1.0.0.1','8.8.8.8','8.8.4.4'])
        dmarc = resolver.query("_dmarc.colemanbros.co.uk", "txt")
        spf = [x for x in resolver.query("colemanbros.co.uk", "TXT") if "spf" in x]


    def setup_auth(self):
        """
        Sets up the auth details for the email server. These can be supplied in the kwargs or will be checked for in the os.environ and a .dotenv file.

        Returns:
            None
        """
        # Load .env file if it exists
        load_dotenv()

        # Helper function to get the configuration value
        def get_config(key):
            # Check in dotenv
            value = os.getenv(key)
            if value:
                return value

            # Check in environment variables
            value = os.environ.get(key)
            if value:
                return value

            # Check in self.kwargs (case-insensitive)
            key_lower = key.lower()
            for k, v in self.kwargs.items():
                if k.lower() == key_lower:
                    return v

            return None

        # Configuration values
        self.mail_server = get_config('MAIL_SERVER')
        self.mail_port = get_config('MAIL_PORT')
        self.mail_use_tls = get_config('MAIL_USE_TLS')
        self.mail_username = get_config('MAIL_USERNAME')
        self.mail_password = get_config('MAIL_PASSWORD')

        #then valide it all
        self.validate_auth_setup()
    def construct_message(self):


def send_html_email(
    recipients: Union[str, list],
    subject: str,
    sender: str,
    html_content: Optional[str] = None,
    attachments: Optional[Union[str, list]] = None,
    template: Optional[str] = None,
    template_path: Optional[Union[list, str]] = None,
    **kwargs: Optional[dict],
):
    """
    Sends an email with HTML content
    Args:
        recipients (str, list): Email address(es) to send to
        subject (str): Email subject
        sender (str): Email address to send from
        html_content (str): HTML content of the email
        attachments (str, list): Path to file(s) to attach
        template (str): Template filename(s) to render
        template_path (str, list): Path to template(s) to render, can be single string path or list of string paths
        **kwargs: key word args for the template

    Returns:
        bool: True if successful, False otherwise
    """

    if not isinstance(recipients, list):
        recipients = [recipients]



    message = EmailMessage()
    message['Subject'] = subject
    message['To'] = ', '.join(recipients)
    message['Date'] = formatdate(localtime=True)
    message['Message-Id'] = make_msgid()

    message["From"] = sender
    # Set the 'From' email address

    if isinstance(attachments, str):
        attachments = [attachments]

    if attachments:
        for file_path in attachments:
            # Ensure file_path is a string
            if isinstance(file_path, str):
                try:
                    with open(file_path, "rb") as attachment:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(attachment.read())

                    encoders.encode_base64(part)

                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename={os.path.basename(file_path)}",
                    )

                    message.attach(part)
                except IOError:
                    print(f"Error opening attachment file {file_path}")
            else:
                print(f"Invalid attachment file path: {file_path}")

    if not template or html_content:
        raise Exception("You must supply either a jinja2 template filename `template` or `html_content` as a string")

    if template:

        if isinstance(template_path, str):
            template_path = [template_path]

        template_dirs = [
            "/usr/portal/main/assets/email_html",
            "/usr/portal/main/assets/templates",
        ]

        env = Environment(
            loader=FileSystemLoader(template_dirs),
            autoescape=select_autoescape(["html", "xml"]),
        )

        # Append '.html' if not in template name
        if "html" not in template:
            template += ".html"

        template = env.get_template(template)
        html_content = template.render(dated=datetime.datetime.now(), **kwargs)

    # Attach both plain text and HTML content
    message.set_content(convert_html_to_plain_text(html_content))  # for plain text
    message.add_alternative(html_content, subtype='html')  # for HTML


    try:
        with smtplib.SMTP(mail_server, mail_port) as server:
            if mail_use_tls:
                server.starttls()
            server.login(mail_username, mail_password)
            # In some implementations, you can set the envelope sender here, e.g., server.sendmail(envelope_sender, recipients, message.as_string())
            server.send_message(message)
            print("Email sent successfully")
            return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False
