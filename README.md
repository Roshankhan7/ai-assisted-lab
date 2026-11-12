# Placement Application Tracker

A Streamlit app for tracking job applications, viewing application totals, and summarizing applications by role and status. Application records are stored in the local SQLite database, `placements.db`.

## Features

- Add applications with an optional interview date.
- Search by company name and filter by application status.
- Update statuses or delete applications with confirmation.
- Export the matching applications to CSV.
- View upcoming interviews alongside the application summary.

On startup, the app adds the optional interview-date column to an existing database if it is missing; existing application records are preserved.

## Run locally

1. Create and activate a Python virtual environment.
2. Install the dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

3. Initialize the database if needed:

   ```bash
   python init_db.py
   ```

4. Start the app:

   ```bash
   streamlit run app.py
   ```

The current `placements.db` is included in this repository. Do not publish personal application records to a public repository unless you intend them to be public.