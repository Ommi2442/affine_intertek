import { useEffect, useState } from 'react';
import { fetchProjectPdfsApi } from '../redux/api/fetchPdfApi';
import { savePdfToDb } from '../components/pdfIndexedDb';

export const usePreloadProjectPdfs = (projectID) => {
  const [pdfLoaded, setPdfLoaded] = useState(false);

  useEffect(() => {
    if (!projectID) return;

    let cancelled = false;

    const base64ToArrayBuffer = (base64) => {
      const binary = window.atob(base64);
      const len = binary.length;
      const bytes = new Uint8Array(len);

      for (let i = 0; i < len; i++) {
        bytes[i] = binary.charCodeAt(i);
      }

      return bytes.buffer;
    };

    const preloadProjectPdfs = async () => {
      try {
        setPdfLoaded(false);

        const res = await fetchProjectPdfsApi(projectID);
        const pdfs = res?.pdfs || [];

        await Promise.all(
          pdfs.map(async (pdf) => {
            const cleanBase64 = pdf.data.includes(',')
              ? pdf.data.split(',')[1]
              : pdf.data;

            const buffer = base64ToArrayBuffer(cleanBase64);
            await savePdfToDb(projectID, pdf.filename, buffer);
          })
        );

        if (!cancelled) {
          setPdfLoaded(true);
        }
      } catch (err) {
        console.error('Preload failed:', err);
      }
    };

    preloadProjectPdfs();

    return () => {
      cancelled = true;
    };
  }, [projectID]);

  return pdfLoaded;
};
