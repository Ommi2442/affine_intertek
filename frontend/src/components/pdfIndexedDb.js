import { openDB } from "idb";

const DB_NAME = "pdf-cache-db";
const STORE = "pdfs";

export const pdfDbPromise = openDB(DB_NAME, 1, {
  upgrade(db) {
    if (!db.objectStoreNames.contains(STORE)) {
      db.createObjectStore(STORE, { keyPath: "key" });
    }
  },
});

export const getPdfFromDb = async (projectId, filename) => {
  const db = await pdfDbPromise;
  return db.get(STORE, `${projectId}_${filename}`);
};

export const savePdfToDb = async (projectId, filename, buffer) => {
  const db = await pdfDbPromise;
  await db.put(STORE, {
    key: `${projectId}_${filename}`,
    projectId,
    filename,
    data: buffer,
    savedAt: Date.now(),
  });
};
