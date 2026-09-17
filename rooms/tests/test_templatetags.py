from django.test import SimpleTestCase
from django.template.loader import render_to_string

from rooms.templatetags.rooms import network_icon


class NetworkIconTest(SimpleTestCase):
    def test_replaces_flag_emoji_with_twemoji_image(self):
        rendered = network_icon("🇦🇲")

        self.assertIn('class="emoji-flag"', rendered)
        self.assertIn("1f1e6-1f1f2.svg", rendered)
        self.assertIn('alt="🇦🇲"', rendered)

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
