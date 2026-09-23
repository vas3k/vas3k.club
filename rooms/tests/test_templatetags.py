from django.test import SimpleTestCase
from django.template.loader import render_to_string

from rooms.templatetags.rooms import network_icon


class NetworkIconTest(SimpleTestCase):
    def test_replaces_single_flag_emoji_with_twemoji_image(self):
        rendered = network_icon("🇦🇲")

        self.assertIn('class="emoji-flag"', rendered)
        self.assertIn("1f1e6-1f1f2.svg", rendered)
        self.assertIn('alt="🇦🇲"', rendered)
        self.assertNotIn("emoji-flags-multiple", rendered)

    def test_groups_multiple_flag_emoji_for_compact_layout(self):
        rendered = network_icon("🇷🇸 🇲🇪<br>🇦🇱 🇸🇮")

        self.assertIn('class="emoji-flags emoji-flags-multiple"', rendered)
        self.assertEqual(4, rendered.count('class="emoji-flag"'))
        self.assertIn("1f1f7-1f1f8.svg", rendered)
        self.assertIn("1f1f2-1f1ea.svg", rendered)
        self.assertIn("1f1e6-1f1f1.svg", rendered)
        self.assertIn("1f1f8-1f1ee.svg", rendered)
        self.assertNotIn("<br", rendered)
        self.assertNotRegex(rendered, r'loading="lazy">\s+<img')

    def test_preserves_non_flag_icons(self):
        rendered = network_icon('<i class="fas fa-comments"></i>')

        self.assertEqual('<i class="fas fa-comments"></i>', rendered)

    def test_preserves_text_emoji(self):
        rendered = network_icon("🌐")

        self.assertEqual("🌐", rendered)

    def test_network_block_template_loads_filter(self):
        class Rooms(list):
            def all(self):
                return self

        class Room:
            icon = "🇦🇲"
            title = "Armenia"
            subtitle = ""
            chat_member_count = 10
            image = ""
            is_visible = True

            @property
            def get_private_url(self):
                return "#armenia"

        class Group:
            code = "relocation"
            title = "Relocation"
            text = ""
            rooms = Rooms([Room()])

        rendered = render_to_string("network/groups/block.html", {"group": Group()})

        self.assertIn('class="emoji-flag"', rendered)
        self.assertIn("1f1e6-1f1f2.svg", rendered)
