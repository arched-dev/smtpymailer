import os
import unittest
from email.mime.multipart import MIMEMultipart

import smtpymailer.html_parse
from smtpymailer.utils import find_project_root
from smtpymailer.html_parse import attach_images_as_cid

class TestRenderHtmlTemplate(unittest.TestCase):
    def test_render_full_path_html_template(self):
        """
        Tests the rendering of a given HTML template using the full path.

        Args:
            self (object): The instance of the test class.

        Returns:
            None

        Raises:
            AssertionError: If the rendered HTML does not match the expected HTML.

        """

        template_name = "test.html"
        full_path = os.path.join(find_project_root(), "tests/templates", template_name)

        expected_html = "<h1>foo</h1><h2>bar</h2>"

        result = smtpymailer.html_parse.render_html_template(
            template=full_path, foo="foo", bar="bar"
        )

        self.assertEqual(expected_html, result)


        result = smtpymailer.html_parse.render_html_template(
            template=full_path, foo="bar", bar="foor"
        )

        self.assertNotEqual(expected_html, result)

    def test_render_name_and_template(self):
        """
        Tests the rendering of a given HTML template using the full path.

        Args:
            self (object): The instance of the test class.

        Returns:
            None

        Raises:
            AssertionError: If the rendered HTML does not match the expected HTML.

        """

        template_name = "test.html"
        template_path = os.path.join(find_project_root(), "tests/templates")
        expected_html = "<h1>foo</h1><h2>bar</h2>"

        result = smtpymailer.html_parse.render_html_template(
            template=template_name, template_paths=template_path, foo="foo", bar="bar"
        )

        self.assertEqual(expected_html, result)

        result = smtpymailer.html_parse.render_html_template(
            template=template_name, template_paths=template_path, foo="bar", bar="foo"
        )

        self.assertNotEqual(expected_html, result)


class TestAttachImagesAsCid(unittest.TestCase):

    #  Attaches images as CID to HTML email content
    def test_attach_images_as_cid_attach_images(self):
        # Test input
        html_content = '<html><body><img src="https://example.com/image1.jpg"><img src="https://example.com/image2.jpg"></body></html>'
        msg = MIMEMultipart()

        # Expected output
        expected_html_content = '<html><body><img src="cid:image0.jpg"><img src="cid:image1.jpg"></body></html>'

        # Call the function
        result = attach_images_as_cid(html_content, msg)

        # Check the result
        self.assertEqual(result, expected_html_content)

    #  Returns modified HTML content with attached CID images
    def test_attach_images_as_cid_return_modified_html_content(self):
        # Test input
        html_content = '<html><body><img src="https://example.com/image1.jpg"></body></html>'
        msg = MIMEMultipart()

        # Call the function
        result = attach_images_as_cid(html_content, msg)

        # Check the result
        self.assertIsInstance(result, str)

    #  Handles HTML content with multiple image elements
    def test_attach_images_as_cid_handles_multiple_image_elements(self):
        # Test input
        html_content = '<html><body><img src="https://example.com/image1.jpg"><img src="https://example.com/image2.jpg"></body></html>'
        msg = MIMEMultipart()

        # Call the function
        result = attach_images_as_cid(html_content, msg)

        # Check the result
        self.assertEqual(result.count("cid:"), 2)

    #  Handles HTML content with malformed image elements
    def test_attach_images_as_cid_handles_malformed_image_elements(self):
        # Test input
        html_content = '<html><body><img src="https://example.com/image1.jpg"><img></body></html>'
        msg = MIMEMultipart()

        # Call the function
        result = attach_images_as_cid(html_content, msg)

        # Check the result
        self.assertEqual(result.count("cid:"), 1)

    #  Handles HTML content with large image files
    def test_attach_images_as_cid_handles_large_image_files(self):
        # Test input
        html_content = '<html><body><img src="https://example.com/large_image.jpg"></body></html>'
        msg = MIMEMultipart()

        # Call the function
        result = attach_images_as_cid(html_content, msg)

        # Check the result
        self.assertEqual(result.count("cid:"), 1)

    #  Handles HTML content with many image elements
    def test_attach_images_as_cid_handles_many_image_elements(self):
        # Test input
        html_content = '<html><body>'
        for i in range(100):
            html_content += f'<img src="https://example.com/image{i}.jpg">'
        html_content += '</body></html>'
        msg = MIMEMultipart()

        # Call the function
        result = attach_images_as_cid(html_content, msg)

        # Check the result
        self.assertEqual(result.count("cid:"), 100)


if __name__ == "__main__":
    unittest.main()
