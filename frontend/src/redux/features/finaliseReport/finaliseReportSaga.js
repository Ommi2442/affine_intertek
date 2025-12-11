import { call, put, select, takeLatest } from 'redux-saga/effects';
import { finaliseReportApi } from '../../api/finaliseReportApi';
import {
  finaliseReportFailed,
  finaliseReportRequest,
  finaliseReportSuccess,
} from './finaliseReportSlice';

// selector to get auth token
const getToken = (state) => state.auth.token;

function* handleFinaliseProjects(action) {
  try {
    const token = yield select(getToken);
    const response = yield call(finaliseReportApi, action.payload, token);
    yield put(finaliseReportSuccess(response));
  } catch (err) {
    yield put(finaliseReportFailed(err.message));
  }
}

export default function* projectSaga() {
  yield takeLatest(finaliseReportRequest.type, handleFinaliseProjects);
}
