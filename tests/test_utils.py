import os
import tempfile
import unittest
from pathlib import Path

from smtpymailer.html_parse import convert_html_to_plain_text
from smtpymailer.utils import (
    is_file_with_path,
    ensure_list,
    recipients_to_str,
    convert_bool,
    find_project_root,
    build_all_recipients_and_validate,
    construct_mime_object,
)

from email_validator import EmailNotValidError
from email.mime.application import MIMEApplication
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.text import MIMEText

class TestCreateMime(unittest.TestCase):

    # Should return a MIMEImage object if the attachment is an image
    def test_image(self):
        path = os.path.abspath("./tests/assets/dog.jpg")
        with open(path, "rb") as attachment:
            part = construct_mime_object(path, attachment)

        self.assertTrue(isinstance(part, MIMEImage))

    # Should return a MIMEApplication object if the attachment is a docx file
    def test_docx(self):
        path = os.path.abspath("./tests/assets/dog.docx")
        with open(path, "rb") as attachment:
            part = construct_mime_object(path, attachment)

        self.assertTrue(isinstance(part, MIMEApplication))

    # Should return a MIMEApplication object if the attachment is a xlsx file
    def test_xlsx(self):
        path = os.path.abspath("./tests/assets/dog.xlsx")
        with open(path, "rb") as attachment:
            part = construct_mime_object(path, attachment)

        self.assertTrue(isinstance(part, MIMEApplication))

    # Should return a MIMEApplication object if the attachment is an ods file
    def test_ods(self):
        path = os.path.abspath("./tests/assets/dog.ods")
        with open(path, "rb") as attachment:
            part = construct_mime_object(path, attachment)

        self.assertTrue(isinstance(part, MIMEApplication))

    # Should return a MIMEApplication object if the attachment is an odt file
    def test_odt(self):
        path = os.path.abspath("./tests/assets/dog.odt")
        with open(path, "rb") as attachment:
            part = construct_mime_object(path, attachment)

        self.assertTrue(isinstance(part, MIMEApplication))

    # Should return a MIMEApplication object if the attachment is a pdf file
    def test_pdf(self):
        path = os.path.abspath("./tests/assets/dog.pdf")
        with open(path, "rb") as attachment:
            part = construct_mime_object(path, attachment)

        self.assertTrue(isinstance(part, MIMEApplication))

    # Should return a MIMEAudio object if the attachment is a pdf file
    def test_mp3(self):
        path = os.path.abspath("./tests/assets/dog.mp3")
        with open(path, "rb") as attachment:
            part = construct_mime_object(path, attachment)

        self.assertTrue(isinstance(part, MIMEAudio))

    # Should return a MIMEText object if the attachment is a txt file
    def test_txt(self):
        path = os.path.abspath("./tests/assets/dog.txt")
        with open(path, "rb") as attachment:
            part = construct_mime_object(path, attachment)

        self.assertTrue(isinstance(part, MIMEText))

    # Should return a MIMEApplication object if the attachment is a zip file
    def test_zip(self):
        path = os.path.abspath("./tests/assets/dog.zip")
        with open(path, "rb") as attachment:
            part = construct_mime_object(path, attachment)

        self.assertTrue(isinstance(part, MIMEApplication))

    # Should return a MIMEBase object if the attachment is a mp4 file
    def test_base(self):
        path = os.path.abspath("./tests/assets/dog.mp4")
        with open(path, "rb") as attachment:
            part = construct_mime_object(path, attachment)

        self.assertTrue(isinstance(part, MIMEBase))



class TestHtmlConversion(unittest.TestCase):
    def test_convert_html_to_plain_text(self):
        html_input = "<p>Hello,</p><p>Welcome to Python.</p><br>Enjoy learning!<br>"
        expected_output = "Hello,\n\nWelcome to Python.\n\nEnjoy learning!"
        self.assertEqual(convert_html_to_plain_text(html_input), expected_output)

    def test_convert_empty_html_to_plain_text(self):
        html_input = ""
        expected_output = ""
        self.assertEqual(convert_html_to_plain_text(html_input), expected_output)

    def test_convert_html_without_tags_to_plain_text(self):
        html_input = "Hello, Welcome to Python."
        expected_output = "Hello, Welcome to Python."
        self.assertEqual(convert_html_to_plain_text(html_input), expected_output)


