import os
import unittest
from unittest.mock import patch

from config import Config


class ConfigTests(unittest.TestCase):
    def test_url_is_required(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(SystemExit, "OPENCONNECT_URL is required"):
                Config.from_env()

    def test_complete_credentials_enable_auto_connect(self):
        env = {
            "OPENCONNECT_URL": "https://vpn.example",
            "OPENCONNECT_USER": "alice",
            "OPENCONNECT_PASSWORD": "secret",
            "AUTO_CONNECT": "yes",
        }
        with patch.dict(os.environ, env, clear=True):
            config = Config.from_env()

        self.assertTrue(config.has_creds)
        self.assertTrue(config.auto_connect)

    def test_incomplete_credentials_disable_auto_connect(self):
        env = {
            "OPENCONNECT_URL": "https://vpn.example",
            "OPENCONNECT_USER": "alice",
            "AUTO_CONNECT": "true",
        }
        with patch.dict(os.environ, env, clear=True):
            config = Config.from_env()

        self.assertFalse(config.has_creds)
        self.assertFalse(config.auto_connect)


if __name__ == "__main__":
    unittest.main()
