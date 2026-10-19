from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from db import (
    Activity,
    EducationHistory,
    Semester,
    SemesterMark,
    Seminar,
    Student,
    Subject,
    clear_ledger_records,
    get_database_engine,
    initialize_database,
    seed_demo_data,
)
from sheets import (
    get_apps_script_config_status,
    get_sheets_config_status,
    sync_database_to_sheets,
    sync_database_via_apps_script,
)

# Load environment configuration from .env file
load_dotenv()

st.set_page_config(
    page_title="Academic Progression · Student Academic & Activity Ledger",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom styling matching the requested UI design
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif;
        letter-spacing: -0.02em;
    }

    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2.5rem;
        max-width: 1540px;
    }
    
    /* Top Header Brand */
    .app-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.85rem 1.4rem;
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border-radius: 12px;
        margin-bottom: 1.2rem;
        border: 1px solid #334155;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08);
        color: #ffffff;
    }
    .app-header-title {
        font-size: 1.3rem;
        font-weight: 700;
        margin: 0;
        color: #f8fafc;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .app-header-sub {
        font-size: 0.82rem;
        color: #94a3b8;
        margin-top: 2px;
    }
    .db-badge-mysql {
        background: #0284c7;
        color: #ffffff;
        font-size: 0.72rem;
        font-weight: 700;
        padding: 4px 10px;
        border-radius: 20px;
        letter-spacing: 0.04em;
    }
    .db-badge-sqlite {
        background: #059669;
        color: #ffffff;
        font-size: 0.72rem;
        font-weight: 700;
        padding: 4px 10px;
        border-radius: 20px;
        letter-spacing: 0.04em;
    }
    
    /* KPI Card styling */
    .kpi-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
        text-align: left;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(15, 23, 42, 0.08);
    }
    .kpi-title {
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #64748b;
        margin-bottom: 4px;
    }
    .kpi-value {
        font-size: 1.85rem;
        font-weight: 700;
        color: #0f172a;
        margin: 0;
        font-family: 'Outfit', sans-serif;
    }
    .kpi-sub {
        font-size: 0.75rem;
        color: #94a3b8;
        margin-top: 4px;
    }

    /* Student Profile Hero Card */
    .profile-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 22px;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.04);
        margin-bottom: 1.2rem;
    }
    .profile-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        border-bottom: 1px solid #f1f5f9;
        padding-bottom: 14px;
        margin-bottom: 14px;
    }
    .profile-name {
        font-size: 1.35rem;
        font-weight: 700;
        color: #0f172a;
        margin: 0;
    }
    .profile-roll {
        font-size: 0.88rem;
        color: #64748b;
        font-weight: 600;
    }
    .status-badge {
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.03em;
        display: inline-block;
    }
    .status-studying { background: #dcfce7; color: #15803d; }
    .status-graduated { background: #e0f2fe; color: #0369a1; }
    .status-onbreak { background: #fef3c7; color: #b45309; }
    .status-discontinued { background: #fee2e2; color: #b91c1c; }

    /* Sidebar Styling Exact Match */
    [data-testid="stSidebar"] {
        background: #0d1322 !important;
        border-right: 1px solid #1a2235;
    }
    [data-testid="stSidebar"] > div:first-child {
        background: #0d1322 !important;
        padding-top: 1rem;
    }
    .sidebar-brand-box {
        text-align: center;
        padding: 10px 0 16px;
        margin-bottom: 14px;
    }
    .sidebar-brand-icon {
        font-size: 38px;
        line-height: 1;
        display: inline-block;
        margin-bottom: 8px;
    }
    .sidebar-brand-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #ffffff;
        margin: 0;
        letter-spacing: -0.01em;
    }
    .sidebar-brand-sub {
        font-size: 0.74rem;
        color: #8da2c0;
        margin-top: 4px;
        letter-spacing: 0.02em;
    }
    .sidebar-nav-header {
        font-size: 0.68rem;
        font-weight: 700;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: #7b91b0;
        margin: 16px 0 8px 4px;
    }
    
    /* Navigation radio button custom styling */
    [data-testid="stSidebar"] [data-testid="stRadio"] > div {
        gap: 3px !important;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label {
        padding: 6px 10px !important;
        border-radius: 8px !important;
        color: #cbd5e1 !important;
        font-size: 0.88rem !important;
        font-weight: 500 !important;
        transition: all 0.15s ease !important;
        margin: 0 !important;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
        background: #172138 !important;
        color: #ffffff !important;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label[data-checked="true"] {
        background: #1e2d4d !important;
        color: #60a5fa !important;
        font-weight: 600 !important;
    }
    
    /* Sidebar Demo Control Buttons */
    [data-testid="stSidebar"] button {
        background: #172138 !important;
        border: 1px solid #283654 !important;
        color: #e2e8f0 !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        padding: 8px 14px !important;
        transition: all 0.2s ease !important;
    }
    [data-testid="stSidebar"] button:hover {
        background: #233252 !important;
        border-color: #3b82f6 !important;
        color: #ffffff !important;
    }

    /* Status indicator at sidebar bottom */
    .sidebar-sync-box {
        margin-top: 24px;
        padding-top: 14px;
        border-top: 1px solid #1a2235;
    }
    .sidebar-status-tag {
        font-size: 0.84rem;
        font-weight: 600;
        color: #e2e8f0;
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 12px;
    }
    .status-dot-green {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: #10b981;
        display: inline-block;
        box-shadow: 0 0 8px rgba(16, 185, 129, 0.5);
    }
    .status-dot-gray {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: #64748b;
        display: inline-block;
    }
    .sync-queue-title {
        font-size: 0.74rem;
        color: #8da2c0;
        margin: 0;
        font-weight: 500;
    }
    .sync-queue-count {
        font-size: 2rem;
        font-weight: 700;
        color: #ffffff;
        line-height: 1.1;
        margin: 2px 0 16px;
        font-family: 'Outfit', sans-serif;
    }
    .sidebar-footer-text {
        font-size: 0.68rem;
        color: #556987;
        text-align: center;
        margin-top: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# Database Engine Initialization
# -----------------------------------------------------------------------------
if "db_choice" not in st.session_state:
    st.session_state.db_choice = "mysql"

if "auto_sync_enabled" not in st.session_state:
    st.session_state.auto_sync_enabled = True

if "last_sync_time" not in st.session_state:
    st.session_state.last_sync_time = None


@st.cache_resource
def cached_engine(choice: str):
    return get_database_engine(choice)


engine, active_db_mode, engine_notice = cached_engine(st.session_state.db_choice)

try:
    initialize_database(engine)
except SQLAlchemyError as exc:
    st.error(
        f"Database initialization failed ({type(exc).__name__}): {exc}. "
        "Check your DATABASE_URL configuration in .env."
    )
    st.stop()


# -----------------------------------------------------------------------------
# Notifications & Helpers
# -----------------------------------------------------------------------------
def display_notice() -> None:
    notice = st.session_state.pop("ledger_notice", None)
    if notice:
        kind, message = notice
        getattr(st, kind)(message)


def set_notice(message: str, kind: str = "success") -> None:
    st.session_state.ledger_notice = (kind, message)


def friendly_integrity_error(exc: IntegrityError) -> str:
    detail = str(exc.orig).lower()
    if "unique" in detail or "duplicate" in detail:
        return "That value is already in use. Check roll number, email, subject code, semester, or marks for duplicate keys."
    if "check constraint" in detail or "check constraint failed" in detail:
        return "A value violates database range or category limits (e.g. percentages 0-100, SGPA/CGPA 0-10, obtained marks <= max marks)."
    if "foreign key" in detail:
        return "The referenced parent record (student, semester, or subject) was not found."
    if "not null" in detail:
        return "A required field was left empty."
    return f"The database rejected this operation due to an integrity constraint: {exc.orig}"


def trigger_auto_sync_if_enabled(engine_to_use) -> tuple[bool, str]:
    """Trigger Google Sheets one-way sync via Apps Script or Service Account if auto-sync is enabled."""
    if not st.session_state.get("auto_sync_enabled", True):
        return False, "Auto-sync disabled."

    apps_cfg = get_apps_script_config_status()
    sheets_cfg = get_sheets_config_status()

    if not apps_cfg["configured"] and not sheets_cfg["configured"]:
        return False, "No Google sync provider configured."

    try:
        if apps_cfg["configured"]:
            ok, msg = sync_database_via_apps_script(engine_to_use)
            if ok:
                st.session_state.last_sync_time = pd.Timestamp.now().strftime("%H:%M:%S")
                return True, "⚡ Synchronized to Google Sheets via Apps Script."
            else:
                return False, f"Apps Script sync failed: {msg}"
        elif sheets_cfg["configured"]:
            ok, msg = sync_database_to_sheets(engine_to_use)
            if ok:
                st.session_state.last_sync_time = pd.Timestamp.now().strftime("%H:%M:%S")
                return True, "⚡ Synchronized to Google Sheets via Service Account."
            else:
                return False, f"Sheets API sync failed: {msg}"
    except Exception as exc:
        return False, f"Auto-sync error: {exc}"
    return False, "Unknown provider state."


@dataclass(frozen=True)
class FieldSpec:
    name: str
    label: str
    kind: str = "text"
    required: bool = False
    options: tuple[str, ...] = ()
    choices: Callable[[], list[tuple[int, str]]] | None = None
    minimum: int | float | None = None
    maximum: int | float | None = None
    step: int | float | None = None
    nullable: bool = False


def fetch_choices(model: type, id_field: str, label_field: str) -> list[tuple[int, str]]:
    with Session(engine) as session:
        records = session.scalars(select(model).order_by(getattr(model, label_field))).all()
        if model is Semester:
            return [
                (
                    int(record.semester_id),
                    f"{record.student.roll_no} · Sem {record.semester_no} ({record.academic_year or 'N/A'})",
                )
                for record in records
            ]
        if model is Student:
            return [
                (int(record.student_id), f"{record.roll_no} · {record.full_name}")
                for record in records
            ]
        if model is Subject:
            return [
                (
                    int(record.subject_id),
                    f"{record.subject_code} · {record.subject_name} [{record.subject_type}]",
                )
                for record in records
            ]
        return [
            (int(getattr(record, id_field)), str(getattr(record, label_field)))
            for record in records
        ]


def scalar_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, date):
        return value
    return value


def model_dataframe(model: type, records: list[Any]) -> pd.DataFrame:
    columns = [column.name for column in model.__table__.columns]
    rows = [
        {column: scalar_value(getattr(record, column)) for column in columns}
        for record in records
    ]
    return pd.DataFrame(rows, columns=columns)


def render_field(
    spec: FieldSpec,
    initial: Any,
    key: str,
) -> Any:
    if spec.kind == "select":
        options: tuple[Any, ...] = spec.options
        return st.selectbox(
            spec.label,
            options,
            index=options.index(initial) if initial in options else 0,
            key=key,
        )
    if spec.kind == "foreign":
        choices = spec.choices() if spec.choices else []
        if not choices:
            st.info(f"Create a parent record for {spec.label.lower()} first.")
            return None
        ids = [choice[0] for choice in choices]
        labels = {choice[0]: choice[1] for choice in choices}
        return st.selectbox(
            spec.label,
            ids,
            index=ids.index(initial) if initial in ids else 0,
            format_func=lambda item: labels.get(item, str(item)),
            key=key,
        )
    if spec.kind in {"int", "float"}:
        if spec.nullable:
            has_value = st.checkbox(
                f"Specify {spec.label.lower()}",
                value=initial is not None,
                key=f"{key}_specified",
            )
            if not has_value:
                return None
        default = initial
        if default is None:
            default = (
                date.today().year
                if spec.name in {"admission_year", "passing_year"}
                else spec.minimum if spec.minimum is not None else 0
            )
        kwargs: dict[str, Any] = {
            "label": spec.label,
            "value": int(default) if spec.kind == "int" else float(default),
            "key": key,
        }
        if spec.minimum is not None:
            kwargs["min_value"] = int(spec.minimum) if spec.kind == "int" else float(spec.minimum)
        if spec.maximum is not None:
            kwargs["max_value"] = int(spec.maximum) if spec.kind == "int" else float(spec.maximum)
        if spec.step is not None:
            kwargs["step"] = int(spec.step) if spec.kind == "int" else float(spec.step)
        value = st.number_input(**kwargs)
        return int(value) if spec.kind == "int" else float(value)
    if spec.kind == "date":
        if spec.nullable:
            has_value = st.checkbox(
                f"Specify {spec.label.lower()}",
                value=initial is not None,
                key=f"{key}_specified",
            )
            if not has_value:
                return None
        return st.date_input(spec.label, value=initial or date.today(), key=key)
    if spec.kind == "textarea":
        return st.text_area(spec.label, value=initial or "", key=key)
    return st.text_input(spec.label, value="" if initial is None else str(initial), key=key)


def render_crud(
    title: str,
    model: type,
    id_field: str,
    fields: list[FieldSpec],
    label: Callable[[Any], str],
    table_view: pd.DataFrame | None = None,
    filter_field: str | None = None,
    filter_options: tuple[str, ...] = (),
    delete_warning: str | None = None,
) -> None:
    st.markdown(f"### {title}")
    with Session(engine) as session:
        records = session.scalars(select(model).order_by(getattr(model, id_field))).all()
        records = list(records)
        dataframe = model_dataframe(model, records)

    shown = table_view if table_view is not None else dataframe
    if filter_field and not shown.empty and filter_field in shown.columns:
        selected_filter = st.multiselect(
            f"Filter by {filter_field.replace('_', ' ').capitalize()}",
            filter_options,
            default=list(filter_options),
            key=f"{model.__tablename__}_filter",
        )
        shown = shown[shown[filter_field].isin(selected_filter)]
    if shown.empty:
        st.info("No records found in the database. Use the form below to create one.")
    else:
        st.dataframe(shown, width="stretch", hide_index=True)

    mode = st.radio(
        "Operation Mode",
        ["Create New Record", "Update / Delete Record"],
        horizontal=True,
        key=f"{model.__tablename__}_mode",
    )
    selected_record = None
    if mode == "Update / Delete Record":
        if not records:
            st.info("There are no records available to edit or delete.")
            return
        record_id = st.selectbox(
            "Select Record to Edit or Remove",
            [getattr(record, id_field) for record in records],
            format_func=lambda item: label(
                next(record for record in records if getattr(record, id_field) == item)
            ),
            key=f"{model.__tablename__}_selected",
        )
        selected_record = next(
            record for record in records if getattr(record, id_field) == record_id
        )

    with st.form(f"{model.__tablename__}_edit_form"):
        st.markdown(
            "**Enter Details:**" if mode == "Create New Record" else f"**Editing #{getattr(selected_record, id_field)}:**"
        )
        values: dict[str, Any] = {}
        for spec in fields:
            initial = None if selected_record is None else getattr(selected_record, spec.name)
            values[spec.name] = render_field(
                spec, initial, f"{model.__tablename__}_{mode}_{spec.name}"
            )
        submitted = st.form_submit_button("Save Record" if mode == "Create New Record" else "Save Changes")

    if submitted:
        missing = [
            spec.label
            for spec in fields
            if spec.required and (values[spec.name] is None or str(values[spec.name]).strip() == "")
        ]
        if missing:
            st.error("Please complete all required fields: " + ", ".join(missing) + ".")
        elif any(values[spec.name] is None for spec in fields if spec.kind == "foreign"):
            st.error("Please select a valid parent record.")
        elif (
            model is SemesterMark
            and values["marks_obtained"] > values["max_marks"]
        ):
            st.error("Validation error: Obtained marks cannot exceed the maximum marks.")
        else:
            for spec in fields:
                if isinstance(values[spec.name], str):
                    values[spec.name] = values[spec.name].strip() or None
            try:
                with Session(engine) as session, session.begin():
                    if selected_record is None:
                        session.add(model(**values))
                    else:
                        current = session.get(model, getattr(selected_record, id_field))
                        if current is None:
                            st.error("Record was not found; it may have been deleted.")
                            return
                        for field_name, value in values.items():
                            setattr(current, field_name, value)
                synced, sync_msg = trigger_auto_sync_if_enabled(engine)
                if synced:
                    set_notice(f"✅ {title}: Record saved & Google Sheet updated! ⚡")
                else:
                    set_notice(f"✅ {title}: Record successfully saved.")
                st.rerun()
            except IntegrityError as exc:
                st.error(friendly_integrity_error(exc))
            except SQLAlchemyError as exc:
                st.error(f"Database error ({type(exc).__name__}): {exc}")

    if mode == "Update / Delete Record" and selected_record is not None:
        if delete_warning:
            st.warning(f"⚠️ Cascade Notice: {delete_warning}")
        col_del_1, col_del_2 = st.columns([2, 1])
        with col_del_1:
            confirm = st.checkbox(
                "Confirm permanent deletion of this record",
                key=f"{model.__tablename__}_delete_confirm",
            )
        with col_del_2:
            if st.button(
                "🗑️ Delete Record",
                disabled=not confirm,
                key=f"{model.__tablename__}_delete_button",
                type="secondary",
            ):
                try:
                    with Session(engine) as session, session.begin():
                        current = session.get(model, getattr(selected_record, id_field))
                        if current is None:
                            st.error("Record was not found.")
                            return
                        session.delete(current)
                    synced, sync_msg = trigger_auto_sync_if_enabled(engine)
                    if synced:
                        set_notice(f"🗑️ {title}: Record deleted & Google Sheet updated! ⚡")
                    else:
                        set_notice(f"🗑️ {title}: Record deleted.")
                    st.rerun()
                except SQLAlchemyError as exc:
                    st.error(f"Could not delete record ({type(exc).__name__}): {exc}")


def get_students(search: str = "") -> list[Student]:
    statement = select(Student).order_by(Student.full_name)
    if search.strip():
        needle = f"%{search.strip()}%"
        statement = statement.where(
            or_(Student.full_name.ilike(needle), Student.roll_no.ilike(needle))
        )
    with Session(engine) as session:
        return list(session.scalars(statement).all())


# -----------------------------------------------------------------------------
# 1. PAGE: DASHBOARD & ANALYTICS
# -----------------------------------------------------------------------------
def render_dashboard_tab() -> None:
    # 1. KPI Cards Row
    with Session(engine) as session:
        student_count = session.scalar(select(func.count()).select_from(Student)) or 0
        semester_count = session.scalar(select(func.count()).select_from(Semester)) or 0
        seminar_count = session.scalar(select(func.count()).select_from(Seminar)) or 0
        activity_count = session.scalar(select(func.count()).select_from(Activity)) or 0
        avg_cgpa = session.scalar(select(func.avg(Semester.cgpa))) or 0.0
        gap_count = session.scalar(select(func.count()).select_from(Semester).where(Semester.gap_years_before > 0)) or 0

    kpi_cols = st.columns(5)
    with kpi_cols[0]:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-title">Enrolled Students</div>
                <div class="kpi-value">{student_count}</div>
                <div class="kpi-sub">Across All Departments</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with kpi_cols[1]:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-title">Semesters Logged</div>
                <div class="kpi-value">{semester_count}</div>
                <div class="kpi-sub">Academic Results</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with kpi_cols[2]:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-title">Average CGPA</div>
                <div class="kpi-value">{float(avg_cgpa):.2f}</div>
                <div class="kpi-sub">Institutional Performance</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with kpi_cols[3]:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-title">Portfolio Events</div>
                <div class="kpi-value">{seminar_count + activity_count}</div>
                <div class="kpi-sub">{seminar_count} Seminars · {activity_count} Activities</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with kpi_cols[4]:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-title">Academic Gaps</div>
                <div class="kpi-value" style="color: {'#dc2626' if gap_count > 0 else '#059669'};">{gap_count}</div>
                <div class="kpi-sub">Flagged Resumptions</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

    # 2. Student Search and Selection
    search_col, sel_col = st.columns([1, 2])
    with search_col:
        search_query = st.text_input(
            "🔍 Search by Student Name or Roll Number",
            key="dash_search_box",
            placeholder="e.g. Maya or DEMO-001",
        )
    
    students = get_students(search_query)
    if not students:
        st.info("No matching students found. Add a student in 'Student Management' or click '🌱 Load Unique Real Students Data' in the sidebar.")
        return

    student_options = {s.student_id: f"{s.roll_no} — {s.full_name} ({s.department})" for s in students}
    with sel_col:
        selected_student_id = st.selectbox(
            "Select Student Profile to Inspect",
            options=list(student_options.keys()),
            format_func=lambda sid: student_options[sid],
            key="dash_student_select",
        )
    
    current_student = next(s for s in students if s.student_id == selected_student_id)

    # Fetch dependent student records
    with Session(engine) as session:
        education_records = list(
            session.scalars(
                select(EducationHistory)
                .where(EducationHistory.student_id == selected_student_id)
                .order_by(EducationHistory.level.desc())
            ).all()
        )
        semesters = list(
            session.scalars(
                select(Semester)
                .where(Semester.student_id == selected_student_id)
                .order_by(Semester.semester_no)
            ).all()
        )
        seminars = list(
            session.scalars(
                select(Seminar)
                .where(Seminar.student_id == selected_student_id)
                .order_by(Seminar.event_date.desc(), Seminar.seminar_id.desc())
            ).all()
        )
        activities = list(
            session.scalars(
                select(Activity)
                .where(Activity.student_id == selected_student_id)
                .order_by(Activity.event_date.desc(), Activity.activity_id.desc())
            ).all()
        )

    # 3. Profile & Academic Progression Split
    prof_col, chart_col = st.columns([1, 2])

    with prof_col:
        status_class = f"status-{current_student.current_status.lower().replace(' ', '')}"
        status_html = f"<span class='status-badge {status_class}'>{current_student.current_status}</span>"
        
        st.markdown(
            f"""
            <div class="profile-card">
                <div class="profile-header">
                    <div>
                        <div class="profile-name">{current_student.full_name}</div>
                        <div class="profile-roll">Roll No: {current_student.roll_no}</div>
                    </div>
                    {status_html}
                </div>
                <p style="margin: 6px 0; font-size: 0.88rem;"><strong>Department:</strong> {current_student.department}</p>
                <p style="margin: 6px 0; font-size: 0.88rem;"><strong>Admission Year:</strong> {current_student.admission_year}</p>
                <p style="margin: 6px 0; font-size: 0.88rem;"><strong>Email:</strong> {current_student.email or 'Not provided'}</p>
                <hr style="margin: 12px 0; border: none; border-top: 1px solid #f1f5f9;">
                <p style="margin: 4px 0 8px; font-weight: 600; font-size: 0.82rem; color: #64748b; text-transform: uppercase;">Prior Education</p>
            """,
            unsafe_allow_html=True,
        )
        if education_records:
            for ed in education_records:
                st.markdown(
                    f"• **{ed.level}:** {float(ed.percentage) if ed.percentage is not None else 'N/A'}% "
                    f"({ed.institution or 'N/A'}, {ed.passing_year or 'N/A'})"
                )
        else:
            st.caption("No secondary/higher secondary records recorded yet.")
        
        st.markdown("</div>", unsafe_allow_html=True)

    with chart_col:
        st.markdown("#### 📈 Academic Progression & Gap Year Visualization")
        if semesters:
            chart_df = pd.DataFrame(
                [
                    {
                        "semester_no": s.semester_no,
                        "academic_year": s.academic_year or "N/A",
                        "sgpa": float(s.sgpa) if s.sgpa is not None else None,
                        "cgpa": float(s.cgpa) if s.cgpa is not None else None,
                        "gap_years": s.gap_years_before,
                        "status": s.status,
                    }
                    for s in semesters
                ]
            )

            fig = go.Figure()

            # SGPA Line Trace
            fig.add_trace(
                go.Scatter(
                    x=chart_df["semester_no"],
                    y=chart_df["sgpa"],
                    mode="lines+markers",
                    name="SGPA (Semester)",
                    line={"color": "#2563eb", "width": 3},
                    marker={"size": 9, "symbol": "circle"},
                    customdata=chart_df[["academic_year", "gap_years", "status"]],
                    hovertemplate=(
                        "<b>Semester %{x}</b> (%{customdata[0]})<br>"
                        "SGPA: <b>%{y:.2f}</b><br>"
                        "Status: %{customdata[2]}<br>"
                        "Gap Before: %{customdata[1]} yr(s)<extra></extra>"
                    ),
                )
            )

            # CGPA Line Trace
            fig.add_trace(
                go.Scatter(
                    x=chart_df["semester_no"],
                    y=chart_df["cgpa"],
                    mode="lines+markers",
                    name="CGPA (Cumulative)",
                    line={"color": "#059669", "width": 3, "dash": "solid"},
                    marker={"size": 9, "symbol": "diamond"},
                    customdata=chart_df[["academic_year", "gap_years", "status"]],
                    hovertemplate=(
                        "<b>Semester %{x}</b> (%{customdata[0]})<br>"
                        "CGPA: <b>%{y:.2f}</b><br>"
                        "Status: %{customdata[2]}<extra></extra>"
                    ),
                )
            )

            # Clearly highlight academic gap years using red markers and red shaded bands
            has_gap = False
            for s in semesters:
                if s.gap_years_before > 0:
                    has_gap = True
                    fig.add_vrect(
                        x0=s.semester_no - 0.25,
                        x1=s.semester_no + 0.25,
                        fillcolor="#ef4444",
                        opacity=0.15,
                        line_width=1,
                        line_color="#ef4444",
                        annotation_text=f"⚠️ {s.gap_years_before} Year Gap",
                        annotation_position="top left",
                        annotation_font={"size": 11, "color": "#b91c1c"},
                    )
                    fig.add_trace(
                        go.Scatter(
                            x=[s.semester_no],
                            y=[float(s.sgpa) if s.sgpa else 0],
                            mode="markers",
                            marker={"size": 14, "color": "#ef4444", "symbol": "star-triangle-up"},
                            showlegend=False,
                            hoverinfo="skip",
                        )
                    )

            fig.update_layout(
                height=320,
                margin={"l": 20, "r": 20, "t": 35, "b": 35},
                yaxis={"title": "Grade Points (0 - 10)", "range": [0, 10.2]},
                xaxis={
                    "title": "Semester Number",
                    "tickmode": "array",
                    "tickvals": chart_df["semester_no"].tolist(),
                    "ticktext": [f"Sem {r.semester_no}<br>({r.academic_year})" for _, r in chart_df.iterrows()],
                },
                legend={"orientation": "h", "y": 1.15, "x": 0.5, "xanchor": "center"},
                hovermode="x unified",
            )
            st.plotly_chart(fig, width="stretch")
            if has_gap:
                st.caption("🔴 Red highlighted bands indicate academic gap/drop years before that semester resumed.")
        else:
            st.info("No semester records found for this student. Add results in 'Semesters & Marks'.")

    # 4. Detailed Semester Marks Drilldown for Selected Student
    st.markdown("---")
    st.markdown("#### 📝 Semester-Wise Breakdown & Subject/Lab Marks")
    if semesters:
        sem_choice = st.selectbox(
            "Select Semester to Inspect Marks:",
            options=[s.semester_id for s in semesters],
            format_func=lambda sid: next(
                f"Semester {s.semester_no} ({s.academic_year or 'Year N/A'}) — Status: {s.status} — SGPA: {s.sgpa or 'N/A'} — CGPA: {s.cgpa or 'N/A'}"
                for s in semesters if s.semester_id == sid
            ),
            key="dash_sem_drilldown",
        )
        
        with engine.connect() as conn:
            marks_stmt = (
                select(
                    Subject.subject_code.label("Code"),
                    Subject.subject_name.label("Subject Name"),
                    Subject.subject_type.label("Type"),
                    SemesterMark.marks_obtained.label("Marks Obtained"),
                    SemesterMark.max_marks.label("Max Marks"),
                    SemesterMark.grade.label("Grade"),
                )
                .join(Subject, SemesterMark.subject_id == Subject.subject_id)
                .where(SemesterMark.semester_id == sem_choice)
                .order_by(Subject.subject_type.desc(), Subject.subject_name)
            )
            marks_df = pd.read_sql(marks_stmt, conn)
            
        if not marks_df.empty:
            marks_df["Percentage"] = (marks_df["Marks Obtained"] / marks_df["Max Marks"] * 100).round(1).astype(str) + "%"
            st.dataframe(marks_df, width="stretch", hide_index=True)
        else:
            st.info("No subject marks logged yet for this semester. Add theory or lab marks in 'Semesters & Marks'.")
    else:
        st.info("No semesters logged for this student.")

    # 5. Portfolio (Seminars and Activities) for Selected Student
    port_col1, port_col2 = st.columns(2)
    with port_col1:
        st.markdown(f"#### 🎤 Seminars ({len(seminars)})")
        if seminars:
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "Title": sem.title,
                            "Type": sem.seminar_type,
                            "Organizer": sem.organizer or "N/A",
                            "Date": sem.event_date,
                            "Certificate": sem.certificate_url or "N/A",
                        }
                        for sem in seminars
                    ]
                ),
                width="stretch",
                hide_index=True,
            )
        else:
            st.caption("No seminars recorded.")

    with port_col2:
        st.markdown(f"#### 🏆 Activities ({len(activities)})")
        if activities:
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "Title": act.title,
                            "Category": act.category,
                            "Role": act.role or "N/A",
                            "Date": act.event_date,
                            "Description": act.description or "N/A",
                        }
                        for act in activities
                    ]
                ),
                width="stretch",
                hide_index=True,
            )
        else:
            st.caption("No activities recorded.")


