import { call, put, takeLatest } from 'redux-saga/effects';
import { loginApi } from '../../api/authApi';
import { loginRequest, loginSuccess, loginFailed } from './authSlice';

function* handleLogin(action) {
  try {
    const response = yield call(loginApi, action.payload);
    yield put(loginSuccess(response));
  } catch (err) {
    yield put(loginFailed(err.message));
  }
}

export default function* authSaga() {
  yield takeLatest(loginRequest.type, handleLogin);
}
