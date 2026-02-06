import React from 'react';
import { Card, CardContent, Typography, Box, Divider } from '@mui/material';
import '../ReportPage.css';

const ConfidenceScoreCard = ({ summary }) => {
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

  return (
    <Card className="confidence-card">
      <CardContent>
        <Typography variant="h6" className="confidence-header">
          Confidence Score
        </Typography>

        <Box className="confidence-summary">
          <Typography>
            {high + userEditedCount}/{totalAiFields} fields
          </Typography>
          <Typography fontWeight="bold">{avgConfidence}%</Typography>
        </Box>

        <Box className="confidence-bar">
          <Box
            className="confidence-fill"
            style={{ width: `${avgConfidence}%` }}
          />
        </Box>

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

export default ConfidenceScoreCard;
