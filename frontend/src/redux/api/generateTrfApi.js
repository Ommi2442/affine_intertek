import api from '../../services/api';
import axios from 'axios';

const BASE_URL = import.meta.env.VITE_BACKEND_URL;

// -------------------------------------------------------
// 1. FETCH TRF REPORTS (GET)
// -------------------------------------------------------
export const generateTrfApi = async (project_id) => {
  const token = localStorage.getItem('token');
  const file_type = '.json'
  const response = await api.get(
    '/projects/fetch-trf-reports',
    {
      params: { project_id , file_type},
      headers: {
        Authorization: `Bearer ${token}`,
      },
      showLoader: true,    // <- HIDE LOADER
    }
  );

  return response.data;
};

// -------------------------------------------------------
// 2. TRIGGER TRF GENERATION (POST)
// -------------------------------------------------------
export const triggerGenerateTrfApi = async (projectId) => {
  const token = localStorage.getItem("token");

  const response = await axios.post(
    `${BASE_URL}/projects/generate-trf`,
    null,
    {
      params: { projectId },
      headers: {
        Authorization: `Bearer ${token}`,
      },
      showLoader: false,    // <- HIDE LOADER
    }
  );

  return response.data;
};


export const fetchTrfJsonPartApi = async (projectId, partIndex) => {
  const token = localStorage.getItem('token');

  const res = await api.get('/projects/trf-json-part', {
    params: {
      project_id: projectId,
      part_index: partIndex,
    },
    headers: {
      Authorization: `Bearer ${token}`,
    },
    // 🔴 show loader ONLY for first part
    showLoader: partIndex === 1,
  });

  return res.data;
};
