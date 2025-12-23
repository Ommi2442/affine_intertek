import React from 'react';
import { Typography } from '@mui/material';

export const Page8FieldTextarea = ({
  fieldLabel,
  value,
  rows,
  editable,
  updateCell,
  tIdx,
  iIdx,
  renderConfidenceColor,
  first,
}) => {
  return (
    <div>
      <Typography
        sx={{
          fontSize: 14,
          fontWeight: 500,
          whiteSpace: 'pre-wrap',
          mb: 1,
        }}
      >
        {fieldLabel}
      </Typography>

      <div style={{ display: 'flex' }}>
        <textarea
          className="dt-textarea dt-textarea-with-actions"
          value={value}
          rows={rows}
          disabled={!editable}
          onChange={(e) => editable && updateCell(tIdx, iIdx, e.target.value)}
        />
        {renderConfidenceColor(first.confidence)}
      </div>
    </div>
  );
};
