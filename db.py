from __future__ import annotations

import os
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    delete,
    event,
    func,
    select,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Student(Base):
    __tablename__ = "students"
    __table_args__ = (
        CheckConstraint("admission_year BETWEEN 1990 AND 2100", name="ck_students_admission_year"),
        CheckConstraint(
            "current_status IN ('Studying', 'Graduated', 'On Break', 'Discontinued')",
            name="ck_students_status",
        ),
    )

    student_id: Mapped[int] = mapped_column(primary_key=True)
    roll_no: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str | None] = mapped_column(String(150), unique=True)
    department: Mapped[str] = mapped_column(String(120), nullable=False)
    admission_year: Mapped[int] = mapped_column(Integer, nullable=False)
    current_status: Mapped[str] = mapped_column(String(30), nullable=False, default="Studying")
    created_at: Mapped[Any] = mapped_column(DateTime, nullable=False, server_default=func.now())

    education_history: Mapped[list[EducationHistory]] = relationship(
        back_populates="student", cascade="all, delete-orphan", passive_deletes=True
    )
    semesters: Mapped[list[Semester]] = relationship(
        back_populates="student", cascade="all, delete-orphan", passive_deletes=True
    )
    seminars: Mapped[list[Seminar]] = relationship(
        back_populates="student", cascade="all, delete-orphan", passive_deletes=True
    )
    activities: Mapped[list[Activity]] = relationship(
        back_populates="student", cascade="all, delete-orphan", passive_deletes=True
    )


class EducationHistory(Base):
    __tablename__ = "education_history"
    __table_args__ = (
        UniqueConstraint("student_id", "level", name="uq_education_student_level"),
        CheckConstraint("level IN ('Secondary', 'Higher Secondary')", name="ck_education_level"),
        CheckConstraint(
            "percentage IS NULL OR percentage BETWEEN 0 AND 100", name="ck_education_percentage"
        ),
        CheckConstraint(
            "passing_year IS NULL OR passing_year BETWEEN 1950 AND 2100",
            name="ck_education_passing_year",
        ),
    )

    education_id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.student_id", ondelete="CASCADE"), nullable=False
    )
    level: Mapped[str] = mapped_column(String(30), nullable=False)
    institution: Mapped[str | None] = mapped_column(String(180))
    passing_year: Mapped[int | None] = mapped_column(Integer)
    percentage: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))

    student: Mapped[Student] = relationship(back_populates="education_history")


class Semester(Base):
    __tablename__ = "semesters"
    __table_args__ = (
        UniqueConstraint("student_id", "semester_no", name="uq_semester_student_number"),
        CheckConstraint("semester_no BETWEEN 1 AND 12", name="ck_semester_number"),
        CheckConstraint("sgpa IS NULL OR sgpa BETWEEN 0 AND 10", name="ck_semester_sgpa"),
        CheckConstraint("cgpa IS NULL OR cgpa BETWEEN 0 AND 10", name="ck_semester_cgpa"),
        CheckConstraint("gap_years_before >= 0", name="ck_semester_gap_years"),
        CheckConstraint(
            "status IN ('Completed', 'In Progress', 'Backlog')", name="ck_semester_status"
        ),
    )

    semester_id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.student_id", ondelete="CASCADE"), nullable=False
    )
    semester_no: Mapped[int] = mapped_column(Integer, nullable=False)
    academic_year: Mapped[str | None] = mapped_column(String(20))
    sgpa: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    cgpa: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="Completed")
    gap_years_before: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    student: Mapped[Student] = relationship(back_populates="semesters")
    marks: Mapped[list[SemesterMark]] = relationship(
        back_populates="semester", cascade="all, delete-orphan", passive_deletes=True
    )


class Subject(Base):
    __tablename__ = "subjects"
    __table_args__ = (CheckConstraint("subject_type IN ('Theory', 'Lab')", name="ck_subject_type"),)

    subject_id: Mapped[int] = mapped_column(primary_key=True)
    subject_code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    subject_name: Mapped[str] = mapped_column(String(180), nullable=False)
    subject_type: Mapped[str] = mapped_column(String(20), nullable=False)

    marks: Mapped[list[SemesterMark]] = relationship(
        back_populates="subject", cascade="all, delete-orphan", passive_deletes=True
    )


