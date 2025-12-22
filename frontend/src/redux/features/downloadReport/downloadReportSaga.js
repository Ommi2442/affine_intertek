// src/redux/saga/downloadReportSaga.js
import { call, put, select, takeLatest } from 'redux-saga/effects';
import { downloadReportApi } from '../../api/downloadReportApi';
import {
  downloadReportRequest,
  downloadReportSuccess,
  downloadReportFailed,
} from './downloadReportSlice';

const getToken = (state) => state.auth.token;

function* handleDownloadReport() {
  try {
    const token = yield select(getToken);

    const response = yield call(downloadReportApi, token);

    // ✅ Extract filename from headers
    const contentDisposition = response.headers['content-disposition'];
    let filename = 'report.pdf';

    if (contentDisposition) {
      const match = contentDisposition.match(/filename="?(.+)"?/);
      if (match?.[1]) filename = match[1];
    }

    // ✅ Trigger browser download
    const blob = new Blob([response.data]);
    const url = window.URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();

    window.URL.revokeObjectURL(url);

    yield put(downloadReportSuccess());
  } catch (err) {
    yield put(downloadReportFailed(err.message));
  }
}

export default function* downloadReportSaga() {
  yield takeLatest(downloadReportRequest.type, handleDownloadReport);
}
