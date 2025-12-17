import { call, put, select, takeLatest } from 'redux-saga/effects';
import { archieveProjectApi } from '../../api/archieveProjectApi';
import {
  archieveProjectsFailed,
  archieveProjectsRequest,
  archieveProjectsSuccess,
} from './archieveProjectSlice';
import { fetchProjectsRequest } from '../dashboard/dashboardSlice';

// selector to get auth token
const getToken = (state) => state.auth.token;

function* handleArchieveProjects(action) {
  try {
    const token = yield select(getToken);
    const response = yield call(archieveProjectApi, action.payload);
    yield put(archieveProjectsSuccess(response));

    // refresh dashboard AFTER archieve
    yield put(fetchProjectsRequest());
  } catch (err) {
    yield put(archieveProjectsFailed(err.message));
  }
}

export default function* projectSaga() {
  yield takeLatest(archieveProjectsRequest.type, handleArchieveProjects);
}