class SemesterMark(Base):
    __tablename__ = "semester_marks"
    __table_args__ = (
        UniqueConstraint("semester_id", "subject_id", name="uq_mark_semester_subject"),
        CheckConstraint("marks_obtained >= 0", name="ck_mark_nonnegative"),
        CheckConstraint("max_marks > 0", name="ck_mark_max_positive"),
        CheckConstraint("marks_obtained <= max_marks", name="ck_mark_not_over_max"),
    )

    mark_id: Mapped[int] = mapped_column(primary_key=True)
    semester_id: Mapped[int] = mapped_column(
        ForeignKey("semesters.semester_id", ondelete="CASCADE"), nullable=False
    )
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.subject_id", ondelete="CASCADE"), nullable=False
    )
    marks_obtained: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    max_marks: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, default=100)
    grade: Mapped[str | None] = mapped_column(String(5))

    semester: Mapped[Semester] = relationship(back_populates="marks")
    subject: Mapped[Subject] = relationship(back_populates="marks")


class Seminar(Base):
    __tablename__ = "seminars"
    __table_args__ = (
        CheckConstraint("seminar_type IN ('Internal', 'External')", name="ck_seminar_type"),
    )

    seminar_id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.student_id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    seminar_type: Mapped[str] = mapped_column(String(20), nullable=False)
    organizer: Mapped[str | None] = mapped_column(String(180))
    event_date: Mapped[date | None] = mapped_column(Date)
    certificate_url: Mapped[str | None] = mapped_column(String(500))

    student: Mapped[Student] = relationship(back_populates="seminars")


class Activity(Base):
    __tablename__ = "activities"
    __table_args__ = (
        CheckConstraint(
            "category IN ('Technical', 'Co-curricular', 'Extra-curricular')",
            name="ck_activity_category",
        ),
    )

    activity_id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.student_id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    role: Mapped[str | None] = mapped_column(String(100))
    event_date: Mapped[date | None] = mapped_column(Date)
    description: Mapped[str | None] = mapped_column(Text)

    student: Mapped[Student] = relationship(back_populates="activities")


def make_engine(database_url: str | None = None) -> Engine:
    """Create a SQLAlchemy engine and enable SQLite foreign-key enforcement."""
    url = database_url or os.getenv("DATABASE_URL", "sqlite:///student_ledger.db")
    options: dict[str, Any] = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
    engine = create_engine(url, **options)

    if engine.dialect.name == "sqlite":
        @event.listens_for(engine, "connect")
        def enable_sqlite_foreign_keys(dbapi_connection: Any, _: Any) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def get_database_engine(choice: str = "auto") -> tuple[Engine, str, str | None]:
    """Return a configured database engine with fallback handling.

    choice can be 'auto', 'mysql', or 'sqlite'.
    Returns: (engine, active_mode, note_or_warning)
    """
    mysql_url = os.getenv("DATABASE_URL", "").strip()

    if choice == "sqlite" or (choice == "auto" and not mysql_url):
        eng = make_engine("sqlite:///student_ledger.db")
        return eng, "sqlite", "SQLite local mode is active (student_ledger.db). No external server required."

    target_url = mysql_url or "mysql+pymysql://root:vyomesh%40_123@127.0.0.1:3306/student_progressdb"
    try:
        eng = make_engine(target_url)
        with eng.connect() as conn:
            conn.execute(select(1))
        db_name = eng.url.database or "student_progressdb"
        return eng, "mysql", f"Connected to MySQL server ({db_name})."
    except Exception as exc:
        fallback_eng = make_engine("sqlite:///student_ledger.db")
        warning = (
            f"Could not connect to MySQL server ({type(exc).__name__}). "
            "Automatically switched to SQLite fallback (student_ledger.db) for an uninterrupted demo."
        )
        return fallback_eng, "sqlite", warning


