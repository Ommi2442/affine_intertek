import { all } from 'redux-saga/effects';
import authSaga from '../redux/features/auth/authSaga';
import dashboardSaga from './features/dashboard/dashboardSaga';
import projectSaga from './features/createProject/createProjectSaga';
import generateTrfSaga from './features/generateTrf/generateTrfSaga';
import finaliseReportSaga from './features/finaliseReport/finaliseReportSaga';
import deleteProjectSaga from './features/deleteProject/deleteProjectSaga';
import archieveProjectSaga from './features/archieveProject/archieveProjectSaga';
import downloadReportSaga from './features/downloadReport/downloadReportSaga';

export default function* rootSaga() {
  yield all([
    authSaga(),
    dashboardSaga(),
    projectSaga(),
    generateTrfSaga(),
    finaliseReportSaga(),
    deleteProjectSaga(),
    archieveProjectSaga(),
    downloadReportSaga(),
  ]);
}
