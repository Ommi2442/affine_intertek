import { useLocation } from 'react-router-dom';
import { useEffect } from 'react';
import { idb_clear_all } from '../utils/idb';

export default function RouteDbGuard() {
  const location = useLocation();

  useEffect(() => {
    // ✅ Allow IndexedDB ONLY on /report-page
    if (location.pathname !== '/report-page') {
      idb_clear_all();
    }
  }, [location.pathname]);

  return null; // no UI
}
