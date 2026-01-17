import api from '../../services/api';

export const uploadCdrOutApi = async (projectId, key, files) => {
  const token = localStorage.getItem('token');

  const formData = new FormData();
  formData.append('projectId', projectId);
  formData.append('key', key);

  // Only include real File objects
  const realFiles = files.filter((f) => f instanceof File);

  if (realFiles.length === 0) {
    console.warn(`Skipping upload for '${key}' because no real files found`);
    return { status: 'skipped', uploaded: [] };
  }

  realFiles.forEach((file) => {
    formData.append('files', file, file.name);
  });

  const response = await api.post('/projects/upload_cdr', formData, {
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
};