class TestIsFileWithPath(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.file_path = os.path.join(self.temp_dir.name, "temp_file")

        with open(self.file_path, "w") as f:
            f.write("Dummy file")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_is_file_with_path_existing_file(self):
        self.assertTrue(
            is_file_with_path(self.file_path),
            "Expected True for existing file, got False",
        )

    def test_is_file_with_path_non_existing_file(self):
        non_existing_file = os.path.join(self.temp_dir.name, "non_existing_file")
        self.assertFalse(
            is_file_with_path(non_existing_file),
            "Expected False for non-existing file, got True",
        )


class TestEnsureList(unittest.TestCase):
    def test_ensure_list(self):
        """
        Test that `ensure_list` works as expected
        """
        # Scenario 1: Input is already a list
        lst = [1, 2, 3]
        self.assertEqual(ensure_list(lst), [1, 2, 3])

        # Scenario 2: Input is not a list
        not_lst = "string"
        self.assertEqual(ensure_list(not_lst), ["string"])

        # Scenario 3: Input is a numerical value
        num = 42
        self.assertEqual(ensure_list(num), [42])

        # Scenario 4: Input is None
        none_val = None
        self.assertEqual(ensure_list(none_val), [])

        # Scenario 5: Input is a complex type
        complex_type = {"key": "value"}
        self.assertEqual(ensure_list(complex_type), [{"key": "value"}])


class TestRecipientsToStr(unittest.TestCase):
    def test_empty_recipients(self):
        recipients = []
        expected_output = ""
        actual_output = recipients_to_str(recipients)
        self.assertEqual(actual_output, expected_output)

    def test_single_recipient(self):
        recipients = ["test@example.com"]
        expected_output = "test@example.com"
        actual_output = recipients_to_str(recipients)
        self.assertEqual(actual_output, expected_output)

    def test_multiple_recipients(self):
        recipients = ["test1@example.com", "test2@example.com", "test3@example.com"]
        expected_output = "test1@example.com, test2@example.com, test3@example.com"
        actual_output = recipients_to_str(recipients)
        self.assertEqual(actual_output, expected_output)

    def test_single_recipient_as_string(self):
        recipients = "test@example.com"
        expected_output = "test@example.com"
        actual_output = recipients_to_str(recipients)
        self.assertEqual(actual_output, expected_output)

    def test_ensure_list(self):
        recipients = "test@example.com"
        expected_output = ["test@example.com"]
        self.assertEqual(ensure_list(recipients), expected_output)


class TestConvertBool(unittest.TestCase):
    def test_convert_bool(self):
        # Test values that should return True
        true_values = ["True", "true", 1, "1", "Yes", "yes", "Y", "y", True]
        for val in true_values:
            self.assertTrue(convert_bool(val))

        # Test values that should return False
        negative_values = ["False", "2", "No", "no", "N", "n", False, "", []]
        for val in negative_values:
            self.assertFalse(convert_bool(val))

        # Test value that doesn't match either category
        self.assertFalse(convert_bool("unexpected_value"))


class TestFindProjectRoot(unittest.TestCase):
    def test_find_project_root_default(
        self,
    ):
        result = find_project_root()

        # Assert
        self.assertTrue(isinstance(result, Path))

    def test_find_project_root_custom_str_marker(self):
        # Arrange
        result = find_project_root("setup.py")
        # Assert
        self.assertTrue(isinstance(result, Path))

    def test_find_project_root_custom_list_marker(self):
        # Arrange
        result = find_project_root(["foo.bar", "setup.py"])
        # Assert
        self.assertTrue(isinstance(result, Path))

    def test_find_project_root_custom_invalid_marker(self):
        # Arrange
        result = find_project_root("foo.bar")
        # Assert
        self.assertIsNone(result)


class TestBuildAllRecipientsAndValidate(unittest.TestCase):
    #  Should return a list of all recipients after validation
    def test_with_valid_recipients(self):
        recipients = ["test1@example.com", "test2@example.com"]
        cc_recipients = ["test3@example.com"]
        bcc_recipients = ["test4@example.com"]
        expected_result = [
            "test1@example.com",
            "test2@example.com",
            "test3@example.com",
            "test4@example.com",
        ]

        result = build_all_recipients_and_validate(
            recipients, cc_recipients, bcc_recipients
        )
        self.assertEqual(result, expected_result)

    #  Should return an empty list if no recipients are provided
    def test_with_empty_recipients(self):
        recipients = []
        cc_recipients = []
        bcc_recipients = []
        expected_result = []

        with self.assertRaises(ValueError):
            build_all_recipients_and_validate(recipients, cc_recipients, bcc_recipients)

    #  Should return an  list if all recipients are None
    def test_with_none_recipients(self):
        recipients = None
        cc_recipients = None
        bcc_recipients = None

        with self.assertRaises(ValueError):
            build_all_recipients_and_validate(recipients, cc_recipients, bcc_recipients)

    #  Should raise an EmailNotValidError if any of the recipients are not valid email addresses
    def test_with_invalid_email(self):
        recipients = ["invalidemail"]
        with self.assertRaises(EmailNotValidError):
            build_all_recipients_and_validate(recipients, None, None)

    #  Should raise an EmailNotValidError if any of the CC recipients are not valid email addresses
    def test_with_invalid_cc_email(self):
        recipients = ["test1@example.com"]
        cc_recipients = ["invalidemail"]
        with self.assertRaises(EmailNotValidError):
            build_all_recipients_and_validate(recipients, cc_recipients, None)

    #  Should raise an EmailNotValidError if any of the BCC recipients are not valid email addresses
    def test_with_invalid_bcc_email(self):
        recipients = ["test1@example.com"]
        bcc_recipients = ["invalidemail"]
        with self.assertRaises(EmailNotValidError):
            build_all_recipients_and_validate(recipients, None, bcc_recipients)




if __name__ == "__main__":
    unittest.main()
