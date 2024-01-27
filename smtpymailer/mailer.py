import os
import pathlib
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from mimetypes import guess_type
from typing import Union, Optional, List

import pydig
from dotenv import load_dotenv

from smtpymailer.html_parse import (
    convert_html_to_plain_text,
    alter_img_html,
    make_html_content,
)
from smtpymailer.utils import (
    is_file_with_path,
    convert_bool,
    recipients_to_str,
    build_all_recipients_and_validate,
    ensure_list,
    construct_mime_object,
)
from smtpymailer.validation import (
    validate_user_email,
    validate_dmarc_record,
    spf_check,
    get_address_type,
    validate_dkim_record,
)


class Contact:
    """
    Contact class represents a contact with an email address and a name. It provides methods to manipulate and retrieve information about the contact.

    Attributes:
        email (str): The contact's email address.
        name (Optional[str]): The contact's name (optional).

    Methods:
        __init__(self, email: str, name: Optional[str] = None, validate_email: bool = True):
            Initializes a Contact object with the specified email address and name.
            Raises EmailNotValidError if the email address is not valid.

        __repr__(self) -> str:
            Returns a string representation of the Contact object.

        get_domain(self) -> str:
            Returns the domain of the email address.

    Raises:
        EmailNotValidError: If the email address is not valid.
    """

    email: str
    name: Optional[str]

    def __init__(self, email, name, validate_email: bool = True):
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

    def get_domain(self):
        """
        Gets the domain of the email address
        Returns:
            str: domain

        """
        return self.email.split("@")[1]


def validate_send_email(
    html_content,
    template,
    template_directory,
    subject,
    recipients,
):
    """
    Validates the parameters for the `send_email` function. it performs the following validations:
        * If neither `html_content` nor `template` is provided.
        * If `template` is a file name but `template_directory` is not provided.
        * If `subject` is empty.
        * If `recipients` is not provided.

    Args:
        html_content (Optional(str)): The HTML content of the email.
        template (Optional(str)): The name of the template to use for the email. If `html_content` is not provided.
            This should be a valid Jinja template.
        template_directory (Optional(Union[list,str])): The directory where the template file is located (if using a template).
            This should only be provided if `template` is a file name and not a full path. Can be a string or list of
            strings.
        subject (str): The subject of the email.
        recipients (str or list): The recipient(s) of the email. This can be a single email address as a string,
            or a list of email addresses.

    Raises:
        ValueError: If neither `html_content` nor `template` is provided.
        FileNotFoundError: If `template` is a file name but `template_directory` is not provided.
        ValueError: If `subject` is empty.
        ValueError: If `recipients` is not provided.

    """
    if not html_content or not template:
        if template:
            if not is_file_with_path(template) and not template_directory:
                raise FileNotFoundError(
                    "Template file not found. Please provide either a full path to the template or a template file and template directory"
                )
            elif not is_file_with_path(template) and not any(
                [
                    is_file_with_path(os.path.join(x, template))
                    for x in ensure_list(template_directory)
                ]
            ):
                raise FileNotFoundError(
                    "Template file not found. Please provide either a full path to the template or a template file and template directory"
                )
        if not html_content and not template:
            raise ValueError(
                "Please provide either 'html_content' or a jinja template to render"
            )

    if not subject:
        raise ValueError("Subject cannot be empty. Please provide a subject")

    if not recipients:
        raise ValueError(
            "Recipients not provided. Please provide a single recipient's email or a list of email addresses"
        )


