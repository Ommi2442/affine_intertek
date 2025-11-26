import axios from 'axios';

const BASE_URL = import.meta.env.VITE_BACKEND_URL;

export const fetchProjectsApi = async (token) => {
  const response = await axios.get(`${BASE_URL}/project/all`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  return response.data;
};
