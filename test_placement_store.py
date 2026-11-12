import csv
import sqlite3
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from placement_store import (
    add_application,
    applications_to_csv,
    delete_application,
    initialize_database,
    load_applications,
    load_dashboard_data,
    load_upcoming_interviews,
    update_application_status,
)


class PlacementStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "placements.db"
        initialize_database(self.database_path)
        add_application(
            self.database_path,
            "Google",
            "Software developer",
            "2026-10-29",
            "Applied",
        )
        add_application(
            self.database_path,
            "Acme",
            "Analyst",
            "2026-10-30",
            "Interview Scheduled",
            (date.today() + timedelta(days=5)).isoformat(),
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_search_is_case_insensitive_and_status_filter_works(self):
        results = load_applications(self.database_path, "goo", "Applied")

        self.assertEqual([row["company_name"] for row in results], ["Google"])
        status_results = load_applications(
            self.database_path,
            status_filter="Interview Scheduled",
        )
        self.assertEqual(
            [row["company_name"] for row in status_results],
            ["Acme"],
        )

    def test_status_can_be_updated(self):
        application_id = load_applications(self.database_path)[0]["application_id"]

        self.assertTrue(
            update_application_status(
                self.database_path,
                application_id,
                "Shortlisted",
            )
        )
        self.assertEqual(
            load_applications(self.database_path)[0]["status"],
            "Shortlisted",
        )

    def test_delete_removes_selected_application(self):
        application_id = load_applications(self.database_path)[0]["application_id"]

        self.assertTrue(delete_application(self.database_path, application_id))
        self.assertEqual(
            [row["company_name"] for row in load_applications(self.database_path)],
            ["Google"],
        )

    def test_csv_export_contains_application_fields(self):
        rows = load_applications(self.database_path)

        exported = list(csv.DictReader(applications_to_csv(rows).splitlines()))

        self.assertEqual(len(exported), 2)
        self.assertEqual(exported[0]["company_name"], "Acme")
        self.assertEqual(exported[0]["interview_date"], rows[0]["interview_date"])

    def test_only_future_interviews_are_listed(self):
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        add_application(
            self.database_path,
            "Past interview",
            "Engineer",
            "2026-10-20",
            "Interview Scheduled",
            yesterday,
        )

        interviews = load_upcoming_interviews(
            self.database_path,
            today=date.today().isoformat(),
        )

        self.assertEqual([row["company_name"] for row in interviews], ["Acme"])

    def test_existing_database_is_migrated_without_losing_rows(self):
        legacy_path = Path(self.temp_dir.name) / "legacy.db"
        connection = sqlite3.connect(legacy_path)
        connection.execute(
            """
            CREATE TABLE applications (
                application_id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL,
                job_role TEXT NOT NULL,
                application_date TEXT,
                status TEXT
            )
            """
        )
        connection.execute(
            """
            INSERT INTO applications (company_name, job_role, status)
            VALUES ('Legacy Co', 'Engineer', 'Applied')
            """
        )
        connection.commit()
        connection.close()

        initialize_database(legacy_path)
        applications, total, _, _ = load_dashboard_data(legacy_path)

        self.assertEqual(total, 1)
        self.assertEqual(applications[0]["company_name"], "Legacy Co")
        self.assertIsNone(applications[0]["interview_date"])


if __name__ == "__main__":
    unittest.main()
