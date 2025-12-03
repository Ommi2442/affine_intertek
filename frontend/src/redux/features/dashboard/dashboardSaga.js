import { call, put, select, takeLatest } from 'redux-saga/effects';
import { fetchProjectsApi } from '../../api/dashboardApi';
import {
  fetchProjectsRequest,
  fetchProjectsSuccess,
  fetchProjectsFailed,
} from './dashboardSlice';

// selector to get auth token
const getToken = (state) => state.auth.token;

function* handleFetchProjects() {
  try {
    const token = yield select((state) => state.auth.token);
    const user_role = yield select((state) => state.auth.user_role);
    const user_email = yield select((state) => state.auth.user_email);

    const response = yield call(fetchProjectsApi, token, {
      user_role,
      user_email,
    });

    yield put(fetchProjectsSuccess(response));
  } catch (err) {
    yield put(fetchProjectsFailed(err.message));
  }
}


export default function* dashboardSaga() {
  yield takeLatest(fetchProjectsRequest.type, handleFetchProjects);
}
