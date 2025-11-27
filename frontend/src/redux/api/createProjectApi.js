import axios from 'axios';

const BASE_URL = import.meta.env.VITE_BACKEND_URL;

export const createProjectApi = async (payload) => {
  const token = localStorage.getItem('token');
  const response = await axios.post(`${BASE_URL}/projects/create`, payload, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  return response.data;
};
