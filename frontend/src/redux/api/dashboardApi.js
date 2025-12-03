import axios from 'axios';

const BASE_URL = import.meta.env.VITE_BACKEND_URL;

export const fetchProjectsApi = async (token) => {
  const user_role = parseInt(localStorage.getItem("role"));
  const user_email = localStorage.getItem("email");

  const response = await axios.post(
    `${BASE_URL}/projects/all`,
    { user_role, user_email },
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  return response.data;
};
