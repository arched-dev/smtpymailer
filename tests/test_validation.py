import socket
import unittest
from smtpymailer.validation import (
    validate_user_email,
    validate_dmarc_record,
    is_ip_in_network,
    resolve_domain,
    get_address_type,
    validate_dkim_record,
    spf_check,
)


class TestValidation(unittest.TestCase):
    def test_validate_user_email_return_normalized_true(self):
        result = validate_user_email(
            "test@EXAMPLE.com", return_normalized=True, check_deliverability=False
        )
        self.assertEqual(result, "test@example.com")

    def test_validate_user_email_return_normalized_false(self):
        result = validate_user_email(
            "test@EXAMPLE.com", return_normalized=False, check_deliverability=False
        )
        self.assertEqual(result, "test@EXAMPLE.com")

    def test_validate_user_email_invalid_email(self):
        with self.assertRaises(Exception):  # Depending on the expected exception
            validate_user_email(
                "invalid_email", return_normalized=False, check_deliverability=False
            )

    def test_validate_dmarc_record_valid(self):
        valid_dmarc_record = (
            "v=DMARC1; p=none; rua=mailto:abc@example.com; pct=100; fo=1;"
        )
        self.assertIsNotNone(validate_dmarc_record(valid_dmarc_record))

    def test_validate_dmarc_record_invalid(self):
        invalid_dmarc_record = "This is invalid dmarc record"
        with self.assertRaises(ValueError):
            validate_dmarc_record(invalid_dmarc_record)

    def test_validate_dmarc_record_invalid_two(self):
        invalid_dmarc_record = (
            "v=SPF; p=none; rua=mailto:abc@example.com; pct=100; fo=1;"
        )
        with self.assertRaises(ValueError):
            validate_dmarc_record(invalid_dmarc_record)

    def test_validate_dmarc_record_pct_value_out_of_range(self):
        invalid_dmarc_record = (
            "v=DMARC1; p=none; rua=mailto:abc@example.com; pct=200; fo=1;"
        )
        with self.assertRaises(ValueError):
            validate_dmarc_record(invalid_dmarc_record)

    def test_validate_dmarc_regex_error(self):
        invalid_dmarc_record = "v=DMARC1; p=reject; rua=mailto:this_is_not_an_email; ruf=mailto:another_invalid_email@; pct=100"

        with self.assertRaises(ValueError):
            validate_dmarc_record(invalid_dmarc_record)

    def test_validate_dmarc_invalid_email(self):
        invalid_dmarc_record = "v=DMARC1; p=none; rua=mailto:abc; pct=200; fo=1;"
        with self.assertRaises(ValueError):
            validate_dmarc_record(invalid_dmarc_record)

    def test_valid_ipv4_in_network(self):
        self.assertTrue(is_ip_in_network("192.168.1.1", "192.168.1.0/24"))

    def test_valid_ipv4_outside_network(self):
        self.assertFalse(is_ip_in_network("192.168.2.1", "192.168.1.0/24"))

    def test_valid_ipv6_in_network(self):
        self.assertTrue(
            is_ip_in_network(
                "2001:0db8:85a3:0000:0000:8a2e:0370:7334", "2001:0db8::/32"
            )
        )

    def test_invalid_ip(self):
        with self.assertRaises(ValueError):
            is_ip_in_network("not-a-valid-ip", "192.168.1.0/24")

    def test_invalid_network(self):
        with self.assertRaises(ValueError):
            is_ip_in_network("192.168.1.1", "not-a-valid-network")

    def test_empty_string_ip(self):
        with self.assertRaises(ValueError):
            is_ip_in_network("", "192.168.1.0/24")

    def test_empty_string_network(self):
        with self.assertRaises(ValueError):
            is_ip_in_network("192.168.1.1", "")

    def test_ipv4(self):
        # This test checks if IPv4 address is returning as expected
        ipv4, ipv6 = resolve_domain("www.google.com")
        self.assertTrue(all(isinstance(ip, str) for ip in ipv4))
        self.assertTrue(all(ip.count(".") == 3 for ip in ipv4))

    def test_ipv6(self):
        # This test checks if IPv6 address is returning as expected
        ipv4, ipv6 = resolve_domain("www.google.com")
        self.assertTrue(all(isinstance(ip, str) for ip in ipv6))
        self.assertTrue(all(ip.count(":") > 0 for ip in ipv6))

    def test_invalid_domain(self):
        # This test checks if the function raises the appropriate exception for invalid domains
        with self.assertRaises(socket.gaierror):
            ipv4, ipv6 = resolve_domain("invalid.domain")

    def test_ipv4_address(self):
        address = "192.0.2.0"
        expected_result = {"ipv4": address}
        self.assertEqual(get_address_type(address), expected_result)

    def test_ipv6_address(self):
        address = "2001:db8::"
        expected_result = {"ipv6": address}
        self.assertEqual(get_address_type(address), expected_result)

    def test_domain_name(self):
        address = "example.com"
        expected_result = {"domain": address}
        self.assertEqual(get_address_type(address), expected_result)

    def test_invalid_input(self):
        address = "invalid"
        expected_result = {"invalid": address}
        self.assertEqual(get_address_type(address), expected_result)

    def test_validate_dkim_record_valid(self):
        valid_dkim_record = "v=DKIM1; h=sha256; k=rsa; p=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAzgLBsMFlJoX5XRcgT7T/"
        self.assertEqual(
            validate_dkim_record(valid_dkim_record), True
        )  # change expected output

    def test_validate_dkim_record_invalid(self):
        invalid_dkim_record = "invalid_dkim_record"
        self.assertEqual(validate_dkim_record(invalid_dkim_record), False)

    def test_validate_dkim_record_empty(self):
        empty_dkim_record = ""
        self.assertEqual(validate_dkim_record(empty_dkim_record), False)

    #  Test valid IPv6 address in network
    def test_valid_ipv6_in_network_attempt(self):
        ip = "2001:0db8:85a3:0000:0000:8a2e:0370:7334"
        network = "2001:0db8::/32"

        result = is_ip_in_network(ip, network)
        self.assertTrue(result)

    #  Test valid IPv6 address outside network
    def test_valid_ipv6_outside_network(self):
        ip = "2001:0db8:abcd:ef01:0000:0000:0000:0001"
        network = "2001:0db8:abcd:ef02::/64"

        result = is_ip_in_network(ip, network)
        self.assertFalse(result)

    #  Test invalid type raises TypeError
    def test_invalid_type(self):
        with self.assertRaises(TypeError):
            is_ip_in_network(1, 1)


