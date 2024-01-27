import base64
import binascii
import ipaddress
import re
import socket
from typing import Optional, Union, Tuple, List

import dns.resolver
import validators
from email_validator import validate_email


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


def validate_dkim_record(dkim_record: str) -> Union[Optional[bytes], bool]:
    """
    Args:
        dkim_record: A string representing the DKIM record that needs to be validated.

    Returns:
        Union[Optional[bytes], bool]: Returns either the decoded public key as bytes or False.

    """

    dkim_regex = re.compile(
        r"v=DKIM1;(\s*h=sha(1|256);)?(\s*k=rsa;)?(\s*t=[\w/]+;)?(\s*p=[A-Za-z0-9+/]+={0,2})"
    )

    # Remove quotes and spaces from the record for validation
    dkim_record = dkim_record.replace('"', "").replace(" ", "").strip()

    # Matching the record with the regex
    match = dkim_regex.fullmatch(dkim_record)
    if not match:
        return False

    # Extract and decode the public key
    public_key_encoded = match.group(5)[2:]  # Correctly remove 'p='

    return True if base64.b64decode(public_key_encoded) else False


def get_address_type(address):
    """
    Takes a string and returns a dictionary indicating whether it's an IPv4, IPv6, or domain.

    Args:
    address (str): The address to be checked.

    Returns:
    dict: A dictionary with the address type and the address.
    """
    try:
        # Check for IPv4
        ipaddress.IPv4Address(address)
        return {"ipv4": address}
    except ipaddress.AddressValueError:
        pass

    try:
        # Check for IPv6
        ipaddress.IPv6Address(address)
        return {"ipv6": address}
    except ipaddress.AddressValueError:
        pass

    # If it's not an IP address, treat it as a domain
    if validators.domain(address):
        return {"domain": address}

    return {"invalid": address}


def resolve_domain(domain: str) -> Tuple[List[str], List[str]]:
    """
    Resolve a domain to its corresponding IP addresses.

    Args:
        domain (str): The domain name to resolve.

    Returns:
        tuple: A tuple containing two lists. The first list contains IPv4 addresses
               associated with the domain, while the second list contains IPv6 addresses.
    """
    ipv4_addresses = []
    ipv6_addresses = []

    for info in socket.getaddrinfo(domain, None):
        address = info[4][0]
        if info[0] == socket.AF_INET:
            # IPv4 address
            ipv4_addresses.append(address)
        elif info[0] == socket.AF_INET6:
            # IPv6 address
            ipv6_addresses.append(address)

    return ipv4_addresses, ipv6_addresses


def is_ip_in_network(ip: str, network: str) -> bool:
    """
    Check if an IP address is in a given network.

    Args:
        ip (str): The IP address to check.
        network (str): The network to check against.

    Returns:
        bool: True if the IP address is in the network, False otherwise.

    Raises:
        TypeError: If the IP address or network is invalid.
        ValueError: if the IP or network is not a string.

    """
    if not isinstance(ip, str) or not isinstance(network, str):
        raise TypeError("Invalid input parameters")

    try:

        ip_obj = ipaddress.ip_address(ip)
        network_obj = ipaddress.ip_interface(network).network
        return ip_obj in network_obj

    except ValueError:
        raise ValueError("Invalid IP or network")


