import os
import unittest
from smtpymailer.mailer import Contact, validate_send_email
from email_validator import EmailNotValidError

from smtpymailer.utils import find_project_root
from email_validator import EmailNotValidError


class TestContact(unittest.TestCase):
    def test_init_valid_email(self):
        """Test initializing a contact with a valid email."""
        try:
            contact = Contact("johndoe@example.com", "John Doe")
            self.assertEqual(contact.email, "johndoe@example.com")
            self.assertEqual(contact.name, "John Doe")
        except EmailNotValidError:
            self.fail("init() raised EmailNotValidError unexpectedly!")

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

    def setUp(self):
        # This method will run before each test
        self.root = find_project_root()
        self.assertIsNotNone(self.root, "Project root not found")

        self.template_path = os.path.join(self.root, "tests/templates")
        self.template_file = "test.html"
        self.full_template_path = os.path.join(self.template_path, self.template_file)


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



if __name__ == "__main__":
    unittest.main()
