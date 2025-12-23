// src/redux/api/downloadReportApi.js
import axios from 'axios';

const BASE_URL = import.meta.env.VITE_BACKEND_URL;

export const downloadReportApi = async (token) => {
  const response = await axios.get(`${BASE_URL}/projects/download-file`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    responseType: 'blob', // ✅ REQUIRED FOR FILE
  });

  return response;
};
