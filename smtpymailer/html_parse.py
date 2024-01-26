import base64
import datetime
import os
import re
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from typing import Optional, List
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from bs4.element import Tag
from jinja2 import Environment, FileSystemLoader, select_autoescape
import html2text


def process_img_element(
    img: Tag,
    idx: int,
    convert_to_base64: bool = False,
    email_message: MIMEMultipart = None,
):
    """
    Process and manipulate HTML img elements, if the request fails the element is ignored and left with the
    original src.

    Args:
        img (Tag): The HTML img element to process.
        idx (int): The index of the img element.
        convert_to_base64 (bool): Boolean indicating whether to convert the image to base64. Defaults to False.
        email_message (MIMEMultipart): An instance of the EmailMessage class. If provided, the image will be attached
            to the email message as an inline image.

    """

    src = img.get("src", "")
    if not src.startswith(("http://", "https://")):
        return

    try:
        response = requests.get(src, stream=True)
        response.raise_for_status()

    except requests.RequestException:
        #if the request fails, ignore the element and leave the original src
        return

    img_data = response.content
    parsed_url = urlparse(src)
    img_ext = os.path.splitext(parsed_url.path)[1].lstrip(".")
    image_content_types = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "svg": "image/svg+xml",
        "bmp": "image/bmp",
        "webp": "image/webp",
    }

    content_type = image_content_types.get(img_ext, "image/jpeg")

    if convert_to_base64:
        base64_data = base64.b64encode(img_data).decode("utf-8")
        img["src"] = f"data:image/{img_ext};base64,{base64_data}"

    elif email_message is not None:
        cid = f"image{idx}.{img_ext}"
        maintype, subtype = content_type.split("/")

        # Create an instance of MIMEImage
        mime_image = MIMEImage(img_data, _subtype=subtype)
        mime_image.add_header("Content-ID", f"<{cid}>")
        mime_image.add_header("Content-Disposition", "inline")

        # Attach it to the email message
        email_message.attach(mime_image)
        img["src"] = f"cid:{cid}"


def convert_img_elements_to_base64(html_content: str) -> str:
    """
    Converts all img elements in the given HTML content to base64.

    Args:
        html_content (str): The HTML content containing img elements.

    Returns:
        str: The modified HTML content with img elements converted to base64.

    """
    soup = BeautifulSoup(html_content, "html.parser")
    for idx, img in enumerate(soup.find_all("img")):
        process_img_element(img, idx, convert_to_base64=True)
    return str(soup)


def attach_images_as_cid(html_content: str, msg: MIMEMultipart) -> str:
    """
    Attach images as CID to the HTML email content.

    Args:
        html_content (str): The HTML content of the email.
        msg (EmailMessage): The email message object to attach the images to.

    Returns:
        str: The modified HTML content with attached CID images.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    for idx, img in enumerate(soup.find_all("img")):
        process_img_element(img, idx, email_message=msg)
    return str(soup)


def convert_html_to_plain_text(html_text: str) -> str:
    """
    Converts HTML text to plain text, ignoring images, links, and markdown-style headers,
    and removing excess whitespace.

    Args:
      html_text (str): HTML text

    Returns:
        str: plain text version of the email
    """

    # Create a html2text object
    h = html2text.HTML2Text()

    # Configure html2text
    h.ignore_images = True
    h.ignore_links = True
    h.strong_mark = ""
    h.ul_item_mark = ""
    h.emphasis_mark = ""

    # Convert HTML to plain text
    plain_text = h.handle(html_text)

    # Remove markdown header symbols
    plain_text = re.sub(r"#+ ", "", plain_text)

    # Remove extra whitespace/newlines after paragraph breaks
    plain_text = re.sub(r"\n\s*\n", "\n\n", plain_text)

    return plain_text.strip()


def create_jinja_environment(template_paths: List[str]) -> Environment:
    """
    Creates a Jinja2 environment.

    Args:
        template_paths (List[str]): List of paths where the templates can be found.

    Returns:
        Environment: The Jinja2 Environment object.
    """
    return Environment(
        loader=FileSystemLoader(template_paths),
        autoescape=select_autoescape(["html", "xml"]),
    )


def render_html_template(
    template: str,
    template_paths: Optional[List[str]] = None,
    extension: str = "html",
    **kwargs,
) -> str:
    """
    Renders an HTML template using Jinja2.

    This function takes the name of an HTML template and optional paths where the template can be found.
    It then renders the template into HTML content. Additional context for rendering can be provided
    through keyword arguments.

    Args:
        template (str): The name of the template file to render.
        template_paths (Optional[List[str]], optional): A list of paths where the template files are located.
            If None, a default path is used. Defaults to None.
        extension (str, optional): The file extension of the template file. Defaults to "html".
        **kwargs: Arbitrary keyword arguments that provide context for the template rendering.
            These arguments are passed directly to the Jinja2 template.

    Returns:
        str: The rendered HTML content as a string.

    Examples:
        Render a simple template without additional paths or context:
        >>> render_html_template('my_template')

        Render a template with additional paths and context:
        >>> render_html_template('my_template', template_paths=['/path/to/templates'], username='Alice')
    """

    # If template_paths is not provided, use the path of the template

    if not template_paths:
        split_path = os.path.split(os.path.abspath(template))
        template_paths = [split_path[0]]
        template = split_path[1]
    # Create the Jinja2 environment with the specified paths
    env = create_jinja_environment(template_paths)
    # Get the template and render it with the provided keyword arguments
    template = env.get_template(template)
    html_content = template.render(dated=datetime.datetime.now(), **kwargs)
    return html_content


def alter_img_html(message, html_content, alter_img_src: Optional = None):
    """
    Alters the HTML content of an email message by converting image elements to base64 encoding or attaching images as CID (Content-ID).

    This method modifies the HTML content based on the specified `alter_img_src` parameter. It either converts image elements in the HTML content to base64 encoding or attaches images as CID.

    Args:
        message (EmailMessage): The email message object to be modified.
        html_content (str): The HTML content of the email.
        alter_img_src (Optional[str]): The source of the image alteration. It can be "base64" or "cid". If None, no alteration is performed.

    Returns:
        str: The altered HTML content with image elements modified according to `alter_img_src`.

    Raises:
        This function does not explicitly raise any exceptions.

    Examples:
        To convert image elements in HTML content to base64 encoding:
        >>> alter_img_html(message, html_content, alter_img_src="base64")

        To attach images in HTML content as CID:
        >>> alter_img_html(message, html_content, alter_img_src="cid")
    """

    if alter_img_src:
        if alter_img_src.lower() == "base64":
            html_content = convert_img_elements_to_base64(html_content)
        elif alter_img_src.lower() == "cid":
            html_content = attach_images_as_cid(html_content, message)

    return html_content


def make_html_content(
    html_content: Optional[str] = None,
    template: Optional[str] = None,
    template_directory: Optional[List[str]] = None,
    **kwargs,
):
    """
    Adds HTML content to the email message.

    Args:
        html_content: Optional string containing the HTML content of the email. Defaults to None.
        template: Optional string representing the template to be used for rendering the HTML content. Defaults to None.
        template_directory: Optional list of strings representing the directories to search for the template file.
            Defaults to None.
        **kwargs: Additional keyword arguments that can be passed to the template rendering function.

    Returns:
        The modified message object with the HTML content added.

    """
    if not html_content:
        html_content = render_html_template(template, template_directory, **kwargs)

    return html_content
