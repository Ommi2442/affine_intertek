import axios from 'axios';

const BASE_URL = import.meta.env.VITE_BACKEND_URL;

// -------------------------------------------------------
// TRIGGER CDR GENERATION (POST)
// -------------------------------------------------------
export const triggerGenerateCdrApi = async (projectId) => {
  const token = localStorage.getItem('token');

  const response = await axios.post(`${BASE_URL}/projects/generate-cdr`, null, {
    params: { projectId },
    headers: {
      Authorization: `Bearer ${token}`,
    },
    showLoader: false,
    timeout: 25000,
    withCredentials: false,
    showLoader: false,
  });

  return response.data;
};

export const CdrApiDataLoad = async (projectId) => {
  const token = localStorage.getItem('token');

  const response = await axios.post(
    `${BASE_URL}/projects/cdr-result`,
    {
      projectId: projectId,
    },
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
      timeout: 25000,
      withCredentials: false,
      showLoader: false,
    }
  );

  return response.data;
};

export const CdrStatusCheck = async (projectId) => {
  const token = localStorage.getItem('token');

  const response = await axios.post(
    `${BASE_URL}/projects/report/status/cdr`,
    {
      projectId: projectId,
    },
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
      timeout: 25000,
      withCredentials: false,
      showLoader: false,
    }
  );

  return response.data;
};
