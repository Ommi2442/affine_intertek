import { call, put, takeLatest } from 'redux-saga/effects';
import { triggerGenerateCdrApi } from '../../api/generateCdrApi';
import {
  generateCdrFailed,
  generateCdrRequest,
  generateCdrSuccess,
} from './generateCdrSlice';

function* handleGenerateCdr(action) {
  try {
    const response = yield call(triggerGenerateCdrApi, action.payload);
    yield put(generateCdrSuccess(response));
  } catch (err) {
    yield put(
      generateCdrFailed(err.response?.data?.detail || 'CDR generation failed')
    );
  }
}

export default function* generateCdrSaga() {
  yield takeLatest(generateCdrRequest.type, handleGenerateCdr);
}
