import React, { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import './ReportPage.css';
import { Card, CardContent, Typography, Box, Divider } from '@mui/material';
import { calculateConfidenceScore } from '../../utils/calculateConfidenceScore';
import { setConfidenceScore } from '../../redux/features/confidence/confidenceSlice';
import { idb_get, STORES } from '../../utils/idb';

/* ------------------ COMPONENT ------------------ */
const ConfidenceScore = ({ data, confidenceTick, projectId, reportType }) => {
  const dispatch = useDispatch();

  // READ FROM REDUX
  const summary = useSelector((state) => state.confidence.summary);
  useEffect(() => {
    let isMounted = true;

    const loadAndCalculate = async () => {
      // 🔒 ONLY run when final data exists
      if (!data) return;
      console.log(
        'live edited clauses',
        data?.Tables?.flatMap((t) => t.Items).filter(
          (i) => i.task_type == null && i.is_user_edited
        ).length
      );

      let sourceData = data;

      /* ---------- TRF ---------- */
      if (reportType === 'trf') {
        //console.log('data', data);
        // const idbTables = await idb_get('tables');
        // if (Array.isArray(idbTables) && idbTables.length > 0) {
        //   sourceData = { Tables: idbTables };
        // }
        sourceData = data;
      }

      /* ---------- CDR ---------- */
      if (reportType === 'cdr') {
        const cdrKey = `cdr_report_${projectId ?? 'default'}`;
        const idbCdr = await idb_get(cdrKey, STORES.CDR);
        if (idbCdr?.Sheets?.length) {
          sourceData = idbCdr;
        }
      }

      if (!sourceData) return;
      let normalizedData = sourceData;

      /* ---------- LETTER ---------- */
      if (reportType === 'letter' && sourceData?.pages) {
        normalizedData = {
          Tables: sourceData.pages.map((p) => ({
            Items: p.items || [],
          })),
        };
      }

      const result = calculateConfidenceScore(normalizedData);

      // const result = calculateConfidenceScore(sourceData);
      //console.log('result', result);
      if (result && isMounted) {
        dispatch(setConfidenceScore(result));
      }
    };

    loadAndCalculate();
    return () => {
      isMounted = false;
    };
  }, [data, confidenceTick, projectId, reportType, dispatch]);
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
        {/* HEADER */}
        <Typography variant="h6" className="confidence-header">
          Confidence Score
        </Typography>

        {/* SUMMARY */}
        <Box className="confidence-summary">
          <Typography>
            {high + userEditedCount}/{totalAiFields} fields
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
