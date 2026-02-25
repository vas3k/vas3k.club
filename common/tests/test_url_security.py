import socket
from unittest.mock import MagicMock, patch

from django.test import TestCase

from common.url_security import is_url_safe_for_fetch


def _make_addrinfo(ip):
    return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", (ip, 0))]


def _make_addrinfo_list(ips):
    return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", (ip, 0)) for ip in ips]


class TestIsUrlSafeForFetchScheme(TestCase):

    def test_ftp_scheme_blocked(self):
        self.assertFalse(is_url_safe_for_fetch("ftp://example.com"))

    def test_file_scheme_blocked(self):
        self.assertFalse(is_url_safe_for_fetch("file:///etc/passwd"))

    def test_gopher_scheme_blocked(self):
        self.assertFalse(is_url_safe_for_fetch("gopher://x"))

    def test_empty_url_blocked(self):
        self.assertFalse(is_url_safe_for_fetch(""))

    def test_no_hostname_blocked(self):
        self.assertFalse(is_url_safe_for_fetch("http://"))


class TestIsUrlSafeForFetchIP(TestCase):

    @patch("common.url_security.socket.getaddrinfo")
    def test_public_ip_allowed(self, mock_dns):
        mock_dns.return_value = _make_addrinfo("93.184.216.34")
        self.assertTrue(is_url_safe_for_fetch("https://example.com"))

    @patch("common.url_security.socket.getaddrinfo")
    def test_public_dns_8888_allowed(self, mock_dns):
        mock_dns.return_value = _make_addrinfo("8.8.8.8")
        self.assertTrue(is_url_safe_for_fetch("https://dns.google"))

    @patch("common.url_security.socket.getaddrinfo")
    def test_loopback_blocked(self, mock_dns):
        mock_dns.return_value = _make_addrinfo("127.0.0.1")
        self.assertFalse(is_url_safe_for_fetch("http://localhost"))

    @patch("common.url_security.socket.getaddrinfo")
    def test_private_10x_blocked(self, mock_dns):
        mock_dns.return_value = _make_addrinfo("10.0.0.1")
        self.assertFalse(is_url_safe_for_fetch("http://internal.corp"))

    @patch("common.url_security.socket.getaddrinfo")
    def test_private_172_16_blocked(self, mock_dns):
        mock_dns.return_value = _make_addrinfo("172.16.0.1")
        self.assertFalse(is_url_safe_for_fetch("http://internal.corp"))

    @patch("common.url_security.socket.getaddrinfo")
    def test_docker_bridge_blocked(self, mock_dns):
        mock_dns.return_value = _make_addrinfo("172.17.0.1")
        self.assertFalse(is_url_safe_for_fetch("http://docker-host"))

    @patch("common.url_security.socket.getaddrinfo")
    def test_private_192_168_blocked(self, mock_dns):
        mock_dns.return_value = _make_addrinfo("192.168.1.1")
        self.assertFalse(is_url_safe_for_fetch("http://router.local"))

    @patch("common.url_security.socket.getaddrinfo")
    def test_link_local_metadata_blocked(self, mock_dns):
        mock_dns.return_value = _make_addrinfo("169.254.169.254")
        self.assertFalse(is_url_safe_for_fetch("http://169.254.169.254/"))

    @patch("common.url_security.socket.getaddrinfo")
    def test_unspecified_blocked(self, mock_dns):
        mock_dns.return_value = _make_addrinfo("0.0.0.0")
        self.assertFalse(is_url_safe_for_fetch("http://zero"))

    @patch("common.url_security.socket.getaddrinfo")
    def test_ipv6_loopback_blocked(self, mock_dns):
        mock_dns.return_value = [(socket.AF_INET6, socket.SOCK_STREAM, 0, "", ("::1", 0, 0, 0))]
        self.assertFalse(is_url_safe_for_fetch("http://ipv6-loopback"))

    @patch("common.url_security.socket.getaddrinfo")
    def test_ipv6_unique_local_blocked(self, mock_dns):
        mock_dns.return_value = [(socket.AF_INET6, socket.SOCK_STREAM, 0, "", ("fd00::1", 0, 0, 0))]
        self.assertFalse(is_url_safe_for_fetch("http://ipv6-ula"))

    @patch("common.url_security.socket.getaddrinfo")
    def test_shared_address_space_blocked(self, mock_dns):
        mock_dns.return_value = _make_addrinfo("100.64.0.1")
        self.assertFalse(is_url_safe_for_fetch("http://cgnat"))

    @patch("common.url_security.socket.getaddrinfo")
    def test_dns_failure_blocked(self, mock_dns):
        mock_dns.side_effect = socket.gaierror("Name resolution failed")
        self.assertFalse(is_url_safe_for_fetch("http://nonexistent.invalid"))

    @patch("common.url_security.socket.getaddrinfo")
    def test_mixed_ips_one_private_blocked(self, mock_dns):
        mock_dns.return_value = _make_addrinfo_list(["8.8.8.8", "127.0.0.1"])
        self.assertFalse(is_url_safe_for_fetch("http://dual-record.example.com"))


