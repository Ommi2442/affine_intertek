import { Breadcrumbs, Link } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { useBreadcrumbs } from './BreadCrumbContext';

const AppBreadcrumbs = () => {
  const history = useBreadcrumbs();
  const navigate = useNavigate();

  return (
    <Breadcrumbs
      sx={{ fontSize: '17px', mb: 1, fontWeight: 700, color: 'black' }}
      aria-label="breadcrumb"
    >
      {history.map((item) => (
        <Link
          key={item.path}
          underline="hover"
          color="inherit"
          onClick={() => navigate(item.path)}
          sx={{ cursor: 'pointer' }}
        >
          {item.label}
        </Link>
      ))}
    </Breadcrumbs>
  );
};

export default AppBreadcrumbs;