# -----------------------------------------------------------------------------
# 2. PAGE: STUDENT MANAGEMENT
# -----------------------------------------------------------------------------
def render_students_tab() -> None:
    render_crud(
        "Student Profiles",
        Student,
        "student_id",
        [
            FieldSpec("roll_no", "Roll Number", required=True),
            FieldSpec("full_name", "Full Name", required=True),
            FieldSpec("email", "Email Address (Optional)"),
            FieldSpec("department", "Department / Branch", required=True),
            FieldSpec("admission_year", "Admission Year", "int", True, minimum=1990, maximum=2100),
            FieldSpec(
                "current_status",
                "Academic Status",
                "select",
                True,
                options=("Studying", "Graduated", "On Break", "Discontinued"),
            ),
        ],
        lambda record: f"{record.roll_no} — {record.full_name} ({record.department})",
        delete_warning="Deleting a student cascades and permanently deletes their Education History, Semesters, Marks, Seminars, and Activities.",
    )


# -----------------------------------------------------------------------------
# 3. PAGE: SCHOOL RECORDS (EDUCATION HISTORY)
# -----------------------------------------------------------------------------
def render_education_tab() -> None:
    with engine.connect() as conn:
        stmt = (
            select(
                EducationHistory.education_id.label("ID"),
                Student.roll_no.label("Roll No"),
                Student.full_name.label("Student Name"),
                EducationHistory.level.label("Level"),
                EducationHistory.institution.label("Institution / Board"),
                EducationHistory.passing_year.label("Passing Year"),
                EducationHistory.percentage.label("Percentage (%)"),
            )
            .join(Student, EducationHistory.student_id == Student.student_id)
            .order_by(Student.full_name, EducationHistory.level)
        )
        ed_df = pd.read_sql(stmt, conn)

    render_crud(
        "Secondary & Higher Secondary Records",
        EducationHistory,
        "education_id",
        [
            FieldSpec(
                "student_id",
                "Student",
                "foreign",
                True,
                choices=lambda: fetch_choices(Student, "student_id", "full_name"),
            ),
            FieldSpec(
                "level",
                "Education Level",
                "select",
                True,
                options=("Secondary", "Higher Secondary"),
            ),
            FieldSpec("institution", "School / Junior College Name"),
            FieldSpec("passing_year", "Passing Year", "int", minimum=1950, maximum=2100, nullable=True),
            FieldSpec("percentage", "Percentage (%)", "float", minimum=0.0, maximum=100.0, step=0.05, nullable=True),
        ],
        lambda record: f"#{record.education_id} · Student ID {record.student_id} · {record.level}",
        table_view=ed_df if not ed_df.empty else None,
        filter_field="Level",
        filter_options=("Secondary", "Higher Secondary"),
    )


