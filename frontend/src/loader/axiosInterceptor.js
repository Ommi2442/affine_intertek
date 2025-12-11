import api from "../services/api";
import { loaderStore } from "./loaderStore";

let activeRequests = 0;

// Show Loader
const showLoader = () => {
  activeRequests++;
  loaderStore.setLoading(true);
};

// Hide Loader
const hideLoader = () => {
  activeRequests--;
  if (activeRequests <= 0) {
    loaderStore.setLoading(false);
  }
};

// REQUEST INTERCEPTOR
api.interceptors.request.use(
  (config) => {
    // DEFAULT = true
    const shouldShow = config.showLoader !== false;

    if (shouldShow) {
      config.__loaderActive = true;   // mark loader was used
      showLoader();
    }

    return config;
  },
  (error) => {
    hideLoader();
    return Promise.reject(error);
  }
);

// RESPONSE INTERCEPTOR
api.interceptors.response.use(
  (response) => {
    if (response.config.__loaderActive) {
      hideLoader();
    }
    return response;
  },
  (error) => {
    if (error.config?.__loaderActive) {
      hideLoader();
    }
    return Promise.reject(error);
  }
);

export default api;
