import { Checkbox, Typography } from '@mui/material';
import React from 'react';
export const renderFieldWithCheckboxAndNewLines = (
  item,
  tIdx,
  iIdx,
  updateCell,
  setTables
) => {
  if (!item?.field) return null;

  const lines = item.field.split('\n').filter((l) => l.trim() !== '');

  return (
    <>
      {/* First line (title / heading) */}
      <Typography sx={{ fontSize: 14, mb: 1 }}>{lines[0]}</Typography>

      {/* Remaining lines with checkbox */}
      {lines.slice(1).map((line, idx) => (
        <div
          key={idx}
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            gap: 8,
            marginBottom: 8,
          }}
        >
          <Checkbox
            size="small"
            checked={!!item.checkbox_value}
            onChange={(e) => {
              setTables((prev) => {
                const next = prev.map((tbl) => ({
                  ...tbl,
                  Items: [...tbl.Items],
                }));

                next[tIdx].Items[iIdx] = {
                  ...next[tIdx].Items[iIdx],
                  checkbox_value: e.target.checked,
                };

                return next;
              });
            }}
          />

          <Typography sx={{ fontSize: 14 }}>{line}</Typography>
        </div>
      ))}
    </>
  );
};
