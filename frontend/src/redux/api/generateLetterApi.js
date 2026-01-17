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
      other_urls:
        'https://stintertekesusdev.blob.core.windows.net/stintertekesusdev-blob/Documents/G105000001/user_uploaded_CDR_file/iec_output_sheet_G10501.xlsx',
    },
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
      showLoader: false, // <- HIDE LOADER
    }
  );

  return response.data;
};