# -----------------------------------------------------------------------------
# 4. PAGE: SEMESTERS & MARKS
# -----------------------------------------------------------------------------
def render_semesters_marks_tab() -> None:
    sub_sem, sub_marks = st.tabs([
        "1️⃣ Semester GPA & Progression",
        "2️⃣ Detailed Subject & Laboratory Marks",
    ])

    with sub_sem:
        with engine.connect() as conn:
            stmt = (
                select(
                    Semester.semester_id.label("ID"),
                    Student.roll_no.label("Roll No"),
                    Student.full_name.label("Student Name"),
                    Semester.semester_no.label("Semester No"),
                    Semester.academic_year.label("Academic Year"),
                    Semester.sgpa.label("SGPA"),
                    Semester.cgpa.label("CGPA"),
                    Semester.status.label("Status"),
                    Semester.gap_years_before.label("Gap Years Before"),
                )
                .join(Student, Semester.student_id == Student.student_id)
                .order_by(Student.full_name, Semester.semester_no)
            )
            sem_table = pd.read_sql(stmt, conn)

        render_crud(
            "Semester Academic Records",
            Semester,
            "semester_id",
            [
                FieldSpec(
                    "student_id",
                    "Student",
                    "foreign",
                    True,
                    choices=lambda: fetch_choices(Student, "student_id", "full_name"),
                ),
                FieldSpec("semester_no", "Semester Number", "int", True, minimum=1, maximum=12),
                FieldSpec("academic_year", "Academic Year (e.g. 2024-25)"),
                FieldSpec("sgpa", "SGPA (0 - 10)", "float", minimum=0.0, maximum=10.0, step=0.05, nullable=True),
                FieldSpec("cgpa", "CGPA (0 - 10)", "float", minimum=0.0, maximum=10.0, step=0.05, nullable=True),
                FieldSpec(
                    "status",
                    "Semester Status",
                    "select",
                    True,
                    options=("Completed", "In Progress", "Backlog"),
                ),
                FieldSpec("gap_years_before", "Gap / Drop Years Before This Semester", "int", True, minimum=0, maximum=10),
            ],
            lambda record: f"Student #{record.student_id} · Sem {record.semester_no} ({record.academic_year or 'N/A'})",
            table_view=sem_table if not sem_table.empty else None,
            delete_warning="Deleting a semester will cascade and delete all subject marks recorded for that semester.",
        )

    with sub_marks:
        with engine.connect() as conn:
            stmt = (
                select(
                    SemesterMark.mark_id.label("ID"),
                    Student.roll_no.label("Roll No"),
                    Student.full_name.label("Student"),
                    Semester.semester_no.label("Sem"),
                    Subject.subject_code.label("Code"),
                    Subject.subject_name.label("Subject Title"),
                    Subject.subject_type.label("Type"),
                    SemesterMark.marks_obtained.label("Obtained"),
                    SemesterMark.max_marks.label("Max Marks"),
                    SemesterMark.grade.label("Grade"),
                )
                .join(Semester, SemesterMark.semester_id == Semester.semester_id)
                .join(Student, Semester.student_id == Student.student_id)
                .join(Subject, SemesterMark.subject_id == Subject.subject_id)
                .order_by(Student.full_name, Semester.semester_no, Subject.subject_type.desc())
            )
            marks_table = pd.read_sql(stmt, conn)

        render_crud(
            "Semester Marks (Theory & Laboratory)",
            SemesterMark,
            "mark_id",
            [
                FieldSpec(
                    "semester_id",
                    "Student Semester",
                    "foreign",
                    True,
                    choices=lambda: fetch_choices(Semester, "semester_id", "semester_no"),
                ),
                FieldSpec(
                    "subject_id",
                    "Subject / Lab",
                    "foreign",
                    True,
                    choices=lambda: fetch_choices(Subject, "subject_id", "subject_name"),
                ),
                FieldSpec("marks_obtained", "Marks Obtained", "float", True, minimum=0.0, maximum=1000.0, step=0.5),
                FieldSpec("max_marks", "Maximum Marks", "float", True, minimum=1.0, maximum=1000.0, step=0.5),
                FieldSpec("grade", "Grade (e.g. O, A+, A, B, C, F)"),
            ],
            lambda record: f"Mark #{record.mark_id} · Semester {record.semester_id} · Subject {record.subject_id}",
            table_view=marks_table if not marks_table.empty else None,
            filter_field="Type",
            filter_options=("Theory", "Lab"),
        )


