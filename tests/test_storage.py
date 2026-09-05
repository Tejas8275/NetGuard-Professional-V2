import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import core.storage as storage


class StorageTests(unittest.TestCase):
    def test_state_is_versioned_and_round_trips_atomically(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / 'state.json'
            with patch.object(storage, 'APP_DATA_FILE', state_path), patch.object(storage, 'LEGACY_APP_DATA_FILE', Path(directory) / 'legacy.json'):
                storage.save_app_state({'history': [{'action': 'Ping'}]})
                self.assertFalse(state_path.with_suffix('.json.tmp').exists())
                loaded = storage.load_app_state()
                self.assertEqual(loaded['schema_version'], storage.STATE_SCHEMA_VERSION)
                self.assertEqual(loaded['history'][0]['action'], 'Ping')

    def test_legacy_users_are_migrated_to_the_app_data_location(self):
        with tempfile.TemporaryDirectory() as directory:
            new_path = Path(directory) / 'users.json'
            legacy_path = Path(directory) / 'legacy-users.json'
            legacy_path.write_text('{"analyst": {"username": "analyst"}}', encoding='utf-8')
            with patch.object(storage, 'USER_DB_FILE', new_path), patch.object(storage, 'LEGACY_USER_DB_FILE', legacy_path):
                self.assertEqual(storage.load_users()['analyst']['username'], 'analyst')
                self.assertTrue(new_path.exists())
