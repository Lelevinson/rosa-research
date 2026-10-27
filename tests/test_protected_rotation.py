"""Real Windows DPAPI regression; synthetic profile, no provider or real grant."""
import os
import shutil
import unittest
from uuid import uuid4

from rosa_auth.oauth import SafeError
from rosa_auth.protected_store import WindowsCredentialStore


@unittest.skipUnless(os.environ.get('ROSA_TEST_WINDOWS_STORAGE') == '1'
                     and shutil.which('powershell.exe'), 'explicit Windows-storage integration opt-in')
class ProtectedRotationTests(unittest.TestCase):
    def test_replacement_is_persisted_across_helper_restarts_and_profile_stays_leased(self):
        profile = 'rotation_test_' + uuid4().hex[:20]
        first = {'synthetic_refresh': 'NOT_A_REAL_CREDENTIAL_INITIAL'}
        replacement = {'synthetic_refresh': 'NOT_A_REAL_CREDENTIAL_REPLACEMENT'}
        with WindowsCredentialStore(profile) as store:
            self.assertIsNone(store.load())
            store.save(first)
            self.assertEqual(store.load(), first)
            store.save(replacement)
            self.assertEqual(store.load(), replacement)
            with self.assertRaises(SafeError) as caught:
                WindowsCredentialStore(profile)
            self.assertEqual(caught.exception.code, 'credential_profile_in_use')
        with WindowsCredentialStore(profile) as store:
            try:
                self.assertEqual(store.load(), replacement)
            finally:
                store.delete()
            self.assertIsNone(store.load())


if __name__ == '__main__': unittest.main()
