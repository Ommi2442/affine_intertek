import { all } from 'redux-saga/effects';
import authSaga from '../redux/features/auth/authSaga';
import dashboardSaga from './features/dashboard/dashboardSaga';
import projectSaga from './features/createProject/createProjectSaga';
import generateTrfSaga from './features/generateTrf/generateTrfSaga';
import finaliseReportSaga from './features/finaliseReport/finaliseReportSaga';

export default function* rootSaga() {
  yield all([
    authSaga(),
    dashboardSaga(),
    projectSaga(),
    generateTrfSaga(),
    finaliseReportSaga(),
  ]);
}
