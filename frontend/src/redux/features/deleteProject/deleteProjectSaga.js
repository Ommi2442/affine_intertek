import { call, put, select, takeLatest } from 'redux-saga/effects';
import {
  deleteProjectsFailed,
  deleteProjectsRequest,
  deleteProjectsSuccess,
} from './deleteProjectSlice';
import { deleteProjectApi } from '../../api/deleteProjectApi';
import { fetchProjectsRequest } from '../dashboard/dashboardSlice';

const getToken = (state) => state.auth.token;

function* handleDeleteProjects(action) {
  try {
    const token = yield select(getToken);
    const projectId = action.payload;

    const response = yield call(deleteProjectApi, projectId, token);

    yield put(deleteProjectsSuccess(response));

    // refresh dashboard AFTER delete
    yield put(fetchProjectsRequest());
  } catch (err) {
    yield put(deleteProjectsFailed(err.message));
  }
}

export default function* projectSaga() {
  yield takeLatest(deleteProjectsRequest.type, handleDeleteProjects);
}