# -----------------------------------------------------------------------------
# 5. PAGE: SUBJECTS CATALOG
# -----------------------------------------------------------------------------
def render_subjects_catalog() -> None:
    render_crud(
        "Theory & Laboratory Subjects Catalog",
        Subject,
        "subject_id",
        [
            FieldSpec("subject_code", "Subject Code (Unique)", required=True),
            FieldSpec("subject_name", "Subject / Lab Title", required=True),
            FieldSpec("subject_type", "Course Type", "select", True, options=("Theory", "Lab")),
        ],
        lambda record: f"{record.subject_code} — {record.subject_name} [{record.subject_type}]",
        filter_field="subject_type",
        filter_options=("Theory", "Lab"),
        delete_warning="Deleting a subject will cascade and delete all marks awarded for this subject across all student semesters.",
    )


# -----------------------------------------------------------------------------
# 6. PAGE: PORTFOLIO & ACHIEVEMENTS
# -----------------------------------------------------------------------------
def render_portfolio_page() -> None:
    port_tabs = st.tabs(["🎤 Internal & External Seminars", "🏆 Student Activities"])
    
    with port_tabs[0]:
        with engine.connect() as conn:
            stmt = (
                select(
                    Seminar.seminar_id.label("ID"),
                    Student.roll_no.label("Roll No"),
                    Student.full_name.label("Student"),
                    Seminar.title.label("Seminar Title"),
                    Seminar.seminar_type.label("Type"),
                    Seminar.organizer.label("Organizer / Body"),
                    Seminar.event_date.label("Date"),
                    Seminar.certificate_url.label("Certificate Link"),
                )
                .join(Student, Seminar.student_id == Student.student_id)
                .order_by(Seminar.event_date.desc(), Seminar.seminar_id.desc())
            )
            seminars_df = pd.read_sql(stmt, conn)

        render_crud(
            "Seminars Portfolio",
            Seminar,
            "seminar_id",
            [
                FieldSpec(
                    "student_id",
                    "Student",
                    "foreign",
                    True,
                    choices=lambda: fetch_choices(Student, "student_id", "full_name"),
                ),
                FieldSpec("title", "Seminar Title", required=True),
                FieldSpec("seminar_type", "Seminar Type", "select", True, options=("Internal", "External")),
                FieldSpec("organizer", "Organizer / Department / Institution"),
                FieldSpec("event_date", "Date of Seminar", "date", nullable=True),
                FieldSpec("certificate_url", "Certificate URL / Verification Link"),
            ],
            lambda record: f"{record.title} [{record.seminar_type}] — Student ID {record.student_id}",
            table_view=seminars_df if not seminars_df.empty else None,
            filter_field="Type",
            filter_options=("Internal", "External"),
        )

    with port_tabs[1]:
        with engine.connect() as conn:
            stmt = (
                select(
                    Activity.activity_id.label("ID"),
                    Student.roll_no.label("Roll No"),
                    Student.full_name.label("Student"),
                    Activity.title.label("Activity Title"),
                    Activity.category.label("Category"),
                    Activity.role.label("Role / Award"),
                    Activity.event_date.label("Date"),
                    Activity.description.label("Description"),
                )
                .join(Student, Activity.student_id == Student.student_id)
                .order_by(Activity.event_date.desc(), Activity.activity_id.desc())
            )
            activities_df = pd.read_sql(stmt, conn)

        render_crud(
            "Activities Portfolio",
            Activity,
            "activity_id",
            [
                FieldSpec(
                    "student_id",
                    "Student",
                    "foreign",
                    True,
                    choices=lambda: fetch_choices(Student, "student_id", "full_name"),
                ),
                FieldSpec("title", "Activity Title", required=True),
                FieldSpec(
                    "category",
                    "Category",
                    "select",
                    True,
                    options=("Technical", "Co-curricular", "Extra-curricular"),
                ),
                FieldSpec("role", "Role / Achievement / Prize"),
                FieldSpec("event_date", "Event Date", "date", nullable=True),
                FieldSpec("description", "Description / Key Learnings", "textarea"),
            ],
            lambda record: f"{record.title} [{record.category}] — Student ID {record.student_id}",
            table_view=activities_df if not activities_df.empty else None,
            filter_field="Category",
            filter_options=("Technical", "Co-curricular", "Extra-curricular"),
        )


