import hashlib
import os
import unittest
from email.mime.multipart import MIMEMultipart
from unittest import mock
import smtpymailer.html_parse
from smtpymailer.utils import find_project_root
from smtpymailer.html_parse import (
    attach_images_as_cid,
    convert_img_elements_to_base64,
    check_data_in_html_el,
    alter_img_html,
    make_html_content,
)


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
    def attach_images_as_cid_helper(
        self, images, html_content=None, fake_content=None, fake_content_match=None
    ):
        if fake_content is None:
            fake_content = b"fake image content"
        if not fake_content_match:
            fake_content_match = fake_content

        with mock.patch("requests.get") as mock_get:
            # Set up the mock response
            mock_response = mock.Mock()
            mock_response.content = fake_content
            mock_response.raise_for_status = mock.Mock()
            mock_get.return_value = mock_response

            # Call the function with a test HTML string
            if html_content is None:
                image_elements = "".join(
                    ['<img src="https://example.com/image.jpg">'] * images
                )
                html_content = f"<html><body>{image_elements}</body></html>"

            msg = MIMEMultipart()
            result = attach_images_as_cid(html_content, msg)

            mock_get.assert_called_with("https://example.com/image.jpg", stream=True)

            cid_hash = hashlib.md5(fake_content_match).hexdigest()
            for i in range(images):
                self.assertIn(f"cid:{cid_hash}{i}", result)

            # Check the number of attachments
            self.assertEqual(len(msg.get_payload()), images)

            # Inspect the attachments
            image_numbers = [i for i in range(images)]
            imgno = 0
            for part in msg.walk():
                if part.get_content_maintype() == "image":
                    # Verify the Content-ID
                    self.assertIn(int(imgno), image_numbers)
                    # Verify the Content-Disposition
                    self.assertEqual(part.get("Content-Disposition"), "inline")
                    # Optionally, verify the image data
                    self.assertEqual(part.get_payload(decode=True), fake_content_match)
                    imgno += 1

            return result

    def test_attach_single_image_as_cid(self):
        self.attach_images_as_cid_helper(images=1)

    def test_attach_ten_images_as_cid(self):
        self.attach_images_as_cid_helper(images=10)

    def test_convert_cid_image_different_type(self):
        with open("./tests/assets/1px.png", "rb") as file:
            png_content = file.read()

        with open("./tests/assets/1px.jpg", "rb") as file:
            jpg_content = file.read()

        html_content = '<html><body><img data-convert="png" data-format="RGB" src="https://example.com/image.jpg"></body></html>'
        self.attach_images_as_cid_helper(
            images=1,
            html_content=html_content,
            fake_content=jpg_content,
            fake_content_match=png_content,
        )

    def test_alter_img_html_with_none(self):
        msg = MIMEMultipart()
        html_content = "<html><body></body></html>"
        html_out = alter_img_html(msg, html_content)
        self.assertEqual(html_content, html_out)

    @mock.patch("requests.get")
    def test_alter_img_html_with_base(self, mock):
        # Set up the mock response
        mock_response = mock.Mock()
        mock_response.content = b"fake_img_data"
        mock_response.raise_for_status = mock.Mock()
        mock.return_value = mock_response

        msg = MIMEMultipart()
        html_content = (
            '<html><body><img src="https://example.com/image.jpg"></body></html>'
        )
        html_out = alter_img_html(msg, html_content, "cid")
        self.assertTrue("cid:" in html_out)

        html_out = alter_img_html(msg, html_content, "base64")
        self.assertTrue(";base64," in html_out)

    def test_make_html_content(self):
        html_content = "<h1>foo</h1><h2>bar</h2>"
        html_out = make_html_content(
            template="./templates/test.html", foo="foo", bar="bar"
        )
        self.assertEqual(html_content, html_out)

        html_content = "<h1>foo</h1><h2>bar</h2>"
        html_out = make_html_content(template="test.html", template_directory="./templates", foo="foo", bar="bar")
        self.assertEqual(html_content, html_out)

        html_content = "<h1>foo</h1><h2>bar</h2>"
        html_out = make_html_content(html_content=html_content)
        self.assertEqual(html_content, html_out)

        html_content = "<h1>foo</h1><h2>bar</h2>"
        html_out = make_html_content(
            template="./templates/test.html", foo="foo", bar="baz"
        )
        self.assertNotEqual(html_content, html_out)

    def test_convert_cid_image_same_type(self):
        html_content = '<html><body><img data-convert="jpg" data-format="RGB" src="https://example.com/image.jpg"></body></html>'
        self.attach_images_as_cid_helper(images=1, html_content=html_content)

    def test_fail_convert_cid_type(self):
        with self.assertRaises(ValueError):
            html_content = '<html><body><img data-convert="webp" data-format="RGB" src="https://example.com/image.jpg"></body></html>'
            self.attach_images_as_cid_helper(images=1, html_content=html_content)

    def test_fail_convert_cid_format(self):
        with self.assertRaises(ValueError):
            html_content = '<html><body><img data-convert="jpg" data-format="cmyk" src="https://example.com/image.jpg"></body></html>'
            self.attach_images_as_cid_helper(images=1, html_content=html_content)

    def test_attach_unavailable_url_cid(self):
        html_content = (
            '<html><body><img src="https://example.com/image.jpg"></body></html>'
        )
        msg = MIMEMultipart()
        result = attach_images_as_cid(html_content, msg)

        self.assertNotIn(f"cid:image0.jpg", result)

        # Check the number of attachments
        self.assertEqual(len(msg.get_payload()), 0)


class TestConvertImgElementsToBase64(unittest.TestCase):
    def convert_images_to_base64_helper(self, images):
        """
        Converts images in HTML content to base64 format.

        Args:
            images (int): The number of images to convert to base64.

        """
        with mock.patch("requests.get") as mock_get:
            # Set up the mock response
            mock_response = mock.Mock()
            mock_response.content = b"fake image content"
            mock_response.raise_for_status = mock.Mock()
            mock_get.return_value = mock_response

            # Call the function with a test HTML string
            image_elements = "".join(
                ['<img src="https://example.com/image.jpg">'] * images
            )
            html_content = f"<html><body>{image_elements}</body></html>"
            result = convert_img_elements_to_base64(html_content)

            converted_data = check_data_in_html_el(result)

            self.assertEqual(converted_data["base64"], images)
            self.assertEqual(converted_data["cid"], 0)
            self.assertEqual(converted_data["data-smtpymailer"], images)
            self.assertEqual(mock_get.call_count, images)

    def test_convert_single_image_to_base64(self):
        self.convert_images_to_base64_helper(images=1)

    def test_convert_ten_images_to_base64(self):
        self.convert_images_to_base64_helper(images=10)

    def test_attach_unavailable_url_base64(self):
        html_content = (
            '<html><body><img src="https://example.com/image.jpg"></body></html>'
        )
        result = convert_img_elements_to_base64(html_content)

        converted_data = check_data_in_html_el(result)

        self.assertEqual(converted_data["base64"], 0)
        self.assertEqual(converted_data["cid"], 0)
        self.assertEqual(converted_data["data-smtpymailer"], 0)

    def test_attach_invalid_url_base64(self):
        html_content = '<html><body><img src="example.com/image.jpg"></body></html>'
        result = convert_img_elements_to_base64(html_content)

        converted_data = check_data_in_html_el(result)

        self.assertEqual(converted_data["base64"], 0)
        self.assertEqual(converted_data["cid"], 0)
        self.assertEqual(converted_data["data-smtpymailer"], 0)


if __name__ == "__main__":
    unittest.main()