def initialize_database(engine: Engine) -> None:
    Base.metadata.create_all(engine)


def clear_ledger_records(engine: Engine) -> None:
    """Delete all ledger rows while retaining the schema and constraints."""
    with Session(engine) as session, session.begin():
        session.execute(delete(Student))
        session.execute(delete(Subject))


def seed_demo_data(engine: Engine) -> bool:
    """Insert a comprehensive, fictional dataset once. Return False if already present."""
    with Session(engine) as session:
        if session.scalar(select(Student.student_id).where(Student.roll_no == "DEMO-001")):
            return False

        # 1. Students (All 4 statuses represented)
        maya = Student(
            roll_no="DEMO-001",
            full_name="Maya Example",
            email="maya.example@demo.invalid",
            department="Computer Engineering",
            admission_year=2023,
            current_status="Studying",
        )
        arjun = Student(
            roll_no="DEMO-002",
            full_name="Arjun Sample",
            email="arjun.sample@demo.invalid",
            department="Electrical Engineering",
            admission_year=2022,
            current_status="On Break",
        )
        priya = Student(
            roll_no="DEMO-003",
            full_name="Priya Sharma",
            email="priya.sharma@demo.invalid",
            department="Information Technology",
            admission_year=2021,
            current_status="Graduated",
        )
        rahul = Student(
            roll_no="DEMO-004",
            full_name="Rahul Verma",
            email="rahul.verma@demo.invalid",
            department="Mechanical Engineering",
            admission_year=2023,
            current_status="Studying",
        )
        session.add_all([maya, arjun, priya, rahul])
        session.flush()

        # 2. Education History (Secondary & Higher Secondary)
        session.add_all(
            [
                EducationHistory(
                    student=maya, level="Secondary", institution="Demo Model High School",
                    passing_year=2021, percentage=Decimal("91.20"),
                ),
                EducationHistory(
                    student=maya, level="Higher Secondary", institution="Demo Junior College of Science",
                    passing_year=2023, percentage=Decimal("88.40"),
                ),
                EducationHistory(
                    student=arjun, level="Secondary", institution="St. Jude High School",
                    passing_year=2020, percentage=Decimal("84.50"),
                ),
                EducationHistory(
                    student=arjun, level="Higher Secondary", institution="Modern Science Junior College",
                    passing_year=2022, percentage=Decimal("79.00"),
                ),
                EducationHistory(
                    student=priya, level="Secondary", institution="National Public School",
                    passing_year=2019, percentage=Decimal("93.60"),
                ),
                EducationHistory(
                    student=priya, level="Higher Secondary", institution="Metro State PU College",
                    passing_year=2021, percentage=Decimal("90.50"),
                ),
                EducationHistory(
                    student=rahul, level="Secondary", institution="City Central High School",
                    passing_year=2021, percentage=Decimal("78.40"),
                ),
                EducationHistory(
                    student=rahul, level="Higher Secondary", institution="Vidya Vikas College",
                    passing_year=2023, percentage=Decimal("76.20"),
                ),
            ]
        )

        # 3. Semesters (showing progression, backlogs, and gap years)
        m_sem1 = Semester(student=maya, semester_no=1, academic_year="2023-24", sgpa=8.10, cgpa=8.10, status="Completed")
        m_sem2 = Semester(student=maya, semester_no=2, academic_year="2023-24", sgpa=8.40, cgpa=8.25, status="Completed")
        m_sem3 = Semester(student=maya, semester_no=3, academic_year="2024-25", sgpa=7.90, cgpa=8.13, status="Completed")
        m_sem4 = Semester(student=maya, semester_no=4, academic_year="2025-26", sgpa=8.80, cgpa=8.30, status="Completed", gap_years_before=1)

        a_sem1 = Semester(student=arjun, semester_no=1, academic_year="2022-23", sgpa=7.60, cgpa=7.60, status="Completed")
        a_sem2 = Semester(student=arjun, semester_no=2, academic_year="2022-23", sgpa=7.20, cgpa=7.40, status="Completed")
        a_sem3 = Semester(student=arjun, semester_no=3, academic_year="2024-25", sgpa=7.80, cgpa=7.53, status="In Progress", gap_years_before=1)

        p_sem1 = Semester(student=priya, semester_no=1, academic_year="2021-22", sgpa=9.10, cgpa=9.10, status="Completed")
        p_sem2 = Semester(student=priya, semester_no=2, academic_year="2021-22", sgpa=9.30, cgpa=9.20, status="Completed")
        p_sem3 = Semester(student=priya, semester_no=3, academic_year="2022-23", sgpa=9.00, cgpa=9.13, status="Completed")
        p_sem4 = Semester(student=priya, semester_no=4, academic_year="2022-23", sgpa=9.40, cgpa=9.20, status="Completed")

        r_sem1 = Semester(student=rahul, semester_no=1, academic_year="2023-24", sgpa=6.80, cgpa=6.80, status="Completed")
        r_sem2 = Semester(student=rahul, semester_no=2, academic_year="2023-24", sgpa=6.20, cgpa=6.50, status="Backlog")
        r_sem3 = Semester(student=rahul, semester_no=3, academic_year="2024-25", sgpa=7.50, cgpa=6.83, status="Completed")

        session.add_all([
            m_sem1, m_sem2, m_sem3, m_sem4,
            a_sem1, a_sem2, a_sem3,
            p_sem1, p_sem2, p_sem3, p_sem4,
            r_sem1, r_sem2, r_sem3,
        ])

        # 4. Subjects (Theory and Lab catalogues)
        sub_cs101 = Subject(subject_code="DEMO-CS101", subject_name="Programming Fundamentals", subject_type="Theory")
        sub_csL1 = Subject(subject_code="DEMO-CSL101", subject_name="Programming Lab", subject_type="Lab")
        sub_cs201 = Subject(subject_code="DEMO-CS201", subject_name="Data Structures & Algorithms", subject_type="Theory")
        sub_csL2 = Subject(subject_code="DEMO-CSL201", subject_name="Data Structures Lab", subject_type="Lab")
        sub_ee101 = Subject(subject_code="DEMO-EE101", subject_name="Basic Electrical Engineering", subject_type="Theory")
        sub_eeL1 = Subject(subject_code="DEMO-EEL101", subject_name="Electrical Circuits Lab", subject_type="Lab")
        sub_it301 = Subject(subject_code="DEMO-IT301", subject_name="Database Management Systems", subject_type="Theory")
        sub_itL1 = Subject(subject_code="DEMO-ITL301", subject_name="DBMS & SQL Lab", subject_type="Lab")
        sub_me101 = Subject(subject_code="DEMO-ME101", subject_name="Engineering Mechanics", subject_type="Theory")
        sub_meL1 = Subject(subject_code="DEMO-MEL101", subject_name="Workshop Practice Lab", subject_type="Lab")

        session.add_all([
            sub_cs101, sub_csL1, sub_cs201, sub_csL2,
            sub_ee101, sub_eeL1, sub_it301, sub_itL1,
            sub_me101, sub_meL1,
        ])

        # 5. Seminars (Internal & External)
        session.add_all(
            [
                Seminar(
                    student=maya, title="Responsible AI & Algorithmic Ethics", seminar_type="Internal",
                    organizer="College CSE Department", event_date=date(2025, 8, 15),
                    certificate_url="https://example.invalid/cert/ai-ethics",
                ),
                Seminar(
                    student=maya, title="Open Source Software & Git Best Practices", seminar_type="External",
                    organizer="FOSS Community Pune", event_date=date(2025, 11, 4),
                    certificate_url="https://example.invalid/cert/foss-git",
                ),
                Seminar(
                    student=arjun, title="Solar Photovoltaic Grid Integration", seminar_type="Internal",
                    organizer="EEE Society", event_date=date(2024, 3, 20),
                ),
                Seminar(
                    student=priya, title="Cloud-Native Microservices & Kubernetes", seminar_type="External",
                    organizer="TechCon India", event_date=date(2023, 2, 18),
                    certificate_url="https://example.invalid/cert/k8s-cloud",
                ),
            ]
        )

        # 6. Activities (Technical, Co-curricular, Extra-curricular)
        session.add_all(
            [
                Activity(
                    student=maya, title="Smart Campus Autonomous Rover Challenge", category="Technical",
                    role="Team Lead / Embedded Dev", event_date=date(2025, 9, 10),
                    description="Designed Arduino-based obstacle-avoiding campus rover; placed 1st.",
                ),
                Activity(
                    student=maya, title="Annual Coding Marathon 2024", category="Co-curricular",
                    role="Coordinator", event_date=date(2024, 10, 5),
                    description="Managed student registrations and problem statement publishing.",
                ),
                Activity(
                    student=arjun, title="University Music Symphony", category="Extra-curricular",
                    role="Lead Guitarist", event_date=date(2024, 12, 2),
                    description="Performed in the annual inter-college cultural festival.",
                ),
                Activity(
                    student=priya, title="Smart India Hackathon 2022", category="Technical",
                    role="Full Stack Developer", event_date=date(2022, 8, 25),
                    description="Built AI-assisted farmer crop health advisory portal; national finalist.",
                ),
                Activity(
                    student=priya, title="Department Student Council", category="Co-curricular",
                    role="President", event_date=date(2023, 1, 15),
                    description="Elected as student president to represent 400+ undergraduate students.",
                ),
                Activity(
                    student=rahul, title="SAE BAJA All-Terrain Vehicle Fabrication", category="Technical",
                    role="Chassis & Suspension Lead", event_date=date(2024, 2, 12),
                    description="Fabricated roll cage and tuned dual A-arm suspension for BAJA.",
                ),
                Activity(
                    student=rahul, title="Inter-Branch Cricket Tournament", category="Extra-curricular",
                    role="Team Captain", event_date=date(2024, 11, 20),
                    description="Captained the Mechanical branch team to championship victory.",
                ),
            ]
        )

        session.flush()

        # 7. Semester Marks (Theory & Lab marks with bounds validation)
        session.add_all(
            [
                # Maya Sem 1
                SemesterMark(
                    semester=m_sem1, subject=sub_cs101,
                    marks_obtained=Decimal("84"), max_marks=Decimal("100"), grade="A",
                ),
                SemesterMark(
                    semester=m_sem1, subject=sub_csL1,
                    marks_obtained=Decimal("46"), max_marks=Decimal("50"), grade="A",
                ),
                # Maya Sem 2
                SemesterMark(
                    semester=m_sem2, subject=sub_cs201,
                    marks_obtained=Decimal("88"), max_marks=Decimal("100"), grade="A+",
                ),
                SemesterMark(
                    semester=m_sem2, subject=sub_csL2,
                    marks_obtained=Decimal("48"), max_marks=Decimal("50"), grade="O",
                ),
                # Arjun Sem 1
                SemesterMark(
                    semester=a_sem1, subject=sub_ee101,
                    marks_obtained=Decimal("74"), max_marks=Decimal("100"), grade="B+",
                ),
                SemesterMark(
                    semester=a_sem1, subject=sub_eeL1,
                    marks_obtained=Decimal("42"), max_marks=Decimal("50"), grade="A",
                ),
                # Priya Sem 3
                SemesterMark(
                    semester=p_sem3, subject=sub_it301,
                    marks_obtained=Decimal("92"), max_marks=Decimal("100"), grade="O",
                ),
                SemesterMark(
                    semester=p_sem3, subject=sub_itL1,
                    marks_obtained=Decimal("49"), max_marks=Decimal("50"), grade="O",
                ),
                # Rahul Sem 1
                SemesterMark(
                    semester=r_sem1, subject=sub_me101,
                    marks_obtained=Decimal("65"), max_marks=Decimal("100"), grade="B",
                ),
                SemesterMark(
                    semester=r_sem1, subject=sub_meL1,
                    marks_obtained=Decimal("42"), max_marks=Decimal("50"), grade="A",
                ),
            ]
        )

        session.commit()
        return True

