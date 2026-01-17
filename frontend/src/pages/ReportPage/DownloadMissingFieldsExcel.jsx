import * as XLSX from 'xlsx';
import { saveAs } from 'file-saver';

export function DownloadMissingFieldsExcel(jsonData, projectID, reportType) {
  const rows = [];

  if (!jsonData) {
    alert('Invalid report data');
    return;
  }

  /* =========================
        TRF
  ========================= */
  if (reportType === 'trf') {
    const tables = jsonData?.Tables || [];

    tables.forEach((table) => {
      const items = table?.Items || [];

      items.forEach((item) => {
        const value = item?.value;

        const isMissing =
          (item?.ai_fillable === false && (value === null || value === '')) ||
          (item?.ai_fillable === true &&
            (value === null ||
              value === '' ||
              value === 'TBD-Info available' ||
              value === 'TBD-Info not available'));

        if (isMissing) {
          rows.push({
            Field: item?.field ?? '',
            Clause: item?.clause ?? '',
            Page: item?.page_no ?? '',
            Value: value ?? '',
          });
        }
      });
    });
  }

  /* =========================
        CDR
  ========================= */
  if (reportType === 'cdr') {
    const sheets = jsonData?.Sheets || [];

    sheets.forEach((sheet) => {
      /* Normal sheet fields */
      const items = sheet?.Items || [];

      items.forEach((item) => {
        if (item?.ai_fillable !== true) return;

        const value = item?.value;

        const isMissing =
          (item?.ai_fillable === false && (value === null || value === '')) ||
          (item?.ai_fillable === true && (value === null || value === ''));

        if (isMissing) {
          rows.push({
            Field: item?.field || item?.prefix || '',
            Sheet: sheet?.sheet_name || '',
            Cell: item?.answer_cell || item?.question_cell || '',
            Value: value ?? '',
          });
        }
      });

      /* Critical components table */
      const rowsTable = sheet?.Rows || [];

      rowsTable.forEach((row) => {
        if (row?.row_type !== 'table_data') return;

        const missing = [];
        if (!row?.manufacturer) missing.push('Manufacturer');
        if (!row?.type_model) missing.push('Type/Model');
        if (!row?.technical_data) missing.push('Technical Data');
        if (!row?.marks_of_conf) missing.push('Mark of Conformity');

        if (missing.length > 0) {
          rows.push({
            Field: `Component ${row?.item_no} - ${row?.name}`,
            Sheet: sheet?.sheet_name || '',
            Cell: row?.start_cell || '',
            Value: `Missing: ${missing.join(', ')}`,
          });
        }
      });
    });
  }

  /* =========================
      LETTER
  ========================= */
  if (reportType === 'letter') {
    const pages = jsonData?.pages || [];

    pages.forEach((page, pageIndex) => {
      const items = page?.items || [];

      items.forEach((item) => {
        /* ---------- NORMAL LETTER FIELDS ---------- */
        if (item?.dataframe_table !== true) {
          const value = item?.value;

          const isMissing =
            (item?.ai_fillable === true || item?.user_editable === true) &&
            (value === null || value === '');

          if (isMissing) {
            rows.push({
              Field: item?.key || item?.field || '',
              Page: pageIndex + 1,
              Value: value ?? '',
            });
          }
        }

        /* ---------- DATAFRAME TABLE (NON-CONFORMANCE ETC.) ---------- */
        if (item?.dataframe_table === true && Array.isArray(item.value)) {
          item.value.forEach((row, rowIndex) => {
            if (row?.__isNew) return; //  skip new rows

            const missingColumns = Object.entries(row)
              .filter(
                ([key, val]) =>
                  key !== '__isNew' && (val === null || val === '')
              )
              .map(([key]) => key);

            if (missingColumns.length > 0) {
              rows.push({
                Field: `${item.key || 'Table'} – Row ${rowIndex + 1}`,
                Page: pageIndex + 1,
                Value: `Missing: ${missingColumns.join(', ')}`,
              });
            }
          });
        }
      });
    });
  }

  /* =========================
        Empty check
  ========================= */
  if (rows.length === 0) {
    alert(`No missing fields found in ${reportType.toUpperCase()} report.`);
    return;
  }

  /* =========================
        Excel
  ========================= */
  const worksheet = XLSX.utils.json_to_sheet(rows);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, 'Missing Fields');

  const excelBuffer = XLSX.write(workbook, {
    bookType: 'xlsx',
    type: 'array',
  });

  const file = new Blob([excelBuffer], {
    type: 'application/octet-stream',
  });

  const now = new Date();
  const date = now.toISOString().split('T')[0];
  const time = now.toTimeString().split(' ')[0].replace(/:/g, '-');

  const safeProjectId =
    projectID || localStorage.getItem('projectId') || 'UNKNOWN_PROJECT';

  saveAs(
    file,
    `missing_fields_${reportType.toUpperCase()}_${safeProjectId}_${date}_${time}.xlsx`
  );
}
