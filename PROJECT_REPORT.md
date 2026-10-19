# DBMS Mini-Project Report

## Project Title
**Comprehensive Student Academic & Activity Ledger**

---

## 1. Objective
Academic progression and extracurricular achievements are frequently stored in disconnected spreadsheets or isolated departmental systems. This makes tracking overall student growth, validating prerequisites, auditing academic gap years, and compiling comprehensive portfolios difficult and prone to data inconsistencies.

The objective of this project is to design, normalize, and implement a robust Relational Database Management System (RDBMS) that tracks:
1. Core student biographical data and current academic status.
2. Prior secondary and higher secondary educational qualifications.
3. Semester-by-semester grade point averages (SGPA and CGPA) and recorded gap/drop years.
4. Detailed theory course marks and laboratory marks.
5. Internal and external seminar presentations.
6. Co-curricular, technical, and extracurricular activities.
7. One-way automated synchronization to Google Sheets for institutional reporting.

---

## 2. Technology Stack & Architecture

- **User Interface:** Streamlit (Python web dashboard with custom CSS design, KPI cards, and tab navigation)
- **Database Layer:** SQLAlchemy 2.0 ORM (parameterized SQL queries, dialect-independent execution)
- **Primary Database:** MySQL 8.0 (strict relational constraints, foreign keys, and check constraints)
- **Fallback Database:** SQLite 3 (zero-configuration local database file `student_ledger.db` with `PRAGMA foreign_keys = ON`)
- **Data Analytics & Charting:** Pandas & Plotly Graph Objects (SGPA/CGPA line charts, red gap year annotations)
- **Cloud Synchronization:** Google Sheets API via `gspread` and service account authentication

---

## 3. Entity-Relationship (ER) Design

### Conceptual ER Relationships
```text
Students (1) ───────< (M) Education_History
Students (1) ───────< (M) Semesters (1) ───────< (M) Semester_Marks (M) >─────── (1) Subjects
Students (1) ───────< (M) Seminars
Students (1) ───────< (M) Activities
```

### Relational Schema Design
1. **`students`**
   - Attributes: `student_id` (PK), `roll_no` (UQ), `full_name`, `email` (UQ), `department`, `admission_year`, `current_status`, `created_at`
2. **`education_history`**
   - Attributes: `education_id` (PK), `student_id` (FK), `level`, `institution`, `passing_year`, `percentage`
   - Constraints: Composite UNIQUE (`student_id`, `level`)
3. **`semesters`**
   - Attributes: `semester_id` (PK), `student_id` (FK), `semester_no`, `academic_year`, `sgpa`, `cgpa`, `status`, `gap_years_before`
   - Constraints: Composite UNIQUE (`student_id`, `semester_no`)
4. **`subjects`**
   - Attributes: `subject_id` (PK), `subject_code` (UQ), `subject_name`, `subject_type`
5. **`semester_marks`**
   - Attributes: `mark_id` (PK), `semester_id` (FK), `subject_id` (FK), `marks_obtained`, `max_marks`, `grade`
   - Constraints: Composite UNIQUE (`semester_id`, `subject_id`), CHECK (`marks_obtained` $\le$ `max_marks`)
6. **`seminars`**
   - Attributes: `seminar_id` (PK), `student_id` (FK), `title`, `seminar_type`, `organizer`, `event_date`, `certificate_url`
7. **`activities`**
   - Attributes: `activity_id` (PK), `student_id` (FK), `title`, `category`, `role`, `event_date`, `description`

---

## 4. Database Normalization (Up to 3NF)

The database was rigorously structured to satisfy the Third Normal Form (3NF):

### First Normal Form (1NF)
- Every column contains atomic (indivisible) values. There are no comma-separated lists of subjects, marks, or multiple seminar entries stored within a single field.
- Each table defines a surrogate integer primary key.
- Each record within a relation is distinct and uniquely identifiable.

### Second Normal Form (2NF)
- The schema satisfies 1NF.
- There are no partial dependencies: in composite candidate keys (such as `student_id` + `semester_no` or `semester_id` + `subject_id`), all non-prime attributes are functionally dependent on the entire composite key.
- Course catalogues are decoupled: `subjects` stores subject details (`subject_name`, `subject_type`) independently of `semester_marks`, preventing partial dependency on student enrollments.

### Third Normal Form (3NF)
- The schema satisfies 2NF.
- There are no transitive functional dependencies ($X \to Y$ and $Y \to Z$).
- Non-key attributes depend only on the primary key:
  - Student details (such as department or admission year) depend only on `student_id`.
  - Marks awarded depend strictly on the pair (`semester_id`, `subject_id`).
  - Subject descriptions depend strictly on `subject_id`.
- Modifying a subject's title or student's email address requires updating exactly one row in one table, eliminating update, insertion, and deletion anomalies.

---

## 5. Integrity Constraints

1. **Entity Integrity (Primary Keys):**
   - Every table enforces an `INTEGER PRIMARY KEY` (mapped to `AUTO_INCREMENT` in MySQL).
2. **Referential Integrity (Foreign Keys & Cascades):**
   - Child records in `education_history`, `semesters`, `seminars`, and `activities` link to `students(student_id)` with `ON DELETE CASCADE`.
   - `semester_marks` links to both `semesters(semester_id)` and `subjects(subject_id)` with `ON DELETE CASCADE`. Deleting a semester or a subject automatically cleans up associated score records.
