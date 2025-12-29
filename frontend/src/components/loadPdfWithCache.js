import { getPdfFromDb, savePdfToDb } from "./pdfIndexedDb";
import { fetchPdfFromBackend } from "../redux/api/fetchPdfApi";

export const loadPdfWithCache = async (
  projectId,
  filename,
  blobUrl,
  pdfViewerRef
) => {
  // 1. IndexedDB
  const cached = await getPdfFromDb(projectId, filename);

  let arrayBuffer;

  if (cached?.data) {
    arrayBuffer = cached.data;
  } else {
    // 2. Backend fetch ONCE
    // arrayBuffer = await fetchPdfFromBackend(blobUrl);
    await savePdfToDb(projectId, filename, arrayBuffer);
  }

  // 3. Always load from IndexedDB bytes
  const blob = new Blob([arrayBuffer], {
    type: "application/pdf",
  });

  const objectUrl = URL.createObjectURL(blob);
  pdfViewerRef.current.loadPdfFromUrl(objectUrl);
};
