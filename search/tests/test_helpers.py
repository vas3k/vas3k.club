from django.test import SimpleTestCase

from datetime import datetime

from search.helpers import parse_search_query, parse_date_filter_bounds


class SearchHelpersTests(SimpleTestCase):
    def test_parse_supports_negative_custom_operators(self):
        parsed = parse_search_query('python -author:vas3k -type:comment -title:guide')

        self.assertEqual(parsed["query"], "python")
        self.assertEqual(parsed["-author"], "vas3k")
        self.assertEqual(parsed["-type"], "comment")
        self.assertEqual(parsed["-title"], "guide")

    def test_parse_negative_custom_operators_with_quotes(self):
        parsed = parse_search_query('"quote token" -author:"vas3k" title:"dev rel"')

        self.assertEqual(parsed["query"], '"quote token"')
        self.assertEqual(parsed["-author"], "vas3k")
        self.assertEqual(parsed["title"], "dev rel")

    def test_parse_keeps_minus_quoted_phrase_in_query(self):
        parsed = parse_search_query('python -"exclude this"')

        self.assertEqual(parsed["query"], 'python -"exclude this"')

    def test_parse_supports_quoted_values_for_custom_operators(self):
        parsed = parse_search_query('author:"vas3k team" title:"two words" -title:"bad words"')

        self.assertEqual(parsed["author"], "vas3k team")
        self.assertEqual(parsed["title"], "two words")
        self.assertEqual(parsed["-title"], "bad words")

    def test_parse_supports_since_until(self):
        parsed = parse_search_query("python since:2024 until:2024-05")

        self.assertEqual(parsed["query"], "python")
        self.assertEqual(parsed["since"], "2024")
        self.assertEqual(parsed["until"], "2024-05")

    def test_parse_date_filter_bounds(self):
        self.assertEqual(
            parse_date_filter_bounds("2025"),
            (datetime(2025, 1, 1), datetime(2026, 1, 1)),
        )
        self.assertEqual(
            parse_date_filter_bounds("2024-01"),
            (datetime(2024, 1, 1), datetime(2024, 2, 1)),
        )
        self.assertEqual(
            parse_date_filter_bounds("2023-04-10"),
            (datetime(2023, 4, 10), datetime(2023, 4, 11)),
        )
        self.assertIsNone(parse_date_filter_bounds("2024-13"))
        self.assertIsNone(parse_date_filter_bounds("abcd"))