def spf_check(
    spf_record: str,
    ipv4: Optional[Union[str, List[str]]] = None,
    ipv6: Optional[Union[str, List[str]]] = None,
    domain: Optional[str] = None,
):
    """
    Args:
        spf_record: The SPF record to be checked.
        ipv4: Optional parameter for the IPv4 addresses to be checked against the SPF record. It can be a single
            IPv4 address or a list of IPv4 addresses.
        ipv6: Optional parameter for the IPv6 addresses to be checked against the SPF record. It can be a single
            IPv6 address or a list of IPv6 addresses.
        domain: Optional parameter for the domain name to be checked against the SPF record.

    Returns:
        Returns True if the SPF record authorizes the provided IPv4 addresses, IPv6 addresses, or the domain.
        Returns False if the SPF record explicitly disallows them.

    Raises:
        ValueError: If the SPF record is invalid.

    """

    def list_fix(
        val: Union[List, str], add: Optional[Union[List, str]] = None
    ) -> Optional[List]:
        """
        Args:
            val: The input value that needs to be fixed. It can be a single value or a list of values.
            add: An optional value to be added to the input value. It can be a single value or a list of values.

        Returns:
            A list with unique elements from the input value and the additional value. If the resulting list is empty, it returns None.

        Example Usage:
            val = [1, 2, 3]
            add = [2, 3, 4, 5]
            fixed_list = list_fix(val, add)
        """
        val = [val] if not isinstance(val, list) else val
        add = [add] if add and not isinstance(add, list) else add
        val += add or []

        return_val = list(set(val))
        return return_val if return_val else []

    if (not ipv4 or not ipv6) and domain:
        _ipv4, _ipv6 = resolve_domain(domain)
        ipv4 = list_fix(_ipv4)
        ipv6 = list_fix(_ipv6)

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
                return False

        elif part.startswith("ip4:"):
            network = part.split(":")[1]
            # Convert ipv4 to a list if it's not already
            ipv4_list = [ipv4] if isinstance(ipv4, str) else ipv4
            for ipv4_address in ipv4_list:
                if ipv4_address and is_ip_in_network(ipv4_address, network):
                    return True

        elif part.startswith("ip6:"):
            network = ":".join(part.split(":")[1:])
            # Convert ipv6 to a list if it's not already
            ipv6_list = [ipv6] if isinstance(ipv6, str) else ipv6
            for ipv6_address in ipv6_list:
                if ipv6_address and is_ip_in_network(ipv6_address, network):
                    return True

    # Check the -all mechanism
    if "-all" in parts:
        return False  # The IP or domain is not authorized

def get_dmarc_record_match(record):
    """
    Clean up the record and checks if it's a match.

    Args:
        record: A string containing the DMARC record.

    Returns:
        A Match object if the record is a valid DMARC record.
        Throws ValueError if regex fullmatch fails.

    Raises:
        EmailNotValidError: If any of the email addresses in mailto: are not valid.
    """
    # Removing quotes and spaces from the record for validation
    clean_record = record.replace('"', "").strip()

    mailto_addresses = re.findall(r"mailto:([^;]+)", clean_record)
    for address in mailto_addresses:
        validate_user_email(address)

    # Regular expression to validate DMARC record
    dmarc_regex = re.compile(
        r"^v=DMARC1;\s*((p=none|p=quarantine|p=reject|rua=mailto:[^;]+|ruf=mailto:[^;]+|pct=\d{1,3}|sp=none|sp=quarantine|sp=reject|aspf=r|aspf=s|adkim=r|adkim=s|fo=[01ds]|rf=afrf|rf=iodef|ri=\d+);?\s*)*\s*$",
        re.IGNORECASE,
    )
    return dmarc_regex.fullmatch(clean_record)


def validate_dmarc_record(record):
    """
    Validates a DMARC record.

    Args:
        record: A string containing the DMARC record.

    Returns:
        A Match object if the record is a valid DMARC record.
        Throws ValueError if the record is not a valid DMARC record.
    """
    # Check if record is a string
    assert isinstance(record, str), "The record must be a string."

    # Clean up and match the record
    record_match = get_dmarc_record_match(record)

    # Check pct value if exists
    if record_match:
        pct_match = re.search(r"pct=(\d{1,3})", record)
        if pct_match:
            pct_value = int(pct_match.group(1))
            if pct_value < 0 or pct_value > 100:
                raise ValueError("The pct value must be between 0 and 100.")
    else:
        raise ValueError("The record is not a valid DMARC record.")

    return True if record_match else False
