import axios from 'axios';

const BASE_URL = import.meta.env.VITE_BACKEND_URL;

// -------------------------------------------------------
// TRIGGER CDR GENERATION (POST)
// -------------------------------------------------------
export const triggerGenerateLetterApi = async (
  projectId,
  trfBlobUrl,
  cdrBlobUrl
) => {
  const token = localStorage.getItem('token');

  const response = await axios.post(
    `${BASE_URL}/projects/letter-generation`,
    {
      projectId: projectId,
      trf_urls: trfBlobUrl,
      cdr_urls: cdrBlobUrl,
    },
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
      timeout: 25000,          // ✅ frontend safety
      withCredentials: false, // ✅ avoids CORS confusion
      showLoader: false, // <- HIDE LOADER
    }
  );

  return response.data;
};
