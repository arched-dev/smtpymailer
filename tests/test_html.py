import os
import unittest
from unittest import mock
from jinja2 import Environment, FileSystemLoader
import datetime
import smtpymailer.html


class TestRenderHtmlTemplate(unittest.TestCase):
    @mock.patch("smtpy_mailer.html.create_jinja_environment")
    @mock.patch("smtpy_mailer.html.os.path.split")
    def test_render_html_template(self, mock_split, mock_create_environment):
        # Arrange
        template_name = "test.html"
        full_path = os.path.abspath(template_name)
        template_path = "/path/to/template"
        template_content = "<h1>{{ title }}</h1>"
        expected_html = "<h1>Test Title</h1>"
        mock_split.return_value = [template_path, template_name]
        mock_environment = mock.MagicMock(spec=Environment)
        mock_template = mock_environment.get_template.return_value
        mock_template.render.return_value = expected_html
        mock_create_environment.return_value = mock_environment

        # Act
        result = smtpymailer.html.render_html_template(
            f"{{template_path}}/{template_name}", title="Test Title"
        )

        # Assert
        mock_split.assert_called_once_with(
            os.path.abspath(f"{template_path}/{template_name}")
        )
        mock_create_environment.assert_called_once_with([template_path])
        mock_environment.get_template.assert_called_once_with(f"{template_name}.html")
        mock_template.render.assert_called_once_with(
            dated=datetime.datetime.now(), title="Test Title"
        )
        self.assertEqual(expected_html, result)


if __name__ == "__main__":
    unittest.main()
