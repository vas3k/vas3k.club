from django.test import TestCase

from common.request import browser_from_useragent


class TestBrowserFromUseragent(TestCase):
    def test_returns_none_without_useragent(self):
        self.assertIsNone(browser_from_useragent(None))
        self.assertIsNone(browser_from_useragent(""))

    def test_parses_chrome(self):
        ua = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        self.assertEqual(browser_from_useragent(ua), "Chrome 120")

    def test_parses_edge_before_chrome(self):
        ua = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
        )
        self.assertEqual(browser_from_useragent(ua), "Edge 120")

    def test_parses_firefox(self):
        ua = "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0"
        self.assertEqual(browser_from_useragent(ua), "Firefox 121")

    def test_parses_safari(self):
        ua = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) Version/17.0 Safari/605.1.15"
        )
        self.assertEqual(browser_from_useragent(ua), "Safari 17")

    def test_parses_telegram(self):
        self.assertEqual(browser_from_useragent("TelegramBot (like TwitterBot)"), "Telegram")

    def test_unknown_useragent(self):
        self.assertIsNone(browser_from_useragent("UnknownClient/1.0"))