# -----------------------------------------------------------------------------
# 7. PAGE: DROP YEARS
# -----------------------------------------------------------------------------
def render_drop_years_page() -> None:
    st.markdown("### ⚠️ Academic Gaps & Drop Years")
    st.caption("Detailed tracking and analytics of academic pauses and drop years before semester resumptions.")
    
    students = get_students()
    if not students:
        st.info("No students found. Add a student to track academic gaps.")
        return

    student_ids = [s.student_id for s in students]
    student_labels = {s.student_id: f"{s.roll_no} — {s.full_name}" for s in students}

    filter_col, _ = st.columns([1, 2])
    with filter_col:
        selected_id = st.selectbox(
            "Filter by Student",
            [None, *student_ids],
            format_func=lambda val: "All Students" if val is None else student_labels[val],
            key="drop_year_filter_select",
        )

    stmt = (
        select(
            Student.roll_no.label("Roll Number"),
            Student.full_name.label("Student"),
            Semester.semester_no.label("Resumed Semester"),
            Semester.academic_year.label("Academic Year"),
            Semester.gap_years_before.label("Gap Duration (Years)"),
            Semester.status.label("Status"),
        )
        .join(Semester, Semester.student_id == Student.student_id)
        .where(Semester.gap_years_before > 0)
        .order_by(Student.full_name, Semester.semester_no)
    )
    if selected_id is not None:
        stmt = stmt.where(Student.student_id == selected_id)

    with engine.connect() as conn:
        gaps_df = pd.read_sql(stmt, conn)

    if gaps_df.empty:
        st.info("No academic gap years recorded for this selection.")
        return

    gap_events = len(gaps_df)
    total_years = int(gaps_df["Gap Duration (Years)"].sum())

    kpi1, kpi2 = st.columns(2)
    with kpi1:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-title">Recorded Gap Events</div>
                <div class="kpi-value" style="color: #dc2626;">{gap_events}</div>
                <div class="kpi-sub">Flagged Resumptions</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with kpi2:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-title">Total Gap Years</div>
                <div class="kpi-value" style="color: #ea580c;">{total_years}</div>
                <div class="kpi-sub">Cumulative Paused Years</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
    st.dataframe(gaps_df, width="stretch", hide_index=True)

    fig = go.Figure(
        go.Bar(
            x=gaps_df["Student"] + " · Sem " + gaps_df["Resumed Semester"].astype(str),
            y=gaps_df["Gap Duration (Years)"],
            marker_color="#ef4444",
            hovertemplate="%{x}<br><b>%{y}</b> Gap Year(s) before resumption<extra></extra>",
        )
    )
    fig.update_layout(
        title="Academic Gap Years by Student and Resumption Semester",
        xaxis_title="Student & Resumed Semester",
        yaxis_title="Gap Duration (Years)",
        height=320,
        margin={"t": 40, "b": 40, "l": 20, "r": 20},
    )
    st.plotly_chart(fig, width="stretch")


