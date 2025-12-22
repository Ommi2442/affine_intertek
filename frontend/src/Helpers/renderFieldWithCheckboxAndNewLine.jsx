import { Checkbox, Typography } from '@mui/material';
import React from 'react';

export const renderFieldWithCheckboxAndNewLines = (
  item,
  tIdx,
  iIdx,
  setTables,
  editMode = true
) => {
  if (!item?.field) return null;

  const text = item.field.replace(/\r\n/g, '\n');

  // Parse checkbox indexes → [6,7]
  let checkboxIndexes = [];
  try {
    checkboxIndexes = Array.isArray(item.checkbox_index)
      ? item.checkbox_index
      : JSON.parse(item.checkbox_index || '[]');
  } catch {
    checkboxIndexes = [];
  }

  let cbCounter = 0;

  // ✅ Split into lines first (IMPORTANT)
  const lines = text.split('\n');

  return (
    <div>
      {lines.map((line, lineIdx) => {
        // Line contains checkbox markers
        if (line.includes('[*]')) {
          const parts = line.split(/(\[\*\])/g);

          return (
            <Typography
              key={lineIdx}
              sx={{ fontSize: 14, whiteSpace: 'pre-wrap', mb: 1 }}
            >
              {parts.map((part, idx) => {
                if (part === '[*]') {
                  const checkboxKey = `checkbox_value_${checkboxIndexes[cbCounter]}`;
                  const checked = !!item[checkboxKey];
                  cbCounter += 1;

                  return (
                    <Checkbox
                      key={`cb-${lineIdx}-${idx}`}
                      size="small"
                      checked={checked}
                      disabled={!editMode}
                      sx={{ px: 0.5 }}
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
                    key={`txt-${lineIdx}-${idx}`}
                    component="span"
                    sx={{ fontSize: 14 }}
                  >
                    {part}
                  </Typography>
                );
              })}
            </Typography>
          );
        }

        // Normal line (no checkbox)
        return (
          <Typography
            key={lineIdx}
            sx={{ fontSize: 14, whiteSpace: 'pre-wrap', mb: 1 }}
          >
            {line}
          </Typography>
        );
      })}
    </div>
  );
};
