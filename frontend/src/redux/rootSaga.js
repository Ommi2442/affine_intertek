import { all } from 'redux-saga/effects';
import authSaga from '../redux/features/auth/authSaga';
import dashboardSaga from './features/dashboard/dashboardSaga';
import projectSaga from './features/createProject/createProjectSaga';

export default function* rootSaga() {
  yield all([authSaga(), dashboardSaga(), projectSaga()]);
}
