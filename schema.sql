-- SQLite reference schema. The application creates the equivalent schema
-- through SQLAlchemy, which emits dialect-specific DDL for MySQL as well.
PRAGMA foreign_keys = ON;

CREATE TABLE students (
    student_id INTEGER PRIMARY KEY,
    roll_no TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    email TEXT UNIQUE,
    department TEXT NOT NULL,
    admission_year INTEGER NOT NULL CHECK (admission_year BETWEEN 1990 AND 2100),
    current_status TEXT NOT NULL DEFAULT 'Studying'
        CHECK (current_status IN ('Studying', 'Graduated', 'On Break', 'Discontinued')),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE education_history (
    education_id INTEGER PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    level TEXT NOT NULL CHECK (level IN ('Secondary', 'Higher Secondary')),
    institution TEXT,
    passing_year INTEGER CHECK (passing_year IS NULL OR passing_year BETWEEN 1950 AND 2100),
    percentage NUMERIC(5, 2)
        CHECK (percentage IS NULL OR percentage BETWEEN 0 AND 100),
    CONSTRAINT uq_education_student_level UNIQUE (student_id, level)
);

CREATE TABLE semesters (
    semester_id INTEGER PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    semester_no INTEGER NOT NULL CHECK (semester_no BETWEEN 1 AND 12),
    academic_year TEXT,
    sgpa NUMERIC(4, 2) CHECK (sgpa IS NULL OR sgpa BETWEEN 0 AND 10),
    cgpa NUMERIC(4, 2) CHECK (cgpa IS NULL OR cgpa BETWEEN 0 AND 10),
    status TEXT NOT NULL DEFAULT 'Completed'
        CHECK (status IN ('Completed', 'In Progress', 'Backlog')),
    gap_years_before INTEGER NOT NULL DEFAULT 0 CHECK (gap_years_before >= 0),
    CONSTRAINT uq_semester_student_number UNIQUE (student_id, semester_no)
);

CREATE TABLE subjects (
    subject_id INTEGER PRIMARY KEY,
    subject_code TEXT NOT NULL UNIQUE,
    subject_name TEXT NOT NULL,
    subject_type TEXT NOT NULL CHECK (subject_type IN ('Theory', 'Lab'))
);

CREATE TABLE semester_marks (
    mark_id INTEGER PRIMARY KEY,
    semester_id INTEGER NOT NULL REFERENCES semesters(semester_id) ON DELETE CASCADE,
    subject_id INTEGER NOT NULL REFERENCES subjects(subject_id) ON DELETE CASCADE,
    marks_obtained NUMERIC(6, 2) NOT NULL CHECK (marks_obtained >= 0),
    max_marks NUMERIC(6, 2) NOT NULL CHECK (max_marks > 0),
    grade TEXT,
    CONSTRAINT uq_mark_semester_subject UNIQUE (semester_id, subject_id),
    CONSTRAINT ck_mark_not_over_max CHECK (marks_obtained <= max_marks)
);

CREATE TABLE seminars (
    seminar_id INTEGER PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    seminar_type TEXT NOT NULL CHECK (seminar_type IN ('Internal', 'External')),
    organizer TEXT,
    event_date DATE,
    certificate_url TEXT
);

CREATE TABLE activities (
    activity_id INTEGER PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    category TEXT NOT NULL
        CHECK (category IN ('Technical', 'Co-curricular', 'Extra-curricular')),
    role TEXT,
    event_date DATE,
    description TEXT
);
