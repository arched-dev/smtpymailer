import os
import random
import string
import unittest
from time import sleep
from typing import Optional

from dotenv import load_dotenv
from email_validator import EmailNotValidError
from mailinator import Mailinator, GetInboxRequest, GetMessageRequest

from smtpymailer.mailer import Contact, validate_send_email, SmtpMailer
from smtpymailer.utils import find_project_root


class TestContact(unittest.TestCase):
    def test_init_valid_email(self):
        """Test initializing a contact with a valid email."""
        contact = Contact("johndoe@example.com", "John Doe")
        self.assertEqual(contact.email, "johndoe@example.com")
        self.assertEqual(contact.name, "John Doe")


    def test_init_invalid_email(self):
        """Test initializing a contact with an invalid email."""
        with self.assertRaises(EmailNotValidError):
            contact = Contact("not a valid email", "John Doe")

    def test_repr_with_name(self):
        """Test the __repr__() method when name is present."""
        contact = Contact("johndoe@example.com", "John Doe", False)
        self.assertEqual(repr(contact), "John Doe <johndoe@example.com>")

    def test_repr_without_name(self):
        """Test the __repr__() method when name is not present."""
        contact = Contact("johndoe@example.com", None, False)
        self.assertEqual(repr(contact), "johndoe@example.com")

    def test_get_domain(self):
        """Test the get_domain() method."""
        contact = Contact("johndoe@example.com", "John Doe", False)
        self.assertEqual(contact.get_domain(), "example.com")


