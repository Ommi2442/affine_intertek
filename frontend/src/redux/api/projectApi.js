import api from '../../services/api';


// LOAD project for recent uploads
export const getProjectByIdApi = async (projectId) => {
  const res = await api.get(`/projects/filesuploaded/${projectId}`);
  return res.data;
};

// DELETE a file
export const deleteUploadedFileApi = async (projectId, fileName) => {
  const res = await api.delete(`/projects/filesdelete/${projectId}/${fileName}`);
  return res.data;
};
