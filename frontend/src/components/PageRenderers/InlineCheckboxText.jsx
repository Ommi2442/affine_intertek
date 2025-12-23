import React from 'react';
import { Checkbox, Typography } from '@mui/material';

export const InlineCheckboxText = ({
  text,
  checkboxIndexes = [],
  item,
  tIdx,
  iIdx,
  setTables,
  editMode,
}) => {
  let cbCounter = 0;

  return (
    <Typography sx={{ fontSize: 14, whiteSpace: 'pre-wrap', mb: 1 }}>
      {text.split(/(\[\*\])/g).map((part, idx) => {
        if (part === '[*]') {
          const index = checkboxIndexes?.[cbCounter];
          if (index === undefined) return null;

          const checkboxKey = `checkbox_value_${index}`;
          const checked = !!(item && item[checkboxKey]);
          cbCounter += 1;

          return (
            <Checkbox
              key={idx}
              size="small"
              checked={checked}
              disabled={!editMode}
              sx={{ px: '4px' }}
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
          <Typography key={idx} component="span" sx={{ fontSize: 14 }}>
            {part}
          </Typography>
        );
      })}
    </Typography>
  );
};
