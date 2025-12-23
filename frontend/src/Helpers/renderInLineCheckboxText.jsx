import React from 'react';
import { Checkbox, Typography } from '@mui/material';

export const renderInlineCheckboxText = (
  text,
  checkboxIndexes,
  item,
  tIdx,
  iIdx,
  editMode,
  setTables
) => {
  let cbCounter = 0;

  const parts = text.split(/(\[\*\])/g);

  return parts.map((part, idx) => {
    if (part === '[*]') {
      const checkboxKey = `checkbox_value_${checkboxIndexes[cbCounter]}`;
      const checked = !!item[checkboxKey];
      cbCounter += 1;

      return (
        <Checkbox
          key={`cb-${idx}`}
          size="small"
          checked={checked}
          disabled={!editMode}
          sx={{ padding: '0 4px' }}
          onChange={() => {
            setTables((prev) => {
              const next = prev.map((tbl) => ({
                ...tbl,
                Items: [...tbl.Items],
              }));

              next[tIdx].Items[iIdx] = {
                ...next[tIdx].Items[iIdx],
                [checkboxKey]: !checked,
              };

              return next;
            });
          }}
        />
      );
    }

    return (
      <Typography
        key={`txt-${idx}`}
        component="span"
        sx={{ fontSize: 14, whiteSpace: 'pre-wrap' }}
      >
        {part}
      </Typography>
    );
  });
};