class TestValidateSendEmail(unittest.TestCase):
    recipient_domain = "team829298.testinator.com"
    email_subject = "My test email - "

    def setUp(self):
        root = find_project_root(file_path=__file__)
        load_dotenv(root.joinpath(".env"))

        # This method will run before each test
        self.root = find_project_root()
        self.assertIsNotNone(self.root, "Project root not found")

        self.template_path = os.path.join(self.root, "tests/templates")
        self.template_file = "test_real_email.html"
        self.full_template_path = os.path.join(self.template_path, self.template_file)
        self.html_content = "<html><body><h1>Test</h1><p>This is a test email with a unique id of $$ </p></body></html>"
        self.unique_id = "".join(random.choice(string.ascii_letters) for _ in range(10))
        self.unique_id_two = "".join(
            random.choice(string.ascii_letters) for _ in range(10)
        )
        self.unique_id_three = "".join(
            random.choice(string.ascii_letters) for _ in range(10)
        )
        self.attachments = ["./tests/assets/dog.pdf"]

    # Generate the random string

    def test_no_content_and_no_template(self):
        with self.assertRaises(ValueError):
            validate_send_email(None, None, None, "Subject", ["recipient@mail.com"])

    def test_no_subject(self):
        with self.assertRaises(ValueError):
            validate_send_email(
                "HTML content", None, None, None, ["recipient@mail.com"]
            )

    def test_no_recipients(self):
        with self.assertRaises(ValueError):
            validate_send_email("HTML content", None, None, "Subject", [])

    def test_invalid_recipients_email(self):
        with self.assertRaises(TypeError):
            validate_send_email(
                "HTML content",
                None,
                None,
                "Subject",
            )

    # Assuming is_file_with_path will return False
    def test_template_no_directory(self):
        with self.assertRaises(FileNotFoundError):
            validate_send_email(
                None, "template.txt", None, "Subject", ["recipient@mail.com"]
            )

    def test_valid(self):
        # Assuming all the inputs are valid, the test will pass if no Exceptions are raised
        validate_send_email(
            "HTML content", None, None, "Subject", ["recipient@mail.com"]
        )

    def test_template_with_list_of_paths(self):
        """Test validate_send_email with relative template file and list of template paths."""
        try:
            validate_send_email(
                None,
                self.template_file,
                [self.template_path, self.template_path],
                "Subject",
                ["recipient@mail.com"],
            )
        except Exception as e:
            self.fail(
                f"Test failed with relative template file and list of template paths: {e}"
            )

    def test_template_with_absolute_path(self):
        """Test validate_send_email with absolute template file path."""
        try:
            validate_send_email(
                None, self.full_template_path, None, "Subject", ["recipient@mail.com"]
            )
        except Exception as e:
            self.fail(f"Test failed with absolute template file path: {e}")

    def check_inbox_for_email(self, find_id: Optional[str] = None):
        """Checks the email inbox for a specific email.

        This method makes use of the Mailinator API to check the email inbox for a specific email. It uses the unique ID and recipient domain to filter the email messages. The method will make
        * multiple attempts with an increasing time wait interval to retrieve the email message.

        Parameters:
        - self: The instance of the class calling this method.
        - find_id: The unique ID to check for in the email subject. Optional. If not provided, the method will use the
            unique ID of the class instance.

        Returns:
        - If the email is found, the method returns the email message.
        - If the email is not found within the given number of attempts, the method returns None.

        Example usage:
        ```python
        email = check_inbox_for_email()
        if email is not None:
            print(email)
        ```
        """
        mailinator = Mailinator(os.getenv("MAILINATOR_API_KEY"))

        if find_id is None:
            find_id = self.unique_id

        time_wait = 2
        for i in range(0, 5):
            sleep(2)
            inbox = mailinator.request(
                GetInboxRequest(domain=self.recipient_domain, inbox=find_id, limit=5)
            )
            for message in inbox.msgs:
                # the id of the subject always remains the same
                if self.unique_id in message.subject:
                    return mailinator.request(
                        GetMessageRequest(
                            domain=self.recipient_domain,
                            inbox=find_id,
                            message_id=message.id,
                        )
                    )
            time_wait *= 2
        return None

    def send_test_email(self, **kwargs):
        """
        Sends a test email.

        Args:
            **kwargs: Additional keyword arguments to be passed to the `send_email` method.

        """
        mailer = SmtpMailer(os.getenv("MAIL_SENDER"), os.getenv("MAIL_SENDER_NAME"), **kwargs)
        return mailer.send_email(**kwargs)

    def check_for_id_in_message(self, message):
        """
        Checks if the given unique ID is found in the message text or HTML body.

        Args:
            self: The class instance.
            message: The message to check for the unique ID.

        Returns:
            A tuple with two boolean values indicating whether the unique ID was found in the text body
            and in the HTML body, respectively.
        """
        txt_body_found_id = False
        html_message_found_id = False
        for part in message.parts:
            if "text/plain" in part.headers.get("content-type"):
                if self.unique_id in part.body:
                    txt_body_found_id = True
            elif "text/html" in part.headers.get("content-type"):
                if self.unique_id in part.body:
                    html_message_found_id = True

        return txt_body_found_id, html_message_found_id

    def check_for_attachment_in_message(self, message, filepath, content_type):
        """
        Checks if the given unique ID is found in the message text or HTML body.

        Args:
            self: The class instance.
            message: The message to check for the unique ID.

        Returns:
            A tuple with two boolean values indicating whether the unique ID was found in the text body
            and in the HTML body, respectively.
        """
        file_name = os.path.basename(filepath)

        for part in message.parts:
            email_content_disposition = part.headers.get("content-disposition")
            email_content_type = part.headers.get("content-type")
            try:
                if (
                    file_name in email_content_disposition
                    and content_type == email_content_type
                ):
                    return True
            except TypeError:
                pass

    def test_send_email_with_html_text_to_one_recipient(self):
        """Test validate_send_email with html text."""

        email_kwargs = {
            "recipients": f"{self.unique_id}@{self.recipient_domain}",
            "subject": f"{self.email_subject}{self.unique_id}",
            "html_content": self.html_content.replace("$$", self.unique_id),
        }

        result = self.send_test_email(**email_kwargs)
        self.assertTrue(result, "Failed to send email")

        message = self.check_inbox_for_email()

        self.assertIsNotNone(message, "Email was not found in the inbox")

        txt_body_found_id, html_message_found_id = self.check_for_id_in_message(message)

        self.assertTrue(
            html_message_found_id, "Unique ID not found in the HTML body of the email"
        )
        self.assertTrue(
            txt_body_found_id, "Unique ID not found in the text body of the email"
        )

    def test_send_reply_to_in_email(self):
        """Test validate_send_email with html text."""

        email_kwargs = {
            "recipients": f"{self.unique_id}@{self.recipient_domain}",
            "reply_to": f"reply@{self.recipient_domain}",
            "subject": f"{self.email_subject}{self.unique_id}",
            "html_content": self.html_content.replace("$$", self.unique_id),
        }

        result = self.send_test_email(**email_kwargs)
        self.assertTrue(result, "Failed to send email")

        message = self.check_inbox_for_email()

        self.assertIsNotNone(message, "Email was not found in the inbox")

        txt_body_found_id, html_message_found_id = self.check_for_id_in_message(message)

        self.assertTrue(
            html_message_found_id, "Unique ID not found in the HTML body of the email"
        )
        self.assertTrue(
            txt_body_found_id, "Unique ID not found in the text body of the email"
        )

        self.assertTrue(
            f"reply@{self.recipient_domain}" == message.headers["reply-to"],
            "reply-to header not found in email",
        )

    def test_send_to_recipient_and_cc(self):
        """Test validate_send_email with html text."""

        email_kwargs = {
            "recipients": f"{self.unique_id}@{self.recipient_domain}",
            "cc_recipients": f"{self.unique_id_two}@{self.recipient_domain}",
            "subject": f"{self.email_subject}{self.unique_id}",
            "html_content": self.html_content.replace("$$", self.unique_id),
        }

        result = self.send_test_email(**email_kwargs)
        self.assertTrue(result, "Failed to send email")

        message = self.check_inbox_for_email()
        cc_message = self.check_inbox_for_email(self.unique_id_two)

        self.assertIsNotNone(message, "Email was not found in the inbox")
        self.assertIsNotNone(
            cc_message, "Email was not found in the Cc addresses inbox"
        )

        txt_body_found_id, html_message_found_id = self.check_for_id_in_message(message)

        self.assertTrue(
            html_message_found_id, "Unique ID not found in the HTML body of the email"
        )
        self.assertTrue(
            txt_body_found_id, "Unique ID not found in the text body of the email"
        )

    def test_send_to_recipient_with_template(self):
        """Test validate_send_email with template and jinja variables."""

        email_kwargs = {
            "recipients": f"{self.unique_id}@{self.recipient_domain}",
            "subject": f"{self.email_subject}{self.unique_id}",
            "template": self.full_template_path,
            "unique_id": self.unique_id,
        }

        result = self.send_test_email(**email_kwargs)
        self.assertTrue(result, "Failed to send email")

        message = self.check_inbox_for_email()

        self.assertIsNotNone(message, "Email was not found in the inbox")

        txt_body_found_id, html_message_found_id = self.check_for_id_in_message(message)

        self.assertTrue(
            html_message_found_id, "Unique ID not found in the HTML body of the email"
        )
        self.assertTrue(
            txt_body_found_id, "Unique ID not found in the text body of the email"
        )

    def test_send_to_recipient_with_attachment(self):
        """Test validate_send_email with template and jinja variables."""

        email_kwargs = {
            "recipients": f"{self.unique_id}@{self.recipient_domain}",
            "subject": f"{self.email_subject}{self.unique_id}",
            "template": self.full_template_path,
            "attachments": self.attachments,
            "unique_id": self.unique_id,
        }

        result = self.send_test_email(**email_kwargs)
        self.assertTrue(result, "Failed to send email")

        message = self.check_inbox_for_email()

        self.assertIsNotNone(message, "Email was not found in the inbox")

        txt_body_found_id, html_message_found_id = self.check_for_id_in_message(message)

        self.assertTrue(
            html_message_found_id, "Unique ID not found in the HTML body of the email"
        )
        self.assertTrue(
            txt_body_found_id, "Unique ID not found in the text body of the email"
        )

        self.check_for_attachment_in_message(
            message, self.attachments[0], "application/pdf"
        )

    def test_send_to_recipient_with_invalid_attachment(self):
        """Test validate_send_email with template and jinja variables."""

        email_kwargs = {
            "recipients": f"{self.unique_id}@{self.recipient_domain}",
            "subject": f"{self.email_subject}{self.unique_id}",
            "template": self.full_template_path,
            "attachments": "./assets/invalid.pdf",
            "unique_id": self.unique_id,
        }
        with self.assertRaises(FileNotFoundError):
            self.send_test_email(**email_kwargs)

    def test_failed_to_connect(self):
        email_kwargs = {
            "recipients": f"{self.unique_id}@{self.recipient_domain}",
            "subject": f"{self.email_subject}{self.unique_id}",
            "template": self.full_template_path,
            "attachments": self.attachments,
            "unique_id": self.unique_id,
            "MAIL_SERVER": "not.a.real.server",
        }

        with self.assertRaises(ValueError):
            self.send_test_email(**email_kwargs)


if __name__ == "__main__":
    unittest.main()
