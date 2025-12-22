import React from 'react';
import { Typography } from '@mui/material';
import { InlineCheckboxText } from './InlineCheckboxText';

export const Page7GeneralRemarks = (props) => {
  const { first } = props;
  const checkboxIndexes = JSON.parse(first.checkbox_index || '[]');

  return (
    <div>
      <Typography sx={{ fontSize: 14, fontWeight: 500, mb: 1 }}>
        {props.fieldLabel}
      </Typography>

      {(first.value || '').split('\n').map((line, idx) =>
        line.includes('[*]') ? (
          <InlineCheckboxText
            key={idx}
            text={line}
            checkboxIndexes={checkboxIndexes}
            {...props}
          />
        ) : (
          <Typography
            key={idx}
            sx={{ fontSize: 14, whiteSpace: 'pre-wrap', mb: 1 }}
          >
            {line}
          </Typography>
        )
      )}
    </div>
  );
};
