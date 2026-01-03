import * as XLSX from 'xlsx';
import { saveAs } from 'file-saver';

export function DownloadMissingFieldsExcel(jsonData, projectID, reportType) {
  const rows = [];

  jsonData.Tables.forEach((table) => {
    table.Items.forEach((item) => {
      if (
        (item.ai_fillable == false && item.value == null) ||
        (item.ai_fillable == true &&
          (item.value == null ||
            item.value == 'TBD-Info available' ||
            item.value == 'TBD-Info not available'))
      ) {
        rows.push({
          Field: item.field ?? '',
          Page: item.page_no ?? '',
          Value: item.value ?? '',
        });
      }
    });
  });

  if (rows.length === 0) {
    alert('No missing fields found.');
    return;
  }

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
