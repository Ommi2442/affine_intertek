import React, { useRef, useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Divider,
  Pagination,
} from '@mui/material';
import DataTable from '../../components/DataTable';
import jsonData from '../../utils/dot.json';

const ReportPage = () => {
  const [currentPage, setCurrentPage] = useState(1);
  const dataTableRef = useRef(null);

  // Child → Parent
  const handlePageScrollChange = (page) => {
    setCurrentPage(page);
  };

  // Parent → Child
  const handlePaginationClick = (e, page) => {
    setCurrentPage(page);
    dataTableRef.current?.scrollToPage(page);
  };

  const totalPages = jsonData.Tables.length;

  return (
    <Box
      sx={{
        width: '100%',
        height: '100%',
        background: '#f5f5f5',
        display: 'flex',
        overflow: 'hidden',
      }}
    >
      {/* LEFT SIDE */}
      <Box sx={{ flex: '0 0 75%', p: 2 }}>
        <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
          <CardContent
            sx={{
              p: 0,
              height: 'calc(100% - 70px)',
              overflow: 'hidden',
            }}
          >
            <Box
              sx={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: 2,
              }}
            >
              {/* Left Image */}
              <Box
                component="img"
                src="/images/trf_image1.jpg"
                sx={{
                  width: 130,
                  height: 'auto',
                  objectFit: 'contain',
                }}
              />

              {/* Right Text */}
              <Typography
                sx={{
                  fontSize: '14px',
                  fontWeight: 600,
                  whiteSpace: 'nowrap',
                  marginRight: 10,
                  flexGrow: 1,
                  textAlign: 'right',
                }}
              >
                Test Report issued under the responsibility of:
              </Typography>
            </Box>

            <Box
              sx={{
                fontSize: '14px',
                fontWeight: 700,
                whiteSpace: 'nowrap',
                marginRight: 0,
                flexGrow: 1,
                textAlign: 'center',
              }}
            >
              <Typography sx={{ fontWeight: 700 }}>TEST REPORT</Typography>
              <Typography sx={{ fontWeight: 700 }}>IEC 61010-1</Typography>
              <Typography sx={{ fontWeight: 700 }}>
                Safety requirements for electrical equipment for measurement,
                control, and laboratory use
              </Typography>
              <Typography sx={{ fontWeight: 700 }}>
                Part 1: General requirements
              </Typography>
            </Box>

            <DataTable
              ref={dataTableRef}
              jsonData={jsonData}
              onPageScrollChange={handlePageScrollChange}
            />
          </CardContent>

          {/* <Box
            sx={{
              p: 2,
              borderTop: '1px solid #ccc',
              textAlign: 'center',
              height: '70px',
            }}
          >
            <Pagination
              count={totalPages}
              page={currentPage}
              onChange={handlePaginationClick}
              color="primary"
            />
          </Box> */}
        </Card>
      </Box>

      {/* RIGHT SIDE — 30% */}
      <Box
        sx={{
          flex: '0 0 25%',
          height: '100%',
          paddingRight: 2,
          paddingTop: 2,
          boxSizing: 'border-box',
          overflowY: 'auto',
        }}
      >
        <Card sx={{ mb: 2, mr: 3 }}>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2, fontWeight: 'bold' }}>
              Actions
            </Typography>

            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Button
                fullWidth
                variant="contained"
                sx={{ background: '#2C2C2C' }}
              >
                Edit / Refine
              </Button>

              <Button
                fullWidth
                variant="contained"
                sx={{ background: '#77D5EA' }}
              >
                Download
              </Button>

              <Button
                fullWidth
                variant="contained"
                sx={{ background: '#5395A4' }}
              >
                {'Finlise -> CDR'}
              </Button>

              <Button
                fullWidth
                variant="contained"
                sx={{ background: '#D9D9D9' }}
              >
                Missing Field Re..
              </Button>
              <Button
                fullWidth
                variant="contained"
                sx={{ background: '#417581' }}
              >
                Regenerate
              </Button>
            </Box>
          </CardContent>
        </Card>

        {/* Confidence Score */}
        <Card sx={{ mb: 2, mr: 3 }}>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 1, fontWeight: 'bold' }}>
              Confidence Score
            </Typography>

            {/* Summary % */}
            <Box
              sx={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                mb: 1,
              }}
            >
              <Typography sx={{ fontSize: '16px', fontWeight: 500 }}>
                4/6 fields
              </Typography>

              <Typography sx={{ fontSize: '22px', fontWeight: 'bold' }}>
                67%
              </Typography>
            </Box>

            {/* Thin yellow summary bar */}
            <Box
              sx={{
                height: '8px',
                background: '#eee',
                borderRadius: '4px',
                overflow: 'hidden',
                mb: 3,
              }}
            >
              <Box
                sx={{
                  width: '67%', // dynamically use confidence %
                  height: '100%',
                  background: '#FFD700', // yellow bar
                }}
              />
            </Box>

            {/* HIGH */}
            <Box sx={{ mb: 1 }}>
              <Box
                sx={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  {/* Green Dot */}
                  <Box
                    sx={{
                      width: 10,
                      height: 10,
                      borderRadius: '50%',
                      background: 'green',
                    }}
                  />
                  <Typography>High</Typography>
                </Box>

                <Typography sx={{ fontWeight: 'bold' }}>4</Typography>
              </Box>
              <Divider sx={{ my: 1 }} />
            </Box>

            {/* MEDIUM */}
            <Box sx={{ mb: 1 }}>
              <Box
                sx={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  {/* Yellow Dot */}
                  <Box
                    sx={{
                      width: 10,
                      height: 10,
                      borderRadius: '50%',
                      background: '#FFC107',
                    }}
                  />
                  <Typography>Medium</Typography>
                </Box>

                <Typography sx={{ fontWeight: 'bold' }}>1</Typography>
              </Box>
              <Divider sx={{ my: 1 }} />
            </Box>

            {/* LOW */}
            <Box sx={{ mb: 1 }}>
              <Box
                sx={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  {/* Red Dot */}
                  <Box
                    sx={{
                      width: 10,
                      height: 10,
                      borderRadius: '50%',
                      background: 'red',
                    }}
                  />
                  <Typography>Low</Typography>
                </Box>

                <Typography sx={{ fontWeight: 'bold' }}>0</Typography>
              </Box>
              <Divider sx={{ my: 1 }} />
            </Box>

            {/* USER EDITED */}
            <Box sx={{ mb: 1 }}>
              <Box
                sx={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  {/* Grey Dot */}
                  <Box
                    sx={{
                      width: 10,
                      height: 10,
                      borderRadius: '50%',
                      background: '#9E9E9E',
                    }}
                  />
                  <Typography>User Edited</Typography>
                </Box>

                <Typography sx={{ fontWeight: 'bold' }}>12</Typography>
              </Box>
            </Box>
          </CardContent>
        </Card>
      </Box>
    </Box>
  );
};

export default ReportPage;