class TestSpfCheck(unittest.TestCase):
    #  Check if an IP address is authorized by the SPF record.
    def test_ip_address_authorized(self):
        spf_record = "v=spf1 ip4:192.0.2.0/24 -all"
        ip_address = "192.0.2.1"
        result = spf_check(spf_record, ipv4=ip_address)
        self.assertTrue(result)

    #  Check if a domain is authorized by the SPF record.
    def test_domain_authorized(self):
        spf_record = "v=spf1 include:example.com -all"
        domain = "example.com"
        result = spf_check(spf_record, domain=domain)
        self.assertTrue(result)

    #  Check if an IPv4 address is authorized by the SPF record.
    def test_ipv4_address_authorized(self):
        spf_record = "v=spf1 ip4:192.0.2.0/24 -all"
        ipv4_address = "192.0.2.1"
        result = spf_check(spf_record, ipv4=ipv4_address)
        self.assertTrue(result)

    #  Test domain fail
    def test_domain_fail(self):
        spf_record = "v=spf1 include:example.com -all"
        result = spf_check(spf_record=spf_record, domain="yourdomain.com")
        self.assertFalse(result)

    #  Test domain pass
    def test_domain_pass(self):
        spf_record = "v=spf1 include:example.com -all"
        result = spf_check(spf_record=spf_record, domain="example.com")
        self.assertTrue(result)

    #  Check if an invalid SPF record raises a ValueError.
    def test_invalid_spf_record(self):
        spf_record = "invalid_spf_record"
        with self.assertRaises(ValueError):
            spf_check(spf_record)

    #  Check if an invalid IP address returns False.
    def test_invalid_ip_address(self):
        spf_record = "v=spf1 ip4:192.0.2.0/24 -all"
        ipv4_address = "invalid_ip_address"
        with self.assertRaises(ValueError):
            spf_check(spf_record, ipv4=ipv4_address)

    #  Check if an invalid network returns False.
    def test_invalid_network(self):
        spf_record = "v=spf1 ip4:192.0.2.0/24 -all"
        ipv4_address = "195.0.2.1"
        result = spf_check(spf_record, ipv4=ipv4_address)
        self.assertFalse(result)

    def test_spf_check_with_ipv6(self):
        spf_record = "v=spf1 ip6:2001:0db8::/32 -all"
        ipv6_address = "2001:0db8::1234"
        # This should return True as the ipv6 address is within the specified range
        self.assertTrue(spf_check(spf_record, ipv6=ipv6_address))

        ipv6_address_outside = "2001:0db9::1234"
        # This should return False as the ipv6 address is outside the specified range
        self.assertFalse(spf_check(spf_record, ipv6=ipv6_address_outside))


if __name__ == "__main__":
    unittest.main()
