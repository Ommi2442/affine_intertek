import api from '../../services/api';


export const fetchPdfFromBackend = async (blobUrl) => {
  const res = await api.get(`/projects/pdf-proxy`, {
    params: { url: blobUrl },
    responseType: "arraybuffer",
    showLoader: false,
  });

  return res.data;
};


export const fetchProjectPdfsApi = async (projectId) => {
  const res = await api.get("/projects/project-pdfs-load", {
    params: { project_id: projectId },
    showLoader: false,
  });

  return res.data;

};