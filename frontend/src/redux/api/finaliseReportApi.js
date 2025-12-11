import axios from 'axios';

const BASE_URL = import.meta.env.VITE_BACKEND_URL;

export const finaliseReportApi = async (payload, token) => {
  // const token = localStorage.getItem('token');
  const response = await axios.post(
    `${BASE_URL}/projects/finaliseReport`,
    payload,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  return response.data;
};
