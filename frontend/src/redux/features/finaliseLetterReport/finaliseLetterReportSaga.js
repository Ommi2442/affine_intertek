import { call, put, select, takeLatest } from 'redux-saga/effects';
import {
  finaliseLetterReportFailed,
  finaliseLetterReportRequest,
  finaliseLetterReportSuccess,
} from './finaliseLetterReportSlice';
import { finaliseLetterReportApi } from '../../api/finaliseLetterReportApi';

// selector to get auth token
const getToken = (state) => state.auth.token;

function* handleFinaliseProjects(action) {
  try {
    const token = yield select(getToken);
    const response = yield call(finaliseLetterReportApi, action.payload, token);
    yield put(finaliseLetterReportSuccess(response));
  } catch (err) {
    yield put(finaliseLetterReportFailed(err.message));
  }
}

export default function* projectSaga() {
  yield takeLatest(finaliseLetterReportRequest.type, handleFinaliseProjects);
}