class SmtpMailer:
    """
    Send emails from alternative domains names to the mail server. DNS records must be correctly assigned to the
    sending domain.
    """

    sender: Contact
    html_content: Optional[Union[str, pathlib.Path]] = None
    mail_server: str
    mail_port: int
    mail_use_tls: bool
    mail_username: str
    mail_password: str
    mail_dkim_selector: str = "mail"
    message: MIMEMultipart
    message_alt: MIMEMultipart

    def __init__(self, sender_email: str, sender_name: Optional[str], **kwargs):
        """
        Send emails from alternative domains names to the mail server. DNS records must be correctly assigned to the
        sending domain.

        Required DNS must include:

        * A valid SPF record
        * A valid DMARC record
        * A DKIM record generated from YOUR sending mail server

        Email server auth details need to be supplied, and in the interest of security can and are preferred to be
        stored in the environment. `SmtpMailer` will check the `os.environ`, dotenv `.env` file in the root directory
        or can be supplied (**IF YOU HAVE TO**) as kwargs.

        Notes:
            If either the email fails to validate or the email server auth fails to validate, an exception will be
            raised.

        Configuration Parameters:
            **MAIL_SERVER**: The hostname or IP address of the email server.

            **MAIL_PORT**: The port number of the email server.

            **MAIL_USE_TLS**: Boolean to enable/disable Transport Layer Security.

            **MAIL_USERNAME**: The username for the email server.

            **MAIL_PASSWORD**: The password for the email server.

            **MAIL_DKIM_SELECTOR**: The DKIM selector to use for email signing, created by the mail server and applied
            to the sending domain's DNS records.


        Args:
            sender_email (str): Email address to send from
            sender_name (str): Name to use in email from field

        """

        self.sender = Contact(sender_email, sender_name)
        self._setup_email_server_auth(**kwargs)
        self._validate_auth_setup()

    def _validate_auth_setup(self):
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
        resolver = pydig.Resolver(
            nameservers=["1.1.1.1", "1.0.0.1", "8.8.8.8", "8.8.4.4"]
        )
        sender_domain = self.sender.get_domain()

        dmarc_records, spf_records, dkim_records = self._query_dns_records(
            resolver, sender_domain
        )

        self._validate_records(sender_domain, dmarc_records, spf_records, dkim_records)

    def _query_dns_records(self, resolver, sender_domain):
        """
        Args:
            resolver: A DNS resolver object that allows querying of DNS records.
            sender_domain: The domain name of the sender for which DNS records need to be queried.

        Returns:
            A tuple of three lists representing the DNS records:
            - dmarc_records: A list of TXT records associated with the "_dmarc" subdomain of the sender domain.
            - spf_records: A list of TXT records that contain "spf" keyword and are associated with the sender domain.
            - dkim_records: A list of TXT records associated with the DKIM selector and "_domainkey" subdomain of the sender domain.

        Note:
            The returned lists may be empty if no matching DNS records are found.
        """
        dmarc_records = resolver.query(f"_dmarc.{sender_domain}", "TXT")
        spf_records = [
            x for x in resolver.query(f"{sender_domain}", "TXT") if "spf" in x
        ]
        dkim_records = [
            x
            for x in resolver.query(
                f"{self.mail_dkim_selector}._domainkey.{sender_domain}", "TXT"
            )
            if "DKIM" in x
        ]
        return dmarc_records, spf_records, dkim_records

    def _validate_records(
        self,
        sender_domain: str,
        dmarc_records: list,
        spf_records: list,
        dkim_records: list,
    ):
        """
        Args:
            sender_domain (str): The domain of the sender.
            dmarc_records (list): A list of DMARC records for the sender domain.
            spf_records (list): A list of SPF records for the sender domain.
            dkim_records (list): A list of DKIM records for the sender domain.

        Raises:
            Exception: If none of the DMARC records for the sender domain are valid.
            Exception: If none of the SPF records for the sender domain are valid.
            Exception: If none of the DKIM records for the sender domain are valid.
        """

        valid_dmarc = False
        for record in dmarc_records:
            if validate_dmarc_record(record):
                valid_dmarc = True
                break
        if not valid_dmarc:
            raise Exception(f"No valid DMARC record found for {sender_domain}")

        valid_spf = False
        for record in spf_records:
            if spf_check(record, **get_address_type(self.mail_server)):
                valid_spf = True
                break
        if not valid_spf:
            raise Exception(f"No valid SPF record found for {sender_domain}")

        valid_dkim = False
        for record in dkim_records:
            if validate_dkim_record(record):
                valid_dkim = True
                break
        if not valid_dkim:
            raise Exception(f"No valid DKIM record found for {sender_domain}")

    def _setup_email_server_auth(self, **kwargs):
        """
        Args:
            **kwargs: Additional keyword arguments that can be passed to the method.

        Raises:
            Exception: If a required configuration value is not found.

        """
        # Load .env file if it exists
        load_dotenv()

        # Helper function to get the configuration value
        def get_config(key):
            """
            Args:
                key: The config key to retrieve the value for.

            Returns:
                The value corresponding to the given config key, or None if the key was not found in any of the
                available sources (dotenv, environment variables, or kwargs).

            """

            # This is discouraged and only first, so I force a unit test to fail.
            key_lower = key.lower()
            for k, v in kwargs.items():
                if k.lower() == key_lower:
                    return v

            # Check in dotenv
            value = os.getenv(key) or os.getenv(key.lower())
            if value:
                return value

            raise ValueError(f"Could not find config value for {key}, cannot continue.")

        # Configuration values
        self.mail_server = get_config("MAIL_SERVER")
        self.mail_port = int(get_config("MAIL_PORT"))
        self.mail_use_tls = convert_bool(get_config("MAIL_USE_TLS"))
        self.mail_username = get_config("MAIL_USERNAME")
        self.mail_password = get_config("MAIL_PASSWORD")
        self.mail_dkim_selector = get_config("MAIL_DKIM_SELECTOR")

        # check for required values and raise exception if not found
        with self._connect_to_server() as server:
            server.quit()

    def _connect_to_server(self):
        """
        Connects to the mail server.
        Returns:
            server: An instance of the server connection
        Raises:
            ValueError: If there is an error connecting to the mail server or invalid server connection details
        """
        try:
            server = smtplib.SMTP(self.mail_server, self.mail_port)
            if self.mail_use_tls:
                server.starttls()
            server.login(self.mail_username, self.mail_password)
            return server
        except:
            raise ValueError(
                "Invalid server connection details, please check and try again"
            )

    def _send_message(self, recipients: list):
        """
        Sends a message if provided.

        Args:
            recipients: a list of all email addresses to send email to including bcc emails that are not in the header.

        Returns:
            True if the message was sent successfully, otherwise raises an Exception.
        """
        try:
            with self._connect_to_server() as server:
                server.sendmail(str(self.sender), recipients, self.message.as_string())
            return True
        except Exception as e:
            raise Exception(f"Failed to send message: {e}")

    def _construct_base_message(
        self,
        subject: str,
        recipients: str,
        cc_recipients: Optional[str] = None,
        reply_to: Optional[str] = None,
    ):
        """
        Args:
            subject (str): The subject of the email message.
            recipients (str): The recipients of the email message.
            cc_recipients (Optional[str], optional): The CC recipients of the email message. Defaults to None.
            reply_to (Optional[str], optional): The reply-to address of the email message. Defaults to None.
            None.

        Returns:
            MIMEMultipart: The constructed base email message.

        """
        message = MIMEMultipart("mixed")

        message["Subject"] = subject
        message["To"] = recipients
        message["Date"] = formatdate(localtime=True)
        message["Message-Id"] = make_msgid()
        message["From"] = str(self.sender)

        if cc_recipients:
            message["Cc"] = cc_recipients

        if reply_to and validate_user_email(email=reply_to, check_deliverability=True):
            message["Reply-To"] = reply_to

        return message

    def _add_attachments(self, attachments: Optional[Union[List[str], str]] = None):
        """
        Args:
            attachments: Optional[List[str] or str] - The attachment file paths to be added. It can be a single file path string or a list of file paths.

        Raises:
            Exception:
                * If the attachment file path is invalid or non-existent.
                * If the file is not found.
                * If there is a permission error while opening the file.
                * If there is an error while opening the attachment file.
        Returns:
            None

        """
        attachments = ensure_list(attachments)

        for attachment_file_path in attachments:

            # Expand the user path, if needed and user has used ~/path/to/file
            attachment_file_path = os.path.expanduser(attachment_file_path)

            if isinstance(attachment_file_path, str) and os.path.isfile(
                attachment_file_path
            ):
                try:
                    with open(attachment_file_path, "rb") as attachment:
                        part = construct_mime_object(attachment_file_path, attachment)
                        part.add_header(
                            "Content-Disposition",
                            f"attachment; filename={os.path.basename(attachment_file_path)}",
                        )
                        self.message.attach(part)

                except PermissionError:
                    raise Exception(
                        f"Cannot open file. Check if the file is open in another program {attachment_file_path}"
                    )
                except IOError as e:
                    raise Exception(
                        f"Error opening attachment file {attachment_file_path}: {e}"
                    )
            else:
                raise FileNotFoundError(
                    f"Invalid or non existent attachment file path: {attachment_file_path}"
                )

    def _make_plain_message(self, html_content):
        """
        Creates a plain text version of the email, using the HTML content it coverts it to plain text.

        Args:
            html_content: A string representing the HTML content of the email.

        Notes:
            This method sets the class attribute `message_alt` to a MIMEMultipart object containing the plain
            text version of the email.

        """
        plain_html = convert_html_to_plain_text(html_content)

        # Attach the plain and HTML versions
        self.message_alt = MIMEMultipart("alternative")
        self.message.attach(self.message_alt)

        # create plain email
        msg_text = MIMEText(plain_html, "plain")
        self.message_alt.attach(msg_text)

    def _make_html_message(self, html_content: str, alter_img_src: str):
        """
        Creates an HTML version of the email, using the HTML content it converts it to HTML.

        It also alters the HTML content based on the specified `alter_img_src` parameter. It either converts image
        elements in the HTML content to base64 encoding or attaches images as CID from the url in the src attribute of
        any <img> HTML elements.

        Args:
            html_content (str): The HTML content of the message.
            alter_img_src (str): Flag indicating whether to alter image src attributes, can be 'base64' or 'cid'.

        Notes:
            This method sets the class attribute `message_alt` to a MIMEMultipart object containing the HTML
            version of the email.

        """
        if alter_img_src:
            html_content = alter_img_html(self.message, html_content, alter_img_src)

        # create html email
        msg_html = MIMEText(html_content, "html")
        self.message_alt.attach(msg_html)

    def send_email(
        self,
        recipients: Union[str, list],
        subject: str,
        cc_recipients: Optional[Union[str, list]] = None,
        bcc_recipients: Optional[Union[str, list]] = None,
        reply_to: Optional[str] = None,
        attachments: Optional[Union[List, str]] = None,
        html_content: Optional = None,
        template: Optional = None,
        template_directory: Optional[Union[str, list]] = None,
        alter_img_src: Optional[str] = None,
        **kwargs,
    ):
        """
        Sends an email with the given parameters.

        Args:
            recipients: Either a single recipient email address or a list of email addresses.
            subject: The subject of the email.
            cc_recipients: Optional. Either a single cc recipient email address or a list of email addresses.
            bcc_recipients: Optional. Either a single bcc recipient email address or a list of email addresses.
            reply_to: Optional. The reply-to email address.
            attachments: Optional. Either a single attachment file path or a list of attachment file paths.
            html_content: Optional. The HTML content of the email, not needed if you are using a template.
            template: Optional. The template file path.
            template_directory: Optional. Either a single template directory or a list of template directories.
            alter_img_src: Optional. String, can either be 'base64' or 'cid'. If 'base64', any <img> HTML elements with
            src as a URL will be converted to base64. If 'cid', any <img> HTML elements with src as a URL will be
            converted to cid. Defaults to None.
            **kwargs: Additional keyword arguments for the jinja template if needed

        Raises:
            Exception:
                * If neither 'html_content' nor a template is provided
                * When a `template` str is passed with no directory and no `template_directory` is supplied.
                * Blank subject field
                * Empty str or list of `recipients`

        Returns:
            True if the email was sent successfully, otherwise raises an Exception.

        """

        validate_send_email(
            html_content, template, template_directory, subject, recipients
        )

        all_recipients = build_all_recipients_and_validate(
            recipients, cc_recipients, bcc_recipients
        )

        recipients_str = recipients_to_str(recipients)
        cc_recipients_str = recipients_to_str(cc_recipients)

        self.message = self._construct_base_message(
            recipients=recipients_str,
            subject=subject,
            cc_recipients=cc_recipients_str,
            reply_to=reply_to,
        )

        html_content = make_html_content(
            html_content,
            template,
            template_directory,
            **kwargs,
        )

        self._make_plain_message(html_content)
        self._make_html_message(html_content, alter_img_src)
        self._add_attachments(attachments)

        return self._send_message(all_recipients)
