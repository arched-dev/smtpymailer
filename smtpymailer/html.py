import datetime
from typing import Optional, List
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os


def create_jinja_environment(template_paths: List[str]) -> Environment:
    """Creates a Jinja2 environment.
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
    template: str, template_paths: Optional = None, extension: str = "html", **kwargs
) -> str:
    """Renders an HTML template using Jinja2.
    Args:
        template (str): The name of the template file to render.
        template_paths (Optional[List[str]]): The paths where the template file can be found. If not provided, the path of the template will be used. Defaults to None.
        extension (str): The extension of the template file. Defaults to "html".
        **kwargs: Additional keyword arguments that will be passed to the template.
    Returns:
        str: The rendered HTML content.
    """
    # If template_paths is not provided, use the path of the template
    if not template_paths:
        split_path = os.path.split(os.path.abspath(template))
        template_paths = [split_path[0]]
        template = split_path[1]
    # Create the Jinja2 environment with the specified paths
    env = create_jinja_environment(template_paths)
    # Append the extension if not present in the template name
    if not template.endswith(f".{extension}"):
        template += f".{extension}"
    # Get the template and render it with the provided keyword arguments
    template = env.get_template(template)
    html_content = template.render(dated=datetime.datetime.now(), **kwargs)
    return html_content
