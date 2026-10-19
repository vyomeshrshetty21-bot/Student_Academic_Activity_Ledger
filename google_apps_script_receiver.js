/**
 * Google Apps Script Web App Receiver
 * Student Academic & Activity Ledger Synchronization
 * 
 * Paste this code into your Google Apps Script editor (Extensions -> Apps Script),
 * then deploy as a Web App (Execute as: Me, Who has access: Anyone).
 */

const SHEET_NAMES = [
  "Students",
  "Education_History",
  "Semesters",
  "Subjects",
  "Semester_Marks",
  "Seminars",
  "Activities",
];

// Fallback token if not set in Script Properties
const DEFAULT_TOKEN = "ledger_sync_token_948f2c3b8a1e7d0f4a2b6c8e0d1f3a5b";

function doGet(e) {
  return jsonResponse({
    status: "ready",
    service: "Student Academic & Activity Ledger Sync Receiver",
    timestamp: new Date().toISOString(),
    supported_tables: SHEET_NAMES
  });
}

function doPost(event) {
  try {
    const properties = PropertiesService.getScriptProperties();
    const expectedToken = properties.getProperty("SYNC_TOKEN") || DEFAULT_TOKEN;
    const spreadsheetId = properties.getProperty("SPREADSHEET_ID");

    let spreadsheet;
    if (spreadsheetId) {
      spreadsheet = SpreadsheetApp.openById(spreadsheetId);
    } else {
      spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    }

    if (!spreadsheet) {
      return jsonResponse({
        ok: false,
        message: "Spreadsheet not found. Bind this script to a Google Sheet (Extensions -> Apps Script) or add SPREADSHEET_ID to Script Properties."
      });
    }

    if (!event || !event.postData || !event.postData.contents) {
      return jsonResponse({ ok: false, message: "A JSON request body is required." });
    }

    const payload = JSON.parse(event.postData.contents);
    if (payload.token !== expectedToken) {
      return jsonResponse({ ok: false, message: "Invalid sync token." });
    }
    if (payload.action !== "replace_all" || !payload.tables) {
      return jsonResponse({ ok: false, message: "Unsupported request action." });
    }
    if (
      Object.keys(payload.tables).length !== SHEET_NAMES.length ||
      SHEET_NAMES.some((name) => !Object.prototype.hasOwnProperty.call(payload.tables, name))
    ) {
      return jsonResponse({ ok: false, message: "The request must contain all seven tables." });
    }

    SHEET_NAMES.forEach((name) => {
      const table = payload.tables[name];
      if (
        !table ||
        !Array.isArray(table.headers) ||
        table.headers.length === 0 ||
        !Array.isArray(table.rows) ||
        table.rows.some((row) => !Array.isArray(row) || row.length !== table.headers.length)
      ) {
        throw new Error("Invalid table data for sheet: " + name);
      }

      let sheet = spreadsheet.getSheetByName(name);
      if (!sheet) {
        sheet = spreadsheet.insertSheet(name);
      }
      sheet.clearContents();
      sheet.getRange(1, 1, 1, table.headers.length).setValues([table.headers]);
      if (table.rows.length > 0) {
        sheet
          .getRange(2, 1, table.rows.length, table.headers.length)
          .setValues(table.rows);
      }
    });

    return jsonResponse({
      ok: true,
      message: "Successfully synchronized all seven tables to Google Sheets.",
      sheets_updated: SHEET_NAMES,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error(error);
    return jsonResponse({ ok: false, message: "Sync error: " + error.toString() });
  }
}

function jsonResponse(value) {
  return ContentService.createTextOutput(JSON.stringify(value))
    .setMimeType(ContentService.MimeType.JSON);
}
