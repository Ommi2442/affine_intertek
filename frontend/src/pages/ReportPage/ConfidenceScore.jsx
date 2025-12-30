import React, { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import './ReportPage.css';
import { Card, CardContent, Typography, Box, Divider } from '@mui/material';
import { calculateConfidenceScore } from '../../utils/calculateConfidenceScore';
import { setConfidenceScore } from '../../redux/features/confidence/confidenceSlice';

/* ------------------ COMPONENT ------------------ */
const ConfidenceScore = ({ data }) => {
  const dispatch = useDispatch();

  // ✅ READ FROM REDUX
  const summary = useSelector((state) => state.confidence.summary);
  //console.log('summm', summary);

  useEffect(() => {
    if (!data) return;

    const result = calculateConfidenceScore(data);

    if (result) {
      dispatch(setConfidenceScore(result));
    }
  }, [data, dispatch]);

  // const summary = React.useMemo(() => {
  //   const result = calculateConfidenceScore(data);
  //   if (result) {
  //     dispatch(setConfidenceScore(result));
  //   }
  //   return result;
  // }, [data, dispatch]);

  if (!summary || summary.totalAiFields === 0) {
    return (
      <Card className="confidence-card">
        <CardContent>
          <Typography variant="h6">Confidence Score</Typography>
          <Typography color="text.secondary">
            No AI confidence data available
          </Typography>
        </CardContent>
      </Card>
    );
  }

  const { totalAiFields, high, medium, low, avgConfidence, userEditedCount } =
    summary;
  //console.log('userEditedCount', userEditedCount);

  return (
    <Card className="confidence-card">
      <CardContent>
        {/* HEADER */}
        <Typography variant="h6" className="confidence-header">
          Confidence Score
        </Typography>

        {/* SUMMARY */}
        <Box className="confidence-summary">
          <Typography>
            {high}/{totalAiFields} fields
          </Typography>
          <Typography fontWeight="bold">{avgConfidence}%</Typography>
        </Box>

        {/* PROGRESS BAR */}
        <Box className="confidence-bar">
          <Box
            className="confidence-fill"
            style={{ width: `${avgConfidence}%` }}
          />
        </Box>

        {/* BREAKDOWN */}
        {[
          { label: 'High', count: high, color: 'green' },
          { label: 'Medium', count: medium, color: 'yellow' },
          { label: 'Low', count: low, color: 'red' },
          { label: 'User Edited', count: userEditedCount, color: 'grey' },
        ].map((row, i) => (
          <Box key={i} className="confidence-row">
            <Box className="confidence-label">
              <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                <span className={`dot ${row.color}`} />
                <Typography>{row.label}</Typography>
              </Box>
              <Typography fontWeight="bold">{row.count}</Typography>
            </Box>

            {i < 3 && <Divider />}
          </Box>
        ))}
      </CardContent>
    </Card>
  );
};

export default ConfidenceScore;
