import { configureStore } from '@reduxjs/toolkit';
import createSagaMiddleware from 'redux-saga';
import authReducer from '../redux/features/auth/authSlice';
import dashboardReducer from '../redux/features/dashboard/dashboardSlice';
import createProjectReducer from '../redux/features/createProject/createProjectSlice';
import generateTrfReducer from '../redux/features/generateTrf/generateTrfSlice';
import finaliseReportReducer from '../redux/features/finaliseReport/finaliseReportSlice';
import deleteProjectReducer from '../redux/features/deleteProject/deleteProjectSlice';
import archieveProjectReducer from '../redux/features/archieveProject/archieveProjectSlice';
import confidenceReducer from '../redux/features/confidence/confidenceSlice';
import rootSaga from './rootSaga';
//import downloadReportReducer from '../redux/features/downloadReport/downloadReportSlice';

const sagaMiddleware = createSagaMiddleware();

export const store = configureStore({
  reducer: {
    auth: authReducer,
    dashboard: dashboardReducer,
    project: createProjectReducer,
    trf: generateTrfReducer,
    finaliseReport: finaliseReportReducer,
    deleteProj: deleteProjectReducer,
    archieveProj: archieveProjectReducer,
    confidence: confidenceReducer,
    //downloadReport: downloadReportReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({ thunk: false }).concat(sagaMiddleware),
});

sagaMiddleware.run(rootSaga);
