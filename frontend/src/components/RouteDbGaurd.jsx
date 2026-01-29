import { useLocation } from 'react-router-dom';
import { useEffect } from 'react';
import { idb_clear_all } from '../utils/idb';

export default function RouteDbGuard() {
  const location = useLocation();

  useEffect(() => {
    // Allow IndexedDB ONLY on /report-page
    console.log('location', location.pathname);
    if (
      location.pathname !== '/report-page/trf' &&
      location.pathname !== '/report-page/cdr' &&
      location.pathname !== '/report-page/letter'
    ) {
      idb_clear_all();
    }
  }, [location.pathname]);

  return null; // no UI
}
