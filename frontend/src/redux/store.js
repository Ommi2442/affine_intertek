import { configureStore } from '@reduxjs/toolkit';
import createSagaMiddleware from 'redux-saga';
import authReducer from '../redux/features/auth/authSlice';
import dashboardReducer from '../redux/features/dashboard/dashboardSlice';
import createProjectReducer from '../redux/features/createProject/createProjectSlice';
import generateTrfReducer from '../redux/features/generateTrf/generateTrfSlice';
import rootSaga from './rootSaga';

const sagaMiddleware = createSagaMiddleware();

export const store = configureStore({
  reducer: {
    auth: authReducer,
    dashboard: dashboardReducer,
    project: createProjectReducer,
    trf: generateTrfReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({ thunk: false }).concat(sagaMiddleware),
});

sagaMiddleware.run(rootSaga);
