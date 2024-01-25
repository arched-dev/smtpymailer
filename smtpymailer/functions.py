import binascii

import dns
from bs4 import BeautifulSoup
from email_validator import validate_email
import dns.resolver
import ipaddress
from typing import Optional
import re
import base64


def validate_dkim_record(dkim_record):
    # Regular expression to validate DKIM record
    dkim_regex = re.compile(
        r"v=DKIM1;(\s*h=sha(1|256);)?(\s*k=rsa;)?(\s*t=[\w/]+;)?(\s*p=[A-Za-z0-9+/]+={0,2})"
    )

    # Remove quotes and spaces from the record for validation
    dkim_record = dkim_record.replace('"', "").strip()

    # Matching the record with the regex
    match = dkim_regex.fullmatch(dkim_record)
    if not match:
        return False

    # Extract and decode the public key
    public_key_encoded = match.group(5)[3:]  # Remove 'p='
    try:
        return base64.b64decode(public_key_encoded)

    except binascii.Error:
        return False


def is_ip_in_network(ip, network):
    """
    Args:
        ip: str, representing the IP address to be checked.
        network: str, representing the network address to be checked against.

    Returns:
        bool, indicating whether the given IP address is within the specified network.

    Example:
        >>> is_ip_in_network('192.168.1.10', '192.168.1.0/24')
        True

    Note:
        This method uses the ipaddress module to perform the IP address and network comparisons.

    """
    return ipaddress.ip_address(ip) in ipaddress.ip_network(network)


def spf_check(
    spf_record: str,
    ipv4: Optional[str] = None,
    ipv6: Optional[str] = None,
    domain: Optional[str] = None,
):
    """
    Args:
        spf_record (str): The SPF record to check.
        ipv4 (Optional[str]): The IPv4 address to check. Default is None.
        ipv6 (Optional[str]): The IPv6 address to check. Default is None.
        domain (Optional[str]): The domain to check. Default is None.

    Returns:
        bool: True if the IP or domain is authorized by the SPF record, False otherwise.

    Raises:
        ValueError: If the SPF record is invalid.

    """
    # Remove quotes and strip whitespace
    spf_record = spf_record.strip('"').strip()

    # Split the SPF record into parts
    parts = spf_record.split()

    # Check if the SPF record is valid
    if not parts or parts[0] != "v=spf1":
        raise ValueError("Invalid SPF record")

    # Check each part of the SPF record
    for part in parts[1:]:
        if part.startswith("include:"):
            included_domain = part.split(":")[1]
            if domain == included_domain:
                return True
            try:
                answers = dns.resolver.resolve(included_domain, "TXT")
                for rdata in answers:
                    if spf_check(str(rdata), ipv4, ipv6, domain):
                        return True
            except Exception as e:
                print(f"DNS query failed: {e}")

        elif part.startswith("ip4:"):
            network = part.split(":")[1]
            if ipv4 and is_ip_in_network(ipv4, network):
                return True

        elif part.startswith("ip6:"):
            network = part.split(":")[1]
            if ipv6 and is_ip_in_network(ipv6, network):
                return True

    # Check the -all mechanism
    if "-all" in parts:
        return False  # The IP or domain is not authorized

    return True  # The SPF record does not explicitly disallow the IP or domain


def validate_dmarc_record(record):
    """
    Args:
        record: A string containing the DMARC record to be validated.

    Returns:
        A Match object if the given record is a valid DMARC record, or None if it does not match the DMARC record format.
    """
    # Regular expression to validate DMARC record
    dmarc_regex = re.compile(
        r"v=DMARC1;(\s*p=[\w]+;)?(\s*rua=mailto:[^;]+;)?(\s*pct=[\d]+;)?(\s*fo=[\d];)?"
    )

    # Removing quotes and spaces from the record for validation
    record = record.replace('"', "").strip()

    # Matching the record with the regex
    return dmarc_regex.fullmatch(record)


def validate_user_email(
    email: str, return_normalized: bool = True, check_deliverability: bool = False
):
    """
    Validates a user email address.

    Args:
        email (str): The email address to be validated.
        return_normalized (bool): Specifies whether to return the normalized email or not.
                                  Default is True. If set to True, the normalized email will be returned.
        check_deliverability (bool): Specifies whether to check the deliverability of the email address or not.
                                     Default is False. If set to True, the deliverability of the email address will be checked.

    Returns:
        str: The normalized email address, if return_normalized is set to True.
        OR
        str: The original email address.

    """
    email_info = validate_email(email, check_deliverability=check_deliverability)
    return email_info.normalized if return_normalized else email


def replace_tags_with_newlines(soup: BeautifulSoup, tag: str) -> None:
    """
    Replaces specified tags in Beautiful Soup object with newlines.

    Args:
      soup: BeautifulSoup object
      tag (str): specific tag to replace

    """
    for element in soup.find_all(tag):
        element.replace_with("\n")


def convert_html_to_plain_text(html_text: str) -> str:
    """
    Creates a plain text version of an email with preserved new lines.

    Args:
      html_text (str): HTML text

    Returns:
        str: plain text version of the email with new lines
    """
    # Parse the HTML
    soup = BeautifulSoup(html_text, "html.parser")

    tags_to_replace = ["br", "p"]
    for tag in tags_to_replace:
        replace_tags_with_newlines(soup, tag)

    # Get the text
    return soup.get_text()
