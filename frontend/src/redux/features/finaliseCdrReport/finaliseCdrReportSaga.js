import { call, put, select, takeLatest } from 'redux-saga/effects';
import { finaliseCdrReportApi } from '../../api/finaliseCdrReportApi';
import {
  finaliseCdrReportFailed,
  finaliseCdrReportRequest,
  finaliseCdrReportSuccess,
} from './finaliseCdrReportSlice';

// selector to get auth token
const getToken = (state) => state.auth.token;

function* handleFinaliseProjects(action) {
  try {
    const token = yield select(getToken);
    const response = yield call(finaliseCdrReportApi, action.payload, token);
    yield put(finaliseCdrReportSuccess(response));
  } catch (err) {
    yield put(finaliseCdrReportFailed(err.message));
  }
}

export default function* projectSaga() {
  yield takeLatest(finaliseCdrReportRequest.type, handleFinaliseProjects);
}
