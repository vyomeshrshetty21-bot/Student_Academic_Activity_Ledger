# Comprehensive Student Academic & Activity Ledger

A modern, normalized DBMS mini-project for managing a student's educational history, semester progression, theory and laboratory marks, seminars, and activities. Built with **Streamlit**, **SQLAlchemy**, and **Plotly**, featuring **MySQL** as the primary database with a transparent **SQLite** fallback, and one-way synchronization to **Google Sheets**.

---

## 1. Technology Stack

- **Frontend & GUI:** Streamlit (interactive tabs, KPI cards, CRUD dialogs, responsive layout)
- **Database Layer:** SQLAlchemy ORM (3NF normalized schema, parameterized queries, cross-database compatibility)
- **Primary Database:** MySQL 8.0 (configured via `DATABASE_URL` in `.env`)
- **Fallback Database:** SQLite (`student_ledger.db`, zero-configuration local execution)
- **Analytics & Visualization:** Plotly Graph Objects & Pandas (SGPA/CGPA progression lines, red gap year annotations)
- **Cloud Integration:** Google Sheets API via `gspread` (service account JSON authentication) & Google Apps Script web receiver

---

## 2. Windows Quick Start (Ready for Demonstration)

### Option A: Direct Launch using existing Virtual Environment

Open PowerShell in the project directory:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

### Option B: Fresh Installation from Scratch

If setting up on a new PC:

```powershell
# 1. Create and activate virtual environment
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Upgrade pip and install dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 3. Launch Streamlit application
streamlit run app.py
```

> **Note on Database Execution:** The application automatically tests for MySQL. If MySQL is not running or not configured, it immediately falls back to local SQLite (`student_ledger.db`) without crashing. You can switch between MySQL and SQLite at any time using the sidebar selector.

---

## 3. Database Setup & Configuration

### A. SQLite (Zero-Setup Fallback)
No configuration required. The file `student_ledger.db` is created automatically on startup with all tables, check constraints, and foreign key cascades.

### B. MySQL Setup (Primary Database)
1. Ensure your MySQL server (v8.0.16+) is running.
2. In MySQL Workbench or MySQL CLI, create the database:
   ```sql
   CREATE DATABASE student_progressdb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```
3. Copy `.env.example` to `.env` and configure your credentials:
   ```text
   DATABASE_URL=mysql+pymysql://root:your_password@127.0.0.1:3306/student_progressdb
   ```
4. Restart the Streamlit app. The application creates all tables and foreign-key constraints on first launch.

---

## 4. Application Tabs & Features

The dashboard provides eight specialized tabs:

1. **📊 Dashboard:**
   - Real-time KPI summary cards (Enrolled Students, Semesters Logged, Institutional Average CGPA, Portfolio Events, Academic Gaps).
   - Search by student name or roll number.
   - Student Profile Card with department, admission year, and status badges (`Studying`, `Graduated`, `On Break`, `Discontinued`).
   - Dynamic **Plotly Line Chart** tracking SGPA and CGPA progression across semesters. Academic gap years are highlighted with red markers, callouts, and shaded vertical bands.
   - Semester drilldown showing individual Theory and Lab marks for the selected semester.
   - Quick portfolio cards for recent seminars and activities.

2. **🎓 Student Management:**
   - Full CRUD (Create, Read, Update, Delete) for student records.
   - Form validation for unique roll numbers, unique emails, and valid admission years (1990–2100).
   - Deletion safety notice indicating cascading removal of dependent records.

3. **🏫 Education History:**
   - Track Secondary and Higher Secondary school performance.
   - Enforces percentage limits (0.0 to 100.0%) and passing years (1950–2100).
   - Unique composite constraint: one Secondary and one Higher Secondary record per student.