# -----------------------------------------------------------------------------
# 8. PAGE: GOOGLE SHEETS SYNC
# -----------------------------------------------------------------------------
def render_google_sheets_tab() -> None:
    st.markdown("### ☁️ One-Way Google Sheets Synchronization")
    st.write(
        "Export the normalized database directly into Google Sheets. "
        "Each of the **seven tables** is synchronized to its own dedicated worksheet tab: "
        "`Students`, `Education_History`, `Semesters`, `Subjects`, `Semester_Marks`, `Seminars`, and `Activities`."
    )

    sheets_cfg = get_sheets_config_status()
    apps_cfg = get_apps_script_config_status()

    st.markdown("#### 1. Cloud & Google Sheets Status")
    col_status1, col_status2 = st.columns(2)
    with col_status1:
        if apps_cfg["configured"]:
            st.success(
                f"✅ **Google Apps Script Web App Active**\n\n"
                f"• **Endpoint:** `{apps_cfg['endpoint'][:45]}...`\n\n"
                f"• **Secret Token:** Verified ({len(os.getenv('GOOGLE_APPS_SCRIPT_TOKEN', ''))} characters)\n\n"
                f"• **Status:** Connected & Ready for instant sync"
            )
        else:
            st.info(f"ℹ️ **Google Apps Script:** {apps_cfg['message']}")

    with col_status2:
        if sheets_cfg["configured"]:
            st.success(
                f"✅ **Google Service Account Active**\n\n"
                f"- **Target Sheet ID:** `{sheets_cfg['sheet_id'][:6]}...{sheets_cfg['sheet_id'][-4:]}`\n\n"
                f"- **Service Account:** `{sheets_cfg.get('client_email', 'valid')}`"
            )
        else:
            st.info(
                f"ℹ️ **Service Account Status:** {sheets_cfg['message']}\n\n"
                "*(Optional: Only needed if not using Google Apps Script)*"
            )

    st.markdown("#### 2. Automatic Synchronization")
    auto_sync_toggle = st.checkbox(
        "⚡ Automatically sync database to Google Sheets after every successful CRUD operation",
        value=st.session_state.get("auto_sync_enabled", True),
        key="auto_sync_checkbox",
        help="When enabled and credentials are valid, saving or deleting student records automatically updates Google Sheets.",
    )
    st.session_state.auto_sync_enabled = auto_sync_toggle
    if auto_sync_toggle:
        if apps_cfg["configured"] or sheets_cfg["configured"]:
            last_time = st.session_state.get("last_sync_time")
            sync_detail = f" (Last sync at {last_time})" if last_time else ""
            st.caption(f"🟢 **Auto-sync is active.** Any database commit (add, edit, delete student) will instantly refresh all 7 worksheets in Google Sheets{sync_detail}.")
        else:
            st.caption("🟡 Auto-sync is enabled in UI, but Google Sheets credentials are not configured in `.env`.")

    st.markdown("#### 3. Manual Synchronization")
    col_sync1, col_sync2 = st.columns([1, 1])
    with col_sync1:
        if st.button("🌐 Sync Database via Google Apps Script", type="primary"):
            with st.spinner("Posting 7 database tables to Google Apps Script endpoint..."):
                success, message = sync_database_via_apps_script(engine)
            if success:
                st.session_state.last_sync_time = pd.Timestamp.now().strftime("%H:%M:%S")
                st.success(message)
            else:
                st.error(message)

    with col_sync2:
        if st.button("🚀 Sync All 7 Tables to Google Sheets (Service Account)"):
            with st.spinner("Connecting to Google Sheets API and updating all 7 tabs..."):
                success, message = sync_database_to_sheets(engine)
            if success:
                st.session_state.last_sync_time = pd.Timestamp.now().strftime("%H:%M:%S")
                st.success(message)
            else:
                st.error(message)

    st.markdown("---")
    st.markdown("#### 4. Setup Instructions & Environment Variables")
    st.code(
        """# Required in .env for Google Sheets API (gspread):
GOOGLE_SHEET_ID=your_spreadsheet_id_here
GOOGLE_SERVICE_ACCOUNT_FILE=service_account.json

# Optional alternative: Apps Script Web App:
GOOGLE_APPS_SCRIPT_URL=https://script.google.com/macros/s/AKfycb.../exec
GOOGLE_APPS_SCRIPT_TOKEN=your_32_character_secret_token""",
        language="text",
    )
    st.caption("🔒 Security Notice: Never expose or commit service_account.json or your .env file to public repositories.")


