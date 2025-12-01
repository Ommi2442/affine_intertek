import { call, put, takeLatest } from 'redux-saga/effects';
import {
  generateTrfRequest,
  generateTrfSuccess,
  generateTrfFailed,
} from './generateTrfSlice';
import { generateTrfApi } from '../../api/generateTrfApi';

function* handleGenerateTrf(action) {
  try {
    const response = yield call(generateTrfApi, action.payload);
    yield put(generateTrfSuccess(response));
  } catch (err) {
    yield put(
      generateTrfFailed(err.response?.data?.detail || 'TRF generation failed')
    );
  }
}

export default function* generateTrfSaga() {
  yield takeLatest(generateTrfRequest.type, handleGenerateTrf);
}
