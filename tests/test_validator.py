from __future__ import annotations

import unittest

from modules.phone import get_phone_info, parse_phone_number


class ValidatorTests(unittest.TestCase):
    def test_invalid_number_returns_none(self) -> None:
        self.assertIsNone(parse_phone_number("12345"))

    def test_valid_number_extracts_basic_metadata(self) -> None:
        info = get_phone_info("+573001234567", lang="es")
        self.assertNotIn("error", info)
        self.assertEqual(info["number"], "+573001234567")
        self.assertEqual(info["country_code"], "CO")
        self.assertIn("America/Bogota", info["timezones"])
        self.assertTrue(info["line_type"])


if __name__ == "__main__":
    unittest.main()
