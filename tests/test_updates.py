import io
import json
import unittest
from unittest.mock import patch

from organizer.updates import latest_release


class UpdateTests(unittest.TestCase):
    def test_latest_stable_release_is_compared_and_link_is_fixed(self):
        for tag, expected in (("v1.2.0", ("1.2.0", "https://github.com/kashnordeen/downloads-organizer/releases/tag/v1.2.0")),
                              ("v1.1.0", None), ("v1.0.0", None)):
            with self.subTest(tag=tag):
                data = {"tag_name": tag, "draft": False, "prerelease": False,
                        "html_url": "https://untrusted.example/installer.exe"}
                with patch("organizer.updates.urlopen", return_value=io.BytesIO(json.dumps(data).encode())):
                    self.assertEqual(latest_release("1.1.0"), expected)

    def test_bad_prerelease_and_oversized_responses_cannot_offer_installation(self):
        for data in ({"tag_name": "v1.3.0", "draft": False, "prerelease": True},
                     {"tag_name": "v1.3.0", "draft": True, "prerelease": False}):
            with patch("organizer.updates.urlopen", return_value=io.BytesIO(json.dumps(data).encode())):
                self.assertIsNone(latest_release("1.1.0"))
        for data in (b"not json", b"[]", b"x" * (1024 * 1024 + 1),
                     b'{"tag_name":"../malicious","draft":false,"prerelease":false}'):
            with patch("organizer.updates.urlopen", return_value=io.BytesIO(data)):
                with self.assertRaises(ValueError):
                    latest_release("1.1.0")
        with patch("organizer.updates.urlopen", side_effect=TimeoutError("offline")):
            with self.assertRaises(TimeoutError):
                latest_release("1.1.0")
