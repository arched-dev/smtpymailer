import base64
import datetime
import hashlib
import os
import re
import uuid
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from io import BytesIO
from mimetypes import guess_type
from typing import Optional, List, Union
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from bs4.element import Tag
from jinja2 import Environment, FileSystemLoader, select_autoescape
import html2text
from PIL import Image


def check_data_in_html_el(html_content: str):
    """
    Check the presence of specific data attributes in HTML content

    Args:
        html_content (str): The HTML content to check.

    Returns:
        dict: A dictionary containing the count of each data attribute found.
            - "base64": The count of base64 encoded images ("data:image/jpeg;base64,").
            - "cid": The count of images with the attribute "cid:smtpymailer-image" in the source.
            - "data-smtpymailer": The count of images with the data attribute data-smtpymailer in the source.

    Example:
        >>> html_content = '<img src="data:image/jpeg;base64,abc123" /> <img src="cid:smtpymailer-image1.jpg" />'
        >>> check_data_in_html_el(html_content)
        {'base64': 1, 'cid': 1, 'data-smtpymailer': 0}
    """
    soup = BeautifulSoup(html_content, "html.parser")

    data_found = {"base64": 0, "cid": 0, "data-smtpymailer": 0}

    for img in soup.find_all("img"):
        src = img.get("src", "")
        data_found["base64"] += 1 if ";base64," in src else 0
        data_found["cid"] += 1 if "cid:smtpymailer-image" in src else 0
        data_found["data-smtpymailer"] += 1 if "data-smtpymailer" in img.attrs else 0

    return data_found


def change_image_type(element: "Tag", mime_type: str, img_data: bytes):
    """
    Optionally changes the image type of the given image data, based on data-attributes in the HTML img element.
    See Notes for more information.

    Args:
        element (Tag): The HTML img element.
        mime_type (str): The MIME type of the image.
        img_data (bytes): The image data.

    Returns:
        tuple: A tuple containing the converted image data and the converted MIME type.

    Notes:
        I found a wierd bug in gmail showing some CID inline png images as `noname` attachments, I had 4 CID
        attachments and only one was showing as `noname`. This was in the gmail preview only, not visible when the
        email was viewed.

        To fix, I converted that image into a jpg and the 'noname' attachment disappeared. There is very little online
        about this, but possible a bug in gmail.

        To use this feature, add the following data attributes to the img element:

            * data-convert="jpg" - Converts the image type if it's not already. Can be "png", "jpg", or "gif".
            * data-format="rgb" (optional): The pixel format of the image. Defaults to "RGB". Can also be "RGBA".

        i.e  <img data-convert="jpg" data-format="rgb" src="https://www.example.com/image.png"/>

    """

    if "data-convert" in element.attrs:
        convert_to_type = element.get("data-convert").lower()
        if convert_to_type not in ["png", "jpg", "gif", "jpeg"]:
            raise ValueError(
                f"Invalid value for data-convert attribute: {convert_to_type}"
            )
        pixel_format = "RGB"
        if "data-format" in element.attrs:
            pixel_format = element.get("data-format").lower()
            if pixel_format not in ["rgb", "rgba"]:
                raise ValueError(
                    f"Invalid value for data-format attribute: {pixel_format}"
                )

        _, file_format = mime_type.split("/")
        file_format = file_format.replace("jpeg", "jpg").lower()

        if convert_to_type != file_format:
            img = Image.open(BytesIO(img_data))
            with BytesIO() as img_io:
                img.convert(pixel_format.upper()).save(img_io, convert_to_type.upper())
                img_data = img_io.getvalue()  # Update img_data with JPEG data
                mime_type = f'image/{convert_to_type.lower().replace("jpg","jpeg")}'  # Update content_type to JPEG

    return img_data, mime_type


def process_img_element(
    img: Tag,
    idx: int,
    convert_to_base64: bool = False,
    email_message: MIMEMultipart = None,
):
    """
    Process and manipulate HTML img elements, converting the image to either CID attachments or base64 encoded.
    If the request fails the element is ignored and left with the original src.

    Optionally you can convert the original image type when using CID attachments. See Notes `change_image_type` for
    more information.

    Args:
        img (Tag): The HTML img element to process.
        idx (int): The index of the img element.
        convert_to_base64 (bool): Boolean indicating whether to convert the image to base64. Defaults to False.
        email_message (MIMEMultipart): An instance of the EmailMessage class. If provided, the image will be attached
            to the email message as an inline image.

    """

    src = img.get("src", "")
    content_type, _ = guess_type(src)

    if not src.startswith(("http://", "https://")):
        return

    try:
        response = requests.get(src, stream=True)
        response.raise_for_status()

    except requests.RequestException:
        # if the request fails, ignore the element and leave the original src
        return

    img_data = response.content
    img_data, content_type = change_image_type(img, content_type, img_data)

    if convert_to_base64:
        parsed_url = urlparse(src)
        img_ext = os.path.splitext(parsed_url.path)[1].lstrip(".")
        base64_data = base64.b64encode(img_data).decode("utf-8")
        img["src"] = f"data:image/{img_ext};base64,{base64_data}"
        img["data-smtpymailer"] = ""

    elif email_message is not None:
        hash_object = hashlib.md5(img_data)
        cid = hash_object.hexdigest() + f"{idx}"
        maintype, subtype = content_type.split("/")

        # Create an instance of MIMEImage
        mime_image = MIMEImage(img_data, _subtype=subtype)
        mime_image.add_header("Content-ID", f"<{cid}>")
        mime_image.add_header("Content-Disposition", "inline")

        # Attach it to the email message
        email_message.attach(mime_image)
        img["src"] = f"cid:{cid}"
        img["data-smtpymailer"] = ""


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
    Alters the HTML content of an email message by converting image elements to base64 encoding or attaching images
    as CID (Content-ID).

    This method modifies the HTML content based on the specified `alter_img_src` parameter. It either converts image
    elements in the HTML content to base64 encoding or attaches images as CID.

    Args:
        message (MIMEMultipart): The email message object to be modified.
        html_content (str): The HTML content of the email.
        alter_img_src (Optional[str]): The source of the image alteration. It can be "base64" or "cid". If None,
            no alteration is performed.

    Returns:
        str: The altered HTML content with image elements modified according to `alter_img_src`.

    Raises:
        This function does not explicitly raise any exceptions.

    Examples:
        To do nothing
        >>> alter_img_html(message, html_content)

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
    template_directory: Optional[Union[str, List[str]]] = None,
    **kwargs,
):
    """
    Adds HTML content to the email message. This function either directly uses provided HTML content or renders HTML content
    from a specified template.

    Args:
        html_content (Optional[str]): A string containing the HTML content of the email. If this is provided, the function
            will use it directly. Defaults to None.
        template (Optional[str]): A string representing the name of the template file to be used for rendering the HTML
            content. This is used if 'html_content' is not provided. Defaults to None.
        template_directory (Optional[Union[str, List[str]]]): A string or list of strings representing the directories
            to search for the template file. This is used in conjunction with 'template' to render the HTML content.
            Defaults to None.
        **kwargs: Additional keyword arguments that are passed to the template rendering function.

    Returns:
        str: The HTML content that will be used in the email. This could be the provided 'html_content' or content rendered
             from the specified template.

    """
    if not html_content:
        html_content = render_html_template(template, template_directory, **kwargs)

    return html_content