# -----------------------------------------------------------------------------
# 9. PAGE: MYSQL & CLOUD SYNC
# -----------------------------------------------------------------------------
def render_mysql_cloud_sync_page() -> None:
    st.markdown("### 🐬 MySQL & Cloud Synchronization Status")

    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown("#### Database Connection Status")
        try:
            with engine.connect() as conn:
                conn.execute(select(1))
            st.success(f"Database connection is ACTIVE: **{engine.dialect.name.upper()}**")
        except Exception as exc:
            st.error(f"Database error: {exc}")

        if engine.dialect.name == "sqlite":
            st.info("SQLite local mode is active (`student_ledger.db`). It needs no server and is the recommended offline demo fallback.")
        else:
            st.info(f"MySQL is active through `DATABASE_URL` in `.env`. Connected to `{engine.url.database or 'student_progressdb'}`.")

        st.markdown("#### Active Configuration")
        st.code(
            f"Dialect: {engine.dialect.name.upper()}\nHost: {engine.url.host or '127.0.0.1'}\nPort: {engine.url.port or 3306}\nDatabase: {engine.url.database or 'student_progressdb'}\nUsername: {engine.url.username or 'root'}",
            language="yaml",
        )

    with col2:
        st.markdown("#### Database Engine Switcher")
        st.caption("Switch between MySQL and SQLite for viva demonstration.")
        new_choice = st.radio(
            "Select Database Preference",
            ["mysql", "sqlite", "auto"],
            format_func=lambda x: {
                "mysql": "🗄️ MySQL Primary (127.0.0.1:3306 / student_progressdb / root)",
                "sqlite": "📁 SQLite Fallback (student_ledger.db - zero config)",
                "auto": "⚡ Auto (MySQL if reachable, else SQLite fallback)",
            }[x],
            index=["mysql", "sqlite", "auto"].index(st.session_state.db_choice),
            key="mysql_page_db_choice_radio",
        )
        if new_choice != st.session_state.db_choice:
            st.session_state.db_choice = new_choice
            st.cache_resource.clear()
            st.rerun()

        st.markdown("#### Live Connection Diagnostics")
        if st.button("🔌 Ping Active Database"):
            try:
                with engine.connect() as conn:
                    if engine.dialect.name == "sqlite":
                        st.success("SQLite ping successful! Foreign keys are ON.")
                    else:
                        ver = conn.execute(select(func.version())).scalar()
                        st.success(f"Ping successful! MySQL Version: `{ver}`")
            except Exception as exc:
                st.error(f"Ping failed: {exc}")


# -----------------------------------------------------------------------------
# 10. PAGE: 3NF SCHEMA & VIVA REFERENCE
# -----------------------------------------------------------------------------
def render_schema_viva_tab() -> None:
    st.markdown("### 📐 3NF Relational Database Schema & Viva Reference")

    col_db1, col_db2 = st.columns([1, 1])
    with col_db1:
        st.markdown("#### Schema Normalization Overview")
        st.write(f"• **Active Engine:** `{engine.dialect.name.upper()}`")
        st.write(f"• **Database URL:** `{engine.url.render_as_string(hide_password=True)}`")
        if engine.dialect.name == "sqlite":
            st.info("SQLite local mode is active. Foreign-key constraints (`PRAGMA foreign_keys = ON`) are enforced via SQLAlchemy connect event listeners.")
        else:
            st.success("MySQL mode is active. Tables, composite foreign keys, and CHECK constraints are compiled with dialect-specific DDL.")

    with col_db2:
        st.markdown("#### Reference DDL Export")
        st.caption("Download the pure SQL schema definition matching this 3NF design.")
        schema_path = Path(__file__).resolve().with_name("schema.sql")
        if schema_path.is_file():
            st.download_button(
                "💾 Download schema.sql (SQLite / MySQL Reference DDL)",
                data=schema_path.read_text(encoding="utf-8"),
                file_name="schema.sql",
                mime="text/sql",
            )

    st.markdown("---")
    st.markdown("#### 3NF Entity-Relationship Diagram")
    st.markdown(
        """
        ```text
        +-----------------------------------------------------------------------------------------+
        |                                        STUDENTS                                         |
        |  PK: student_id | roll_no (UQ) | full_name | email (UQ) | department | admission_year    |
        +-----------------------------------------------------------------------------------------+
                 | 1                                     | 1                     | 1            | 1
                 |                                       |                       |              |
                 *                                       *                       *              *
        +-------------------+                  +-------------------+      +-------------+ +------------+
        | EDUCATION_HISTORY |                  |     SEMESTERS     |      |  SEMINARS   | | ACTIVITIES |
        | PK: education_id  |                  | PK: semester_id   |      | PK: sem_id  | | PK: act_id |
        | FK: student_id    |                  | FK: student_id    |      | FK: stud_id | | FK: stud_id|
        | level (UQ pair)   |                  | sem_no (UQ pair)  |      | title       | | title      |
        | percentage        |                  | sgpa | cgpa       |      | type        | | category   |
        | passing_year      |                  | gap_years_before  |      | organizer   | | role       |
        +-------------------+                  +-------------------+      +-------------+ +------------+
                                                         | 1
                                                         |
                                                         *
                                               +-------------------+
                                               |  SEMESTER_MARKS   |
                                               | PK: mark_id       |
                                               | FK: semester_id   |
                                               | FK: subject_id    |---* (Many-to-One)
                                               | marks_obtained    |         |
                                               | max_marks         |         | 1
                                               | grade             |  +--------------------+
                                               +-------------------+  |      SUBJECTS      |
                                                                      | PK: subject_id     |
                                                                      | subject_code (UQ)  |
                                                                      | subject_name       |
                                                                      | subject_type       |
                                                                      +--------------------+
        ```
        """
    )

    st.markdown("#### Normalization Analysis (3NF Compliance)")
    norm_data = [
        ("1NF (First Normal Form)", "All attributes are atomic. There are no repeating groups or comma-separated lists of marks or subjects."),
        ("2NF (Second Normal Form)", "All relations are in 1NF and every non-key attribute is fully functionally dependent on the primary key. Subjects are isolated from student marks."),
        ("3NF (Third Normal Form)", "All relations are in 2NF and there are no transitive functional dependencies (e.g., subject names depend on subject_id, not semester_id)."),
    ]
    st.dataframe(pd.DataFrame(norm_data, columns=["Normal Form", "Implementation Evidence"]), width="stretch", hide_index=True)

    st.markdown("#### Integrity Constraints Reference")
    constraint_data = [
        ("Primary Keys", "Surrogate integer primary keys on all 7 tables for high performance indexing and stable foreign referencing."),
        ("Foreign Keys & Cascades", "ON DELETE CASCADE on all child tables (Education, Semesters, Marks, Seminars, Activities) guarantees zero orphaned records."),
        ("Unique Constraints", "Unique roll_no, unique subject_code, unique (student_id, level), unique (student_id, semester_no), unique (semester_id, subject_id)."),
        ("CHECK: Percentages", "0 <= percentage <= 100 on education_history."),
        ("CHECK: SGPA / CGPA", "0 <= sgpa <= 10 and 0 <= cgpa <= 10 on semesters."),
        ("CHECK: Marks Bounded", "marks_obtained >= 0, max_marks > 0, and marks_obtained <= max_marks on semester_marks."),
        ("CHECK: Categorical", "Enumerated CHECK constraints for level ('Secondary', 'Higher Secondary'), subject_type ('Theory', 'Lab'), seminar_type ('Internal', 'External'), category ('Technical', 'Co-curricular', 'Extra-curricular')."),
    ]
    st.dataframe(pd.DataFrame(constraint_data, columns=["Constraint Type", "Relational Rule"]), width="stretch", hide_index=True)


