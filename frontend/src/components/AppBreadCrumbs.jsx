import { Breadcrumbs, Link } from '@mui/material';
import { useNavigate, useLocation } from 'react-router-dom';

const routeLabelMap = {
  dashboard: 'Dashboard',
  'create-project': 'Create Project',
  'report-page': 'Report Page',
  trf: 'TRF',
  cdr: 'CDR',
  letter: 'Letter',
};

const AppBreadcrumbs = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const pathnames = location.pathname.split('/').filter(Boolean);

  const breadcrumbs = [];

  // ✅ Always Dashboard first
  breadcrumbs.push({
    path: '/dashboard',
    label: 'Dashboard',
  });

  // Build remaining breadcrumbs from URL
  let accumulatedPath = '';

  pathnames.forEach((segment) => {
    accumulatedPath += `/${segment}`;

    // Skip duplicate dashboard
    if (segment === 'dashboard') return;

    breadcrumbs.push({
      path: accumulatedPath,
      label: routeLabelMap[segment] || segment,
    });
  });

  return (
    <Breadcrumbs
      sx={{ fontSize: '17px', mb: 1, fontWeight: 700, color: 'black' }}
      aria-label="breadcrumb"
    >
      {breadcrumbs.map((item, index) => (
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
