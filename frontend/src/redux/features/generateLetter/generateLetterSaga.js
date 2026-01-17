import { call, put, takeLatest } from 'redux-saga/effects';
import {
  generateLetterRequest,
  generateLetterSuccess,
  generateLetterFailed,
} from './generateLetterSlice';
import { triggerGenerateLetterApi } from '../../api/generateLetterApi';

function* handleGenerateLetter(action) {
  console.log('Saga triggered:', action.payload);
  try {
    const { projectId, trfBlobUrl, cdrBlobUrl } = action.payload;
    const response = yield call(
      triggerGenerateLetterApi,
      projectId,
      trfBlobUrl,
      cdrBlobUrl
    );
    yield put(generateLetterSuccess(response));
  } catch (err) {
    yield put(
      generateLetterFailed(
        err.response?.data?.detail || 'LETTER generation failed'
      )
    );
  }
}

export default function* generateLetterSaga() {
  yield takeLatest(generateLetterRequest.type, handleGenerateLetter);
}
