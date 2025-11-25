import axios from 'axios';

export const loginApi = async (payload) => {
  const response = await axios.post('https://backendapi/login', payload);
  return response.data;
};
