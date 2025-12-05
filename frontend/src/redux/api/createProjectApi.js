import api from '../../services/api';

export const createProjectApi = async (payload) => {
  const token = localStorage.getItem('token');

  const response = await api.post('/projects/create', payload, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  return response.data;
};

export const deleteUploadedFileApi = async (projectId, fileName) => {
  const response = await api.delete(`/projects/${projectId}/files/${fileName}`);
  return response.data;
};
