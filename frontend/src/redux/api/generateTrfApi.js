import axios from 'axios';

const BASE_URL = import.meta.env.VITE_BACKEND_URL;

export const generateTrfApi = async ({ project_id, file }) => {
  const token = localStorage.getItem('token');

  const formData = new FormData();
  formData.append('file', file);
  formData.append('project_id', project_id);

  const response = await axios.post(
    `${BASE_URL}/projects/Trf-reports`,
    formData,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  return response.data;
};
