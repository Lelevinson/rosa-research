"""Consent page must disclose the selected storage mode; no provider contacted."""
import threading
import unittest
from urllib.request import urlopen
from rosa_auth.oauth import Attempt, ISSUER, LoginServer


class CleanupNoticeTests(unittest.TestCase):
    def test_default_and_opt_in_pages_disclose_their_actual_cleanup(self):
        for remembered in (False, True):
            with self.subTest(remembered=remembered):
                with LoginServer(Attempt('SYNTHETIC_HOST'), ISSUER + '/authorize', 0,
                        remember_authorization=remembered) as server:
                    worker = threading.Thread(target=server.handle_request)
                    worker.start()
                    try:
                        with urlopen(server.base_url + '/', timeout=3) as response:
                            text = response.read().decode()
                            self.assertEqual(response.headers['Cache-Control'], 'no-store')
                        if remembered:
                            self.assertIn('refresh credential remains encrypted', text)
                            self.assertIn('explicit sign-out', text)
                            self.assertNotIn('attempts session revocation when finished', text)
                        else:
                            self.assertIn('Tokens stay in memory', text)
                            self.assertIn('attempts session revocation when finished', text)
                            self.assertNotIn('refresh credential remains encrypted', text)
                    finally:
                        worker.join(timeout=5)
                        self.assertFalse(worker.is_alive())


if __name__ == '__main__': unittest.main()
