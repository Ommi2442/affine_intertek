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
    showLoader: false, // <- HIDE LOADER
    timeout: 25000,          // ✅ frontend safety
    withCredentials: false, // ✅ avoids CORS confusion
    showLoader: false, // <- HIDE LOADER
  });

  return response.data;
};