3. **Domain & Check Constraints:**
   - **Percentages:** `percentage BETWEEN 0 AND 100`
   - **Grade Points:** `sgpa BETWEEN 0 AND 10`, `cgpa BETWEEN 0 AND 10`
   - **Academic Bounds:** `semester_no BETWEEN 1 AND 12`, `gap_years_before >= 0`
   - **Mark Validity:** `marks_obtained >= 0`, `max_marks > 0`, and `marks_obtained <= max_marks`
   - **Categorical Integrity:**
     - `current_status IN ('Studying', 'Graduated', 'On Break', 'Discontinued')`
     - `level IN ('Secondary', 'Higher Secondary')`
     - `subject_type IN ('Theory', 'Lab')`
     - `seminar_type IN ('Internal', 'External')`
     - `category IN ('Technical', 'Co-curricular', 'Extra-curricular')`
4. **Key Uniqueness Constraints:**
   - `roll_no` and `email` are unique in `students`.
   - `subject_code` is unique in `subjects`.
   - Composite uniqueness prevents duplicate marks for the same subject in the same semester (`semester_id`, `subject_id`).

---

## 6. Application Modules

1. **Dashboard & Analytics:** Real-time KPI summary counters, student search bar, student profile card, interactive Plotly progression chart tracking SGPA/CGPA with red highlighted bands and markers for academic gaps, and semester-level subject/lab marks drilldown.
2. **Student Management:** Full CRUD operations for student profiles with uniqueness validation.
3. **Education History:** Secondary and higher secondary records tracking percentages, passing years, and institutions.
4. **Semester Results & Marks:** Three sub-modules managing semester GPAs, subject catalogues (Theory vs. Lab), and individual subject/lab marks with boundary checks.
5. **Seminars Portfolio:** Categorized internal vs. external seminar presentations with certificate links.
6. **Activities Portfolio:** Technical, co-curricular, and extracurricular activities tracking achievements and roles.
7. **Google Sheets Sync:** Real-time configuration verification, one-way table export across seven worksheet tabs, and optional automatic synchronization upon database CRUD commits.
8. **Database & 3NF Viva Guide:** Runtime database engine switcher (MySQL / SQLite), ER diagrams, normalization walkthrough, constraint reference, and DDL export.

---

## 7. Testing & Verification

Automated unit tests (`tests/test_database.py`) and manual verification were conducted:

- **Idempotent Demo Seeding:** Verified insertion of four diverse student profiles (representing all statuses, gap years, theory/lab marks, and activities) without key collision on repeated runs.
- **Cascade Deletion:** Verified that deleting a student deletes all linked education records, semesters, marks, seminars, and activities with zero orphaned rows.
- **Boundary Validation:** Verified that entering marks exceeding `max_marks`, SGPA $> 10$, or percentages $> 100$ triggers immediate database-level `IntegrityError` rejections.
- **Dialect Portability:** Tested compilation of both MySQL DDL and SQLite in-memory DDL.
- **Server Health Check:** Confirmed Streamlit serves HTTP 200 on port 8501 and gracefully manages connections across both engines.

---

## 8. Instructions for Demonstration Screenshots

For the final viva and project submission, take the following screenshots:

1. **Dashboard Overview:** Display KPI metric cards, selected student profile (`Maya Example`), and the Plotly SGPA/CGPA line graph displaying the red shaded area marking the 1-year academic gap before Semester 4.
2. **Student Management CRUD:** Display the students table and the create/update input form.
3. **Education History:** Display Secondary and Higher Secondary school percentages and passing years.
4. **Semester Results & Lab Marks:**
   - Sub-tab 1 showing semester-level GPA progression.
   - Sub-tab 3 showing marks filtered by `Lab` and `Theory`.
5. **Portfolio Filters:**
   - Seminars tab filtered by `Internal` and `External`.
   - Activities tab filtered by `Technical` and `Extra-curricular`.
6. **Database Engine Switcher:** Sidebar/Tab 8 showing active connection to MySQL and fallback to SQLite.
7. **Google Sheets Sync:** Tab 7 showing the service account status and the one-way synchronization trigger.

---

## 9. Limitations & Future Scope

- **One-Way Sync:** Synchronization is unidirectional (Database $\to$ Google Sheets) to prevent unvalidated spreadsheet overwrites from corrupting relational integrity. Two-way synchronization with conflict resolution is a future enhancement.
- **Authentication & Roles:** The current implementation is designed for single-operator college demonstrations; role-based access control (Student vs. Faculty vs. Admin) can be added for multi-tenant deployment.
- **File Storage:** Certificate URLs are stored as web references; direct blob/PDF file uploads to cloud storage (e.g. AWS S3 or Google Drive) could be integrated.

---

## 10. Conclusion

The **Comprehensive Student Academic & Activity Ledger** successfully demonstrates a normalized 3NF relational database implemented using industry-standard engineering practices. By combining Python, Streamlit, SQLAlchemy, MySQL, SQLite, and Plotly, the project balances academic rigor with an intuitive graphical interface suitable for faculty evaluation and student portfolio tracking.