class TestResolveUrlProtection(TestCase):

    @patch("common.url_metadata_parser.requests.head")
    @patch("common.url_security.socket.getaddrinfo")
    def test_private_ip_returns_error_tuple(self, mock_dns, mock_head):
        from common.url_metadata_parser import resolve_url, MAX_PARSABLE_CONTENT_LENGTH

        mock_dns.return_value = _make_addrinfo("10.0.0.1")
        url, ct, cl = resolve_url("http://internal.corp/secret")
        self.assertIsNone(url)
        self.assertIsNone(ct)
        self.assertGreater(cl, MAX_PARSABLE_CONTENT_LENGTH)
        mock_head.assert_not_called()

    @patch("common.url_metadata_parser.requests.head")
    @patch("common.url_security.socket.getaddrinfo")
    def test_redirect_to_private_ip_blocked(self, mock_dns, mock_head):
        from common.url_metadata_parser import resolve_url, MAX_PARSABLE_CONTENT_LENGTH

        mock_dns.side_effect = [
            _make_addrinfo("93.184.216.34"),
            _make_addrinfo("127.0.0.1"),
        ]

        redirect_response = MagicMock()
        redirect_response.status_code = 302
        redirect_response.headers = {"location": "http://localhost/admin"}
        mock_head.return_value = redirect_response

        url, ct, cl = resolve_url("http://example.com/redir")
        self.assertIsNone(url)
        self.assertGreater(cl, MAX_PARSABLE_CONTENT_LENGTH)

    @patch("common.url_metadata_parser.requests.head")
    @patch("common.url_security.socket.getaddrinfo")
    def test_public_url_no_redirect(self, mock_dns, mock_head):
        from common.url_metadata_parser import resolve_url

        mock_dns.return_value = _make_addrinfo("93.184.216.34")

        ok_response = MagicMock()
        ok_response.status_code = 200
        ok_response.headers = {"content-type": "text/html", "content-length": "1234"}
        mock_head.return_value = ok_response

        url, ct, cl = resolve_url("http://example.com/page")
        self.assertEqual(url, "http://example.com/page")
        self.assertEqual(ct, "text/html")
        self.assertEqual(cl, 1234)

    @patch("common.url_metadata_parser.requests.head")
    @patch("common.url_security.socket.getaddrinfo")
    def test_relative_redirect_handled(self, mock_dns, mock_head):
        from common.url_metadata_parser import resolve_url

        mock_dns.return_value = _make_addrinfo("93.184.216.34")

        redirect_response = MagicMock()
        redirect_response.status_code = 301
        redirect_response.headers = {"location": "/new-path"}

        ok_response = MagicMock()
        ok_response.status_code = 200
        ok_response.headers = {"content-type": "text/html", "content-length": "500"}

        mock_head.side_effect = [redirect_response, ok_response]

        url, ct, cl = resolve_url("http://example.com/old-path")
        self.assertEqual(url, "http://example.com/new-path")
        self.assertEqual(ct, "text/html")


class TestLoadPageSafeProtection(TestCase):

    @patch("common.url_metadata_parser.requests.get")
    @patch("common.url_security.socket.getaddrinfo")
    def test_private_ip_returns_empty(self, mock_dns, mock_get):
        from common.url_metadata_parser import load_page_safe

        mock_dns.return_value = _make_addrinfo("10.0.0.1")
        result = load_page_safe("http://internal.corp/secret")
        self.assertEqual(result, "")
        mock_get.assert_not_called()

    @patch("common.url_metadata_parser.requests.get")
    @patch("common.url_security.socket.getaddrinfo")
    def test_public_ip_returns_content(self, mock_dns, mock_get):
        from common.url_metadata_parser import load_page_safe

        mock_dns.return_value = _make_addrinfo("93.184.216.34")

        mock_response = MagicMock()
        mock_response.raw.read.return_value = b"<html>hello</html>"
        mock_get.return_value = mock_response

        result = load_page_safe("http://example.com")
        self.assertEqual(result, b"<html>hello</html>")


class TestUploadImageProtection(TestCase):

    @patch("common.images.requests.get")
    @patch("common.url_security.socket.getaddrinfo")
    def test_private_ip_returns_none(self, mock_dns, mock_get):
        from common.images import upload_image_from_url

        mock_dns.return_value = _make_addrinfo("10.0.0.1")

        with self.settings(DEBUG=False, MEDIA_UPLOAD_URL="http://media.test", MEDIA_UPLOAD_CODE="test"):
            result = upload_image_from_url("http://internal.corp/image.jpg")

        self.assertIsNone(result)
        mock_get.assert_not_called()
