import csv
import io
import sqlite3
from datetime import date


CSV_COLUMNS = [
    "application_id",
    "company_name",
    "job_role",
    "application_date",
    "status",
    "interview_date",
]


def _connect(database_path):
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database(database_path):
    """Create the applications table and migrate older databases in place."""
    connection = _connect(database_path)

    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS applications (
                application_id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL,
                job_role TEXT NOT NULL,
                application_date TEXT,
                status TEXT,
                interview_date TEXT
            )
            """
        )
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(applications)")
        }
        if "interview_date" not in columns:
            connection.execute(
                "ALTER TABLE applications ADD COLUMN interview_date TEXT"
            )
        connection.commit()
    finally:
        connection.close()


def load_dashboard_data(database_path):
    """Load applications and their summary information from SQLite."""
    connection = _connect(database_path)

    try:
        applications = connection.execute(
            """
            SELECT application_id, company_name, job_role, application_date,
                   status, interview_date
            FROM applications
            ORDER BY application_id DESC
            """
        ).fetchall()
        total_applications = connection.execute(
            "SELECT COUNT(*) FROM applications"
        ).fetchone()[0]
        role_counts = connection.execute(
            """
            SELECT job_role, COUNT(*) AS application_count
            FROM applications
            WHERE job_role IS NOT NULL AND TRIM(job_role) != ''
            GROUP BY job_role
            """
        ).fetchall()
        status_counts = connection.execute(
            """
            SELECT status, COUNT(*) AS application_count
            FROM applications
            GROUP BY status
            """
        ).fetchall()
    finally:
        connection.close()

    return applications, total_applications, role_counts, status_counts


def add_application(
    database_path, company_name, job_role, application_date, status, interview_date=None
):
    """Save one application to the database."""
    connection = _connect(database_path)

    try:
        connection.execute(
            """
            INSERT INTO applications (
                company_name, job_role, application_date, status, interview_date
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (company_name, job_role, application_date, status, interview_date),
        )
        connection.commit()
    finally:
        connection.close()


def load_applications(database_path, search_term="", status_filter="All statuses"):
    """Load applications matching the company-name search and status filter."""
    query = """
        SELECT application_id, company_name, job_role, application_date,
               status, interview_date
        FROM applications
        WHERE company_name LIKE ? COLLATE NOCASE
    """
    parameters = [f"%{search_term.strip()}%"]

    if status_filter == "Not specified":
        query += " AND (status IS NULL OR TRIM(status) = '')"
    elif status_filter != "All statuses":
        query += " AND status = ?"
        parameters.append(status_filter)

    query += " ORDER BY application_id DESC"
    connection = _connect(database_path)

    try:
        return connection.execute(query, parameters).fetchall()
    finally:
        connection.close()


def update_application_status(database_path, application_id, status):
    """Update an application's status; return whether a row was updated."""
    connection = _connect(database_path)

    try:
        cursor = connection.execute(
            "UPDATE applications SET status = ? WHERE application_id = ?",
            (status, application_id),
        )
        connection.commit()
        return cursor.rowcount == 1
    finally:
        connection.close()


def delete_application(database_path, application_id):
    """Delete an application; return whether a row was deleted."""
    connection = _connect(database_path)

    try:
        cursor = connection.execute(
            "DELETE FROM applications WHERE application_id = ?",
            (application_id,),
        )
        connection.commit()
        return cursor.rowcount == 1
    finally:
        connection.close()


def load_upcoming_interviews(database_path, today=None):
    """Load interviews scheduled for today or a later date."""
    today = today or date.today().isoformat()
    connection = _connect(database_path)

    try:
        return connection.execute(
            """
            SELECT application_id, company_name, job_role, interview_date, status
            FROM applications
            WHERE interview_date IS NOT NULL
              AND date(interview_date) >= date(?)
            ORDER BY date(interview_date), application_id
            """,
            (today,),
        ).fetchall()
    finally:
        connection.close()


def applications_to_csv(applications):
    """Serialize application rows to CSV text for Streamlit downloads."""
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(dict(application) for application in applications)
    return output.getvalue()
