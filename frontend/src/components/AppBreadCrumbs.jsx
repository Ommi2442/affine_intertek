import { Breadcrumbs, Link } from '@mui/material';
import { useNavigate, useLocation } from 'react-router-dom';

const routeLabelMap = {
  '/dashboard': 'Dashboard',
  '/create-project': 'Create Project',
  '/report-page': 'Report Page',
};

const AppBreadcrumbs = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const currentPath = location.pathname;

  const breadcrumbs = [];

  // ✅ Always show Dashboard as first breadcrumb
  breadcrumbs.push({
    path: '/dashboard',
    label: 'Dashboard',
  });

  // ✅ Show second breadcrumb only if NOT on dashboard
  if (currentPath !== '/dashboard') {
    breadcrumbs.push({
      path: currentPath,
      label: routeLabelMap[currentPath] || currentPath.replace('/', ''),
    });
  }

  return (
    <Breadcrumbs
      sx={{ fontSize: '17px', mb: 1, fontWeight: 700, color: 'black' }}
      aria-label="breadcrumb"
    >
      {breadcrumbs.map((item) => (
        <Link
          key={item.path}
          underline="hover"
          color="inherit"
          sx={{ cursor: 'pointer' }}
          onClick={() => navigate(item.path)}
        >
          {item.label}
        </Link>
      ))}
    </Breadcrumbs>
  );
};

export default AppBreadcrumbs;
