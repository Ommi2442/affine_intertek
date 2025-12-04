import axios from "axios";

const BASE_URL = import.meta.env.VITE_BACKEND_URL;

export const checkProjectIdApi = async (projectId) => {
  const token = localStorage.getItem("token");

  const response = await axios.get(
    `${BASE_URL}/projects/check/${projectId}`, 
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  return response.data;
};
