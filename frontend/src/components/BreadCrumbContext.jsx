import { createContext, useContext, useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';

const BreadcrumbContext = createContext([]);

export const BreadcrumbProvider = ({ children }) => {
  const location = useLocation();
  const [history, setHistory] = useState([]);

  useEffect(() => {
    setHistory((prev) => {
      const exists = prev.find((item) => item.path === location.pathname);
      if (exists) return prev;

      return [
        ...prev,
        {
          path: location.pathname,
          label: formatLabel(location.pathname),
        },
      ];
    });
  }, [location.pathname]);

  return (
    <BreadcrumbContext.Provider value={history}>
      {children}
    </BreadcrumbContext.Provider>
  );
};

export const useBreadcrumbs = () => useContext(BreadcrumbContext);

// Converts /report-page → Report Page
const formatLabel = (path) =>
  path
    .replace('/', '')
    .replace('-', ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