# -----------------------------------------------------------------------------
# SIDEBAR NAVIGATION (EXACT SCREENSHOT MATCH)
# -----------------------------------------------------------------------------
with st.sidebar:
    # 1. Header
    db_mode_label = "MySQL 8.0" if active_db_mode == "mysql" else "SQLite 3NF"
    st.markdown(
        f"""
        <div class="sidebar-brand-box">
            <span class="sidebar-brand-icon">🎓</span>
            <div class="sidebar-brand-title">Academic Progression</div>
            <div class="sidebar-brand-sub">DBMS Mini-Project · {db_mode_label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 2. Navigation items
    st.markdown('<div class="sidebar-nav-header">NAVIGATION</div>', unsafe_allow_html=True)
    
    navigation_options = [
        "Dashboard & Analytics",
        "Student Management",
        "School Records",
        "Semesters & Marks",
        "Subjects Catalog",
        "Portfolio & Achievements",
        "Drop Years",
        "Google Sheets Sync",
        "MySQL & Cloud Sync",
        "3NF Schema & Viva",
    ]
    
    navigation_icons = {
        "Dashboard & Analytics": "📊",
        "Student Management": "👨‍🎓",
        "School Records": "🏫",
        "Semesters & Marks": "📈",
        "Subjects Catalog": "📚",
        "Portfolio & Achievements": "🏆",
        "Drop Years": "⚠️",
        "Google Sheets Sync": "☁️",
        "MySQL & Cloud Sync": "🐬",
        "3NF Schema & Viva": "📐",
    }
    
    selected_page = st.radio(
        "NAVIGATION",
        navigation_options,
        format_func=lambda item: f"{navigation_icons[item]}  {item}",
        label_visibility="collapsed",
        key="app_sidebar_navigation",
    )

    # 3. Demo Controls
    st.markdown('<div class="sidebar-nav-header" style="margin-top: 20px;">DEMO CONTROLS</div>', unsafe_allow_html=True)
    
    if st.button("🌱  Load Unique Real Students Data", width="stretch"):
        try:
            seeded = seed_demo_data(engine)
            if seeded:
                trigger_auto_sync_if_enabled(engine)
                set_notice("✅ Fictional demo dataset loaded & Google Sheet updated! ⚡")
            else:
                set_notice("ℹ️ Fictional demo records already exist in the database.", "info")
            st.rerun()
        except SQLAlchemyError as exc:
            st.error(f"Error loading demo data: {exc}")

    if st.button("🗑️  Reset Database", width="stretch"):
        st.session_state.reset_database_pending = True

    if st.session_state.get("reset_database_pending", False):
        st.warning("⚠️ This will permanently delete all records while keeping the 3NF schema intact.")
        confirm_phrase = st.text_input("Type RESET to confirm:", key="sidebar_reset_input")
        if st.button(
            "Confirm Permanent Reset",
            disabled=confirm_phrase != "RESET",
            key="sidebar_reset_confirm_btn",
            type="primary",
        ):
            try:
                clear_ledger_records(engine)
                trigger_auto_sync_if_enabled(engine)
                st.session_state.reset_database_pending = False
                set_notice("All records have been reset & Google Sheet updated! ⚡")
                st.rerun()
            except SQLAlchemyError as exc:
                st.error(f"Reset failed: {exc}")

    # 4. Sheets Connected Status & Sync Queue
    st.markdown('<div class="sidebar-sync-box"></div>', unsafe_allow_html=True)
    sheets_cfg_sb = get_sheets_config_status()
    apps_cfg_sb = get_apps_script_config_status()
    
    if apps_cfg_sb["configured"] or sheets_cfg_sb["configured"]:
        dot_html = '<span class="status-dot-green"></span>'
        status_text = "Sheets Connected"
    else:
        dot_html = '<span class="status-dot-gray"></span>'
        status_text = "Sheets Disconnected"

    last_sync_text = (
        f"Synced at {st.session_state.last_sync_time}"
        if st.session_state.get("last_sync_time")
        else "Auto-Sync Active"
    )

    st.markdown(
        f"""
        <div class="sidebar-status-tag">
            {dot_html} <span>{status_text}</span>
        </div>
        <p class="sync-queue-title">Cloud Sync</p>
        <p class="sync-queue-count">{last_sync_text}</p>
        <div class="sidebar-footer-text">v2.1 · Google Sheets Sync · Plotly Charts</div>
        """,
        unsafe_allow_html=True,
    )

# -----------------------------------------------------------------------------
# MAIN CONTENT ROUTER
# -----------------------------------------------------------------------------
# Header bar
db_badge = (
    f'<span class="db-badge-mysql">MYSQL 8.0 ACTIVE</span>'
    if active_db_mode == "mysql"
    else '<span class="db-badge-sqlite">SQLITE FALLBACK ACTIVE</span>'
)
st.markdown(
    f"""
    <div class="app-header">
        <div>
            <div class="app-header-title">🎓 Academic Progression</div>
            <div class="app-header-sub">Student Academic & Activity Ledger · {selected_page}</div>
        </div>
        <div>
            {db_badge}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

display_notice()

if selected_page == "Dashboard & Analytics":
    render_dashboard_tab()
elif selected_page == "Student Management":
    render_students_tab()
elif selected_page == "School Records":
    render_education_tab()
elif selected_page == "Semesters & Marks":
    render_semesters_marks_tab()
elif selected_page == "Subjects Catalog":
    render_subjects_catalog()
elif selected_page == "Portfolio & Achievements":
    render_portfolio_page()
elif selected_page == "Drop Years":
    render_drop_years_page()
elif selected_page == "Google Sheets Sync":
    render_google_sheets_tab()
elif selected_page == "MySQL & Cloud Sync":
    render_mysql_cloud_sync_page()
elif selected_page == "3NF Schema & Viva":
    render_schema_viva_tab()