4. **📝 Semester Results and Subject/Lab Marks:**
   - Organized into three sub-sections:
     - **Semester GPA & Progression:** Track semester numbers (1–12), academic year, SGPA, CGPA, status, and gap years before resumption.
     - **Subject Catalogue:** Theory and Laboratory courses with unique subject codes.
     - **Detailed Subject/Lab Marks:** Theory/Lab filter, obtained marks validation (marks obtained $\le$ maximum marks), and letter grades.

5. **🎤 Seminars:**
   - Filter portfolio records by **Internal** vs. **External** seminars.
   - Filter by individual student.
   - Record title, organizer, event date, and certificate verification link.

6. **🏆 Activities:**
   - Filter portfolio records by category: **Technical**, **Co-curricular**, or **Extra-curricular**.
   - Filter by individual student.
   - Record role, achievements, dates, and learning descriptions.

7. **☁️ Google Sheets Synchronization:**
   - Live diagnostic check for Google Cloud service account file (`service_account.json`) and spreadsheet ID.
   - **One-Way Sync Button:** Overwrites destination spreadsheet tabs (`Students`, `Education_History`, `Semesters`, `Subjects`, `Semester_Marks`, `Seminars`, and `Activities`) with current database contents.
   - **Automatic Sync Toggle:** When enabled with valid credentials, every database CRUD operation automatically refreshes Google Sheets.
   - Alternative Apps Script web receiver support.

8. **📐 Database & 3NF Schema (Viva Reference):**
   - Active database engine inspection and runtime engine switcher (MySQL / SQLite).
   - Comprehensive ASCII and Mermaid Entity-Relationship diagrams.
   - Detailed viva guide for 1NF, 2NF, and 3NF normalization.
   - Table of primary keys, foreign keys, cascades, and check constraints.
   - Download button for reference `schema.sql`.

---

## 5. Google Sheets Integration Guide (Optional)

1. Go to the [Google Cloud Console](https://console.cloud.google.com/) and create a project.
2. Enable the **Google Sheets API**.
3. Create a **Service Account**, generate a JSON key, and save it in the project root as `service_account.json`.
4. Create a new Google Spreadsheet in Google Drive. Copy its Spreadsheet ID from the URL:
   `https://docs.google.com/spreadsheets/d/<SPREADSHEET_ID>/edit`
5. Share the spreadsheet with the `client_email` listed inside `service_account.json` (grant **Editor** permission).
6. In `.env`, add:
   ```text
   GOOGLE_SHEET_ID=your_spreadsheet_id_here
   GOOGLE_SERVICE_ACCOUNT_FILE=service_account.json
   ```
7. In the Streamlit app under **Google Sheets Synchronization**, click **Sync All 7 Tables to Google Sheets**.

---

## 6. Testing & Integrity Verification

Run the automated test suite in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The test suite verifies:
- Idempotent seeding of fictional student demo data
- Cascade deletion behavior across all child tables
- Boundary validation (percentage $\le 100$, obtained marks $\le$ max marks, SGPA $\le 10$)
- MySQL and SQLite DDL generation and check constraints
- Google Sheets configuration error handling and payload formatting

---

## 7. Instructions for College Demonstration & Screenshots

For your mini-project presentation or project report, capture the following screenshots:

1. **Dashboard & KPIs:** Select student `DEMO-001 (Maya Example)` to display the KPI cards, profile details, and the Plotly progression chart showing SGPA/CGPA with the red 1-year gap highlight before Semester 4.
2. **Student Management:** Show the student table and the "Create New Record" or "Update / Delete Record" form.
3. **Education History:** Show Secondary and Higher Secondary records with percentages.
4. **Semester Results & Marks:**
   - Capture Sub-tab 1 showing semester progression.
   - Capture Sub-tab 3 filtered by `Lab` and then `Theory`.
5. **Portfolio Filters:**
   - Capture **Seminars** filtered by `External`.
   - Capture **Activities** filtered by `Technical` and `Co-curricular`.
6. **Database Engine Switcher:** In the sidebar or Tab 8, demonstrate switching from MySQL to SQLite.
7. **Google Sheets Sync:** Display the synchronization status card and setup guide.
