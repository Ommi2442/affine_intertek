import api from "../services/api";   // your axios instance
import { loaderStore } from "./loaderStore";

let requestCount = 0;

const showLoader = () => {
  requestCount++;
  loaderStore.setLoading(true);
};

const hideLoader = () => {
  requestCount--;
  if (requestCount <= 0) {
    loaderStore.setLoading(false);
  }
};

// Request Interceptor
api.interceptors.request.use(
  (config) => {
    showLoader();
    return config;
  },
  (error) => {
    hideLoader();
    return Promise.reject(error);
  }
);

// Response Interceptor
api.interceptors.response.use(
  (response) => {
    hideLoader();
    return response;
  },
  (error) => {
    hideLoader();
    return Promise.reject(error);
  }
);

export default api;
