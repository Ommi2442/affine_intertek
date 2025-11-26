import { call, put, select, takeLatest } from 'redux-saga/effects';
import {
  createProjectsRequest,
  createProjectsSuccess,
  createProjectsFailed,
} from './createProjectSlice';
import { createProjectApi } from '../../api/createProjectApi';

// selector to get auth token
const getToken = (state) => state.auth.token;

function* handleCreateProjects() {
  try {
    const token = yield select(getToken);
    const response = yield call(createProjectApi, token);
    yield put(createProjectsSuccess(response));
  } catch (err) {
    yield put(createProjectsFailed(err.message));
  }
}

export default function* projectSaga() {
  yield takeLatest(createProjectsRequest.type, handleCreateProjects);
}
