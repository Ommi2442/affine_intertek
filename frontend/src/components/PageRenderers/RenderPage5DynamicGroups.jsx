import React from 'react';
import { Box, Typography, Button } from '@mui/material';

export const RenderPage5DynamicGroups = ({
  items,
  setTables,
  isEditable,
  updateCell,
  editMode,
}) => {
  const PAGE_5_GROUPS = {
    reportRef: {
      left: 'Report Ref. No.',
      right: 'Item',
    },
    testsPerformed: {
      left: 'Tests performed (name of test and test clause):',
      right: 'Testing location:',
    },
  };

  const grouped = {};

  // group rows by field pair
  items.forEach((item) => {
    Object.entries(PAGE_5_GROUPS).forEach(([key, cfg]) => {
      if (item.field === cfg.left || item.field === cfg.right) {
        if (!grouped[key]) grouped[key] = [];
        grouped[key].push(item);
      }
    });
  });

  const addRow = (groupKey) => {
    setTables((prev) => {
      const next = prev.map((tbl) => ({ ...tbl, Items: [...tbl.Items] }));

      const templateLeft = grouped[groupKey][0];
      const templateRight = grouped[groupKey][1];

      if (!templateLeft || !templateRight) return prev;

      const tIdx = templateLeft.__t;

      next[tIdx].Items.push(
        {
          ...templateLeft,
          value: '',
          is_user_modified: true,
        },
        {
          ...templateRight,
          value: '',
          is_user_modified: true,
        }
      );

      return next;
    });
  };

  return Object.entries(PAGE_5_GROUPS).map(([key]) => {
    const rows = grouped[key] || [];

    const pairs = [];
    for (let i = 0; i < rows.length; i += 2) {
      pairs.push(rows.slice(i, i + 2));
    }

    return (
      <Box key={key} sx={{ mb: 3 }}>
        {pairs.map((pair, idx) => (
          <Box key={idx} sx={{ display: 'flex', gap: 2, mb: 1 }}>
            {pair.map((item) => {
              const tIdx = item.__t;
              const iIdx = item.__i;
              const editable = isEditable(item);

              return (
                <Box key={iIdx} sx={{ flex: 1 }}>
                  <Typography sx={{ fontSize: 14, mb: 0.5 }}>
                    {item.field}
                  </Typography>

                  <textarea
                    className="dt-textarea"
                    rows={2}
                    value={item.value ?? ''}
                    disabled={!editable}
                    onChange={(e) =>
                      editable && updateCell(tIdx, iIdx, e.target.value)
                    }
                  />
                </Box>
              );
            })}
          </Box>
        ))}

        {/* {editMode && (
          <Button variant="outlined" size="small" onClick={() => addRow(key)}>
            Add
          </Button>
        )} */}
      </Box>
    );
  });
};
