from pathlib import Path

import streamlit as st

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


DATABASE_PATH = Path(__file__).with_name("placements.db")
APPLICATION_STATUSES = [
    "Applied",
    "Shortlisted",
    "Interview Scheduled",
    "Selected",
    "Rejected",
]


def get_most_applied_roles(role_counts):
    """Return all highest-count roles in a consistent alphabetical order."""
    if not role_counts:
        return []

    highest_count = max(row["application_count"] for row in role_counts)
    return sorted(
        (
            row["job_role"]
            for row in role_counts
            if row["application_count"] == highest_count
        ),
        key=lambda role: (role.casefold(), role),
    )


st.set_page_config(page_title="Placement Application Tracker", page_icon="📋")
initialize_database(DATABASE_PATH)
st.title("Placement Application Tracker")
st.write("Keep track of your job applications and their progress.")

with st.form("add_application_form"):
    st.subheader("Add Application")
    company_name = st.text_input("Company Name")
    job_role = st.text_input("Job Role")
    application_date = st.date_input("Application Date", format="YYYY-MM-DD")
    interview_date = st.date_input(
        "Interview Date (optional)", value=None, format="YYYY-MM-DD"
    )
    status = st.selectbox("Status", APPLICATION_STATUSES)
    submitted = st.form_submit_button("Add Application")

if submitted:
    company_name = company_name.strip()
    job_role = job_role.strip()

    if not company_name or not job_role:
        st.error("Please enter both a company name and a job role.")
    else:
        add_application(
            DATABASE_PATH,
            company_name,
            job_role,
            application_date.isoformat(),
            status,
            interview_date.isoformat() if interview_date else None,
        )
        st.success("Application added successfully.")

st.subheader("View Applications")
search_term = st.text_input("Search by company name")
status_filter = st.selectbox(
    "Filter by status",
    ["All statuses", *APPLICATION_STATUSES, "Not specified"],
)
matching_applications = load_applications(
    DATABASE_PATH,
    search_term,
    status_filter,
)

if matching_applications:
    application_ids = [row["application_id"] for row in matching_applications]
    with st.expander("Update an application status"):
        with st.form("update_application_status_form"):
            update_id = st.selectbox(
                "Application",
                application_ids,
                format_func=lambda application_id: next(
                    f"#{row['application_id']} - {row['company_name']} ({row['job_role']})"
                    for row in matching_applications
                    if row["application_id"] == application_id
                ),
                key="update_application_id",
            )
            current_status = next(
                row["status"]
                for row in matching_applications
                if row["application_id"] == update_id
            )
            status_options = list(APPLICATION_STATUSES)
            if current_status and current_status not in status_options:
                status_options.insert(0, current_status)
            selected_status = st.selectbox(
                "New status",
                status_options,
                index=(
                    status_options.index(current_status)
                    if current_status in status_options
                    else 0
                ),
            )
            update_submitted = st.form_submit_button("Update Status")

        if update_submitted:
            if update_application_status(
                DATABASE_PATH,
                update_id,
                selected_status,
            ):
                st.success("Application status updated.")
            else:
                st.error("The selected application could not be found.")

    with st.expander("Delete an application"):
        with st.form("delete_application_form"):
            delete_id = st.selectbox(
                "Application to delete",
                application_ids,
                format_func=lambda application_id: next(
                    f"#{row['application_id']} - {row['company_name']} ({row['job_role']})"
                    for row in matching_applications
                    if row["application_id"] == application_id
                ),
                key="delete_application_id",
            )
            confirmed = st.checkbox(
                f"I confirm deleting application #{delete_id} permanently."
            )
            delete_submitted = st.form_submit_button("Delete Application")

        if delete_submitted:
            if not confirmed:
                st.error("Confirm the deletion before continuing.")
            elif delete_application(DATABASE_PATH, delete_id):
                st.success("Application deleted.")
                matching_applications = load_applications(
                    DATABASE_PATH,
                    search_term,
                    status_filter,
                )
            else:
                st.error("The selected application could not be found.")

applications = load_applications(
    DATABASE_PATH,
    search_term,
    status_filter,
)
if applications:
    st.download_button(
        "Export matching applications as CSV",
        data=applications_to_csv(applications),
        file_name="placement_applications.csv",
        mime="text/csv",
    )
    st.dataframe(
        [dict(application) for application in applications],
        hide_index=True,
        width="stretch",
    )
else:
    st.info("No applications are available yet. Add one using the form above.")

st.subheader("Upcoming Interviews")
upcoming_interviews = load_upcoming_interviews(DATABASE_PATH)
if upcoming_interviews:
    st.dataframe(
        [dict(interview) for interview in upcoming_interviews],
        hide_index=True,
        width="stretch",
    )
else:
    st.info("No upcoming interviews are scheduled.")

st.subheader("Application Summary")
_, total_applications, role_counts, saved_status_counts = load_dashboard_data(
    DATABASE_PATH
)
st.metric("Total Applications", total_applications)

most_applied_roles = get_most_applied_roles(role_counts)
if most_applied_roles:
    if len(most_applied_roles) == 1:
        st.write(f"Most Applied Role: **{most_applied_roles[0]}**")
    else:
        tied_roles = ", ".join(most_applied_roles)
        st.write(f"Most Applied Roles (tied, alphabetical): **{tied_roles}**")
else:
    st.write("Most Applied Role: No applications yet.")

st.subheader("Status-wise Summary")
status_totals = {status_name: 0 for status_name in APPLICATION_STATUSES}

for row in saved_status_counts:
    status_name = row["status"] or "Not specified"
    status_totals[status_name] = row["application_count"]

for status_name, count in status_totals.items():
    st.write(f"**{status_name}:** {count}")

st.bar_chart(
    {
        "Status": list(status_totals.keys()),
        "Applications": list(status_totals.values()),
    },
    x="Status",
    y="Applications",
)
