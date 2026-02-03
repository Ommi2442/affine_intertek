// src/utils/idb.js
// TRF_DB with two stores: TRF_STORE and CDR_STORE

const DB_NAME = 'TRF_DB';
const DB_VERSION = 4; // IMPORTANT: bumped to 2 so new store gets created

const DEFAULT_STORE = 'TRF_STORE';
const CDR_STORE = 'CDR_STORE';
const LETTER_STORE = 'LETTER_STORE';

// Create stores when DB upgrades
function ensureStores(db) {
  if (!db.objectStoreNames.contains(DEFAULT_STORE)) {
    db.createObjectStore(DEFAULT_STORE);
  }
  if (!db.objectStoreNames.contains(CDR_STORE)) {
    db.createObjectStore(CDR_STORE);
  }
  if (!db.objectStoreNames.contains(LETTER_STORE)) {
    db.createObjectStore(LETTER_STORE);
  }
}

// Open DB with schema upgrade support
export function idb_open() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);

    req.onupgradeneeded = () => {
      const db = req.result;
      ensureStores(db);
    };

    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

// INTERNAL UTIL → Open a store safely (auto-upgrade if missing)
async function getStore(storeName = DEFAULT_STORE, mode = 'readonly') {
  let db = await idb_open();

  // If store is missing (rare), we must upgrade DB dynamically
  if (!db.objectStoreNames.contains(storeName)) {
    db.close();

    // bump version automatically
    const newVersion = db.version + 1;
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, newVersion);

      req.onupgradeneeded = () => {
        const upgradeDB = req.result;
        if (!upgradeDB.objectStoreNames.contains(storeName)) {
          upgradeDB.createObjectStore(storeName);
        }
      };

      req.onsuccess = () => {
        const upgradedDB = req.result;
        const tx = upgradedDB.transaction(storeName, mode);
        resolve({
          db: upgradedDB,
          tx,
          store: tx.objectStore(storeName),
        });
      };

      req.onerror = () => reject(req.error);
    });
  }

  const tx = db.transaction(storeName, mode);
  return { db, tx, store: tx.objectStore(storeName) };
}

// Write any value (deep clone ensures no React proxy leaks)
export async function idb_set(key, value, storeName = DEFAULT_STORE) {
  const { db, tx, store } = await getStore(storeName, 'readwrite');

  return new Promise((resolve, reject) => {
    try {
      const safeValue = JSON.parse(JSON.stringify(value));
      const req = store.put(safeValue, key);

      req.onsuccess = () => {
        tx.oncomplete = () => {
          try {
            db.close();
          } catch {}
          resolve(true);
        };
      };

      req.onerror = () => {
        try {
          db.close();
        } catch {}
        reject(req.error);
      };
    } catch (err) {
      try {
        db.close();
      } catch {}
      reject(err);
    }
  });
}

// Read value from store
export async function idb_get(key, storeName = DEFAULT_STORE) {
  const { db, tx, store } = await getStore(storeName, 'readonly');

  return new Promise((resolve, reject) => {
    try {
      const req = store.get(key);

      req.onsuccess = () => {
        try {
          db.close();
        } catch {}
        resolve(req.result ?? null);
      };

      req.onerror = () => {
        try {
          db.close();
        } catch {}
        reject(req.error);
      };
    } catch (err) {
      try {
        db.close();
      } catch {}
      reject(err);
    }
  });
}

// Delete a key
export async function idb_delete(key, storeName = DEFAULT_STORE) {
  const { db, tx, store } = await getStore(storeName, 'readwrite');

  return new Promise((resolve, reject) => {
    try {
      const req = store.delete(key);

      req.onsuccess = () => {
        tx.oncomplete = () => {
          try {
            db.close();
          } catch {}
          resolve(true);
        };
      };

      req.onerror = () => {
        try {
          db.close();
        } catch {}
        reject(req.error);
      };
    } catch (err) {
      try {
        db.close();
      } catch {}
      reject(err);
    }
  });
}

// export async function idb_clear_all() {
//   console.log('aaaaaa');
//   const db = await new Promise((resolve, reject) => {
//     const req = indexedDB.open(DB_NAME, DB_VERSION);

//     req.onsuccess = () => resolve(req.result);
//     req.onerror = () => reject(req.error);
//   });

//   return new Promise((resolve, reject) => {
//     try {
//       const storeNames = Array.from(db.objectStoreNames);

//       if (storeNames.length === 0) {
//         db.close();
//         resolve(true);
//         return;
//       }

//       const tx = db.transaction(storeNames, 'readwrite');

//       storeNames.forEach((store) => {
//         tx.objectStore(store).clear();
//       });

//       tx.oncomplete = () => {
//         try {
//           db.close();
//         } catch {}
//         resolve(true);
//       };

//       tx.onerror = () => {
//         try {
//           db.close();
//         } catch {}
//         reject(tx.error);
//       };
//     } catch (err) {
//       try {
//         db.close();
//       } catch {}
//       reject(err);
//     }
//   });
// }

// Export store constants for use in React components

// export const idb_clear_all = async () => {
//   if (!window.indexedDB) return;

//   const databases = await indexedDB.databases();

//   for (const db of databases) {
//     if (db.name) {
//       indexedDB.deleteDatabase(db.name);
//     }
//   }

//   console.log('IndexedDB cleared');
// };

export const idb_clear_all = () =>
  new Promise((resolve, reject) => {
    const req = indexedDB.deleteDatabase('TRF_DB');
    const req2 = indexedDB.deleteDatabase('pdf-cache-db');
    req.onsuccess = () => resolve(true);
    req.onerror = () => reject(req.error);
    req2.onsuccess = () => resolve(true);
    req2.onerror = () => reject(req2.error);
  });

export const STORES = {
  TRF: DEFAULT_STORE,
  CDR: CDR_STORE,
  LETTER: LETTER_STORE,
};
