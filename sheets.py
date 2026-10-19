from __future__ import annotations

import json
import os
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from typing import Any

import pandas as pd
from sqlalchemy import Table, select
from sqlalchemy.engine import Engine

from db import Base


SHEET_TABLES = {
    "Students": "students",
    "Education_History": "education_history",
    "Semesters": "semesters",
    "Subjects": "subjects",
    "Semester_Marks": "semester_marks",
    "Seminars": "seminars",
    "Activities": "activities",
}


class _GoogleScriptRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, request, file, code, message, headers, new_url):
        parsed_url = urlparse(new_url)
        if parsed_url.scheme != "https" or parsed_url.netloc not in {
            "script.google.com",
            "script.googleusercontent.com",
        }:
            raise URLError("Apps Script redirected outside Google's script hosts.")
        return super().redirect_request(request, file, code, message, headers, new_url)


def _table_values(engine: Engine, table_name: str) -> tuple[list[str], list[list[str]]]:
    table: Table = Base.metadata.tables[table_name]
    with engine.connect() as connection:
        frame = pd.read_sql(select(table), connection)
    rows = [
        ["" if pd.isna(value) else str(value) for value in row]
        for row in frame.itertuples(index=False, name=None)
    ]
    return frame.columns.tolist(), rows


def sync_database_to_sheets(engine: Engine) -> tuple[bool, str]:
    """Replace the seven spreadsheet worksheets with the current database tables."""
    sheet_id = os.getenv("GOOGLE_SHEET_ID", "").strip()
    credentials_setting = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "").strip()
    if not sheet_id or not credentials_setting:
        return False, "Set GOOGLE_SHEET_ID and GOOGLE_SERVICE_ACCOUNT_FILE in .env first."
    if not re.fullmatch(r"[A-Za-z0-9_-]{20,}", sheet_id):
        return False, "GOOGLE_SHEET_ID does not look like a valid spreadsheet ID."

    credentials_path = Path(credentials_setting)
    if not credentials_path.is_absolute():
        credentials_path = Path(__file__).resolve().parent / credentials_path
    if not credentials_path.is_file():
        return False, "The configured service-account JSON file was not found."
    try:
        with credentials_path.open("r", encoding="utf-8") as file:
            credential_data = json.load(file)
    except json.JSONDecodeError:
        return False, "The service-account file is not valid JSON."
    except OSError:
        return False, "The service-account JSON file could not be read."
    if not isinstance(credential_data, dict) or not all(
        credential_data.get(key) for key in ("client_email", "private_key", "token_uri")
    ):
        return False, "The JSON file is missing required Google service-account fields."

    try:
        import gspread
        from google.auth.exceptions import GoogleAuthError
        from google.oauth2.service_account import Credentials
    except ImportError:
        return False, "Google Sheets dependencies are missing. Install requirements.txt and retry."

    try:
        credentials = Credentials.from_service_account_file(
            str(credentials_path),
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        spreadsheet = gspread.authorize(credentials).open_by_key(sheet_id)
        for worksheet_title, table_name in SHEET_TABLES.items():
            headers, rows = _table_values(engine, table_name)
            values = [headers, *rows]

            try:
                worksheet = spreadsheet.worksheet(worksheet_title)
            except gspread.WorksheetNotFound:
                worksheet = spreadsheet.add_worksheet(
                    title=worksheet_title,
                    rows=max(len(values) + 10, 100),
                    cols=max(len(headers) + 2, 10),
                )
            worksheet.clear()
            worksheet.update(values=values, value_input_option="RAW")
    except (gspread.exceptions.GSpreadException, GoogleAuthError, OSError, ValueError) as exc:
        return False, f"Google Sheets sync failed ({type(exc).__name__}): {exc}. Verify sharing, API access, and configuration."

    return True, "All seven database tables were successfully synchronized to Google Sheets."


def sync_database_via_apps_script(engine: Engine) -> tuple[bool, str]:
    """POST all seven database tables to a compatible Google Apps Script web app."""
    endpoint = os.getenv("GOOGLE_APPS_SCRIPT_URL", "").strip()
    token = os.getenv("GOOGLE_APPS_SCRIPT_TOKEN", "").strip()
    if not endpoint or not token:
        return False, "Set GOOGLE_APPS_SCRIPT_URL and GOOGLE_APPS_SCRIPT_TOKEN in .env first."
    if len(token) < 32:
        return False, "GOOGLE_APPS_SCRIPT_TOKEN must be at least 32 characters."

    parsed_url = urlparse(endpoint)
    if (
        parsed_url.scheme != "https"
        or parsed_url.netloc != "script.google.com"
        or not parsed_url.path.startswith("/macros/s/")
        or not parsed_url.path.endswith("/exec")
    ):
        return False, "GOOGLE_APPS_SCRIPT_URL must be a Google Apps Script HTTPS /exec URL."

    tables = {}
    for worksheet_title, table_name in SHEET_TABLES.items():
        headers, rows = _table_values(engine, table_name)
        tables[worksheet_title] = {"headers": headers, "rows": rows}

    payload = json.dumps(
        {"action": "replace_all", "token": token, "tables": tables},
        ensure_ascii=True,
    ).encode("utf-8")
    request = Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        opener = build_opener(_GoogleScriptRedirectHandler())
        with opener.open(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        return False, f"Apps Script sync failed with HTTP {exc.code}."
    except (URLError, TimeoutError, OSError):
        return False, "Could not reach the Apps Script endpoint. Check its deployment and network access."
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False, "Apps Script returned an unreadable response; verify the documented response contract."

    if not isinstance(result, dict) or result.get("ok") is not True:
        return False, "Apps Script did not confirm the sync. Verify its token and request contract."
    return True, "All seven database tables were synchronized through Google Apps Script."


def get_sheets_config_status() -> dict[str, Any]:
    """Inspect environment and filesystem for Google Sheets Service Account configuration."""
    sheet_id = os.getenv("GOOGLE_SHEET_ID", "").strip()
    creds_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "").strip()
    
    status = {
        "configured": False,
        "sheet_id": sheet_id,
        "creds_file": creds_file,
        "file_exists": False,
        "valid_json": False,
        "has_required_keys": False,
        "message": "",
    }
    
    if not sheet_id or not creds_file:
        status["message"] = "GOOGLE_SHEET_ID or GOOGLE_SERVICE_ACCOUNT_FILE is not set in .env."
        return status

    creds_path = Path(creds_file)
    if not creds_path.is_absolute():
        creds_path = Path(__file__).resolve().parent / creds_path

    if not creds_path.is_file():
        status["message"] = f"Service account file '{creds_file}' was not found on disk."
        return status
    status["file_exists"] = True

    try:
        with creds_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        status["valid_json"] = True
    except Exception as exc:
        status["message"] = f"Service account file is not valid JSON: {exc}"
        return status

    if isinstance(data, dict) and all(data.get(k) for k in ("client_email", "private_key", "token_uri")):
        status["has_required_keys"] = True
        status["configured"] = True
        status["client_email"] = data.get("client_email", "")
        status["message"] = f"Ready to sync. Service Account: {data.get('client_email')}"
    else:
        status["message"] = "Service account JSON is missing required fields (client_email, private_key, token_uri)."

    return status


def get_apps_script_config_status() -> dict[str, Any]:
    """Inspect environment for Apps Script configuration."""
    endpoint = os.getenv("GOOGLE_APPS_SCRIPT_URL", "").strip()
    token = os.getenv("GOOGLE_APPS_SCRIPT_TOKEN", "").strip()
    
    status = {
        "configured": False,
        "endpoint": endpoint,
        "has_token": bool(token),
        "valid_token_length": len(token) >= 32,
        "message": "",
    }
    
    if not endpoint or not token:
        status["message"] = "GOOGLE_APPS_SCRIPT_URL or GOOGLE_APPS_SCRIPT_TOKEN is not set in .env."
        return status
        
    if len(token) < 32:
        status["message"] = "Token must be at least 32 characters."
        return status
        
    status["configured"] = True
    status["message"] = "Apps Script endpoint and token configured."
    return status

