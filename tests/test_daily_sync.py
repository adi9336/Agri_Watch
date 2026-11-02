"""
Unit Tests for Agri_watch Automated Daily Mandi Price Sync Engine
"""

import os
import sys
import unittest

sys.stdout.reconfigure(encoding='utf-8')

# Ensure parent directory is in path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from scripts.daily_mandi_sync import load_existing_keys_for_dates, sync_mandi_data, CSV_PATH


class TestDailyMandiSync(unittest.TestCase):
    def test_csv_exists(self):
        self.assertTrue(os.path.exists(CSV_PATH), "Historical mandi CSV should exist.")

    def test_load_existing_keys(self):
        # Pick a date known to exist in the snapshot
        keys = load_existing_keys_for_dates({"02/11/2026"})
        self.assertIsInstance(keys, set)
        self.assertGreater(len(keys), 0)
        # Check compound key structure: (arrival_date, state, district, market, commodity, variety)
        sample_key = next(iter(keys))
        self.assertEqual(len(sample_key), 6)
        self.assertEqual(sample_key[0], "02/11/2026")

    def test_sync_dry_run(self):
        # Dry run should succeed without appending to CSV
        result = sync_mandi_data(target_date="02/11/2026", dry_run=True, max_records_per_date=50)
        self.assertEqual(result.get("status"), "dry_run")
        self.assertIn("total_fetched", result)
        self.assertIn("new_records", result)


if __name__ == "__main__":
    unittest.main()
