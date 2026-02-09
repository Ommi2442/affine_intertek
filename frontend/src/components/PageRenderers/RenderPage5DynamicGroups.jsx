import React from 'react';
import { Box, Typography } from '@mui/material';

export const RenderPage5DynamicGroups = ({
  items,
  setTables,
  isEditable,
  updateCell,
  editMode,
  hovered,
  setHovered,
  renderHoverActions,
  renderConfidenceColor,
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
  const matchedItems = new Set();

  // Group Report Ref & Tests Performed
  items.forEach((item) => {
    Object.entries(PAGE_5_GROUPS).forEach(([key, cfg]) => {
      if (item.field === cfg.left || item.field === cfg.right) {
        if (!grouped[key]) grouped[key] = [];
        grouped[key].push(item);
        matchedItems.add(item);
      }
    });
  });

  const ungroupedItems = items.filter((item) => !matchedItems.has(item));

  //  Clean polluted value (removes field prefix if backend sends it)
  const cleanValue = (field, value) => {
    if (!field || !value) return value;

    const label = field.split('\n')[0].trim(); // only first line of field
    let v = value.trim();

    if (v.toLowerCase().startsWith(label.toLowerCase())) {
      v = v.slice(label.length).trim();
    }

    v = v.replace(/^[:\-\s]+/, '').trim();
    return v;
  };

  //  Render FIELD with unlimited checkboxes for [*]
  const renderFieldWithCheckboxes = (item, editable, tIdx, iIdx) => {
    const parts = (item.field || '').split('[*]');

    const checkboxIndexes = Array.isArray(item.checkbox_index)
      ? item.checkbox_index
      : JSON.parse(item.checkbox_index || '[]');

    let cbCounter = 0;

    return (
      <Typography sx={{ fontSize: 14, whiteSpace: 'pre-wrap', mb: 1 }}>
        {parts.map((part, idx) => {
          const elements = [];

          if (part) {
            elements.push(<span key={`txt-${idx}`}>{part}</span>);
          }

          if (idx < parts.length - 1) {
            const checkboxKey = `checkbox_value_${checkboxIndexes[cbCounter]}`;
            const checked = !!item[checkboxKey];
            const localIndex = cbCounter;

            elements.push(
              <input
                key={`cb-${idx}`}
                type="checkbox"
                checked={checked}
                disabled={!editable}
                onChange={() => {
                  setTables((prev) => {
                    const next = prev.map((tbl) => ({
                      ...tbl,
                      Items: [...tbl.Items],
                    }));

                    next[tIdx].Items[iIdx] = {
                      ...next[tIdx].Items[iIdx],
                      [checkboxKey]: !checked,
                      is_user_modified: true,
                      is_user_edited: true,
                    };

                    return next;
                  });
                }}
                style={{ margin: '0 6px' }}
              />
            );

            cbCounter++;
          }

          return elements;
        })}
      </Typography>
    );
  };

  //  Render Summary / Statement blocks
  const renderUngroupedItem = (item) => {
    const tIdx = item.__t;
    const iIdx = item.__i;
    const editable = isEditable(item);

    const displayValue = cleanValue(item.field, item.value);

    return (
      <Box
        key={`${tIdx}-${iIdx}`}
        sx={{ mb: 3 }}
        className="dt-value-column-page5 dt-relative"
        onMouseEnter={() => setHovered({ t: tIdx, i: iIdx })}
        onMouseLeave={() => setHovered({ t: null, i: null })}
      >
        {/* FIELD + MULTIPLE CHECKBOX SUPPORT */}
        {renderFieldWithCheckboxes(item, editable, tIdx, iIdx)}

        {/* VALUE TEXTBOX (ONLY CLEAN VALUE SHOWN) */}
        {item.value != null && item.value !== '' && (
          <div
            style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: 12,
            }}
          >
            <textarea
              className="dt-textarea"
              rows={item.rendering_row || 3}
              value={displayValue}
              disabled={!editable}
              onChange={(e) =>
                editable && updateCell(tIdx, iIdx, e.target.value)
              }
              style={{ flex: 1 }}
            />
            <div style={{ flexShrink: 0 }}>
              {renderConfidenceColor(
                item.confidence,
                item.is_user_edited,
                item.ai_fillable,
                item.accuracy_level
              )}
            </div>
          </div>
        )}
        {renderHoverActions(tIdx, iIdx)}
      </Box>
    );
  };

  return (
    <Box>
      {/* ================= GROUPED (REPORT REF + TESTS PERFORMED) ================= */}
      {Object.entries(PAGE_5_GROUPS).map(([key]) => {
        const rows = grouped[key] || [];

        if (rows.length === 0) return null;

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
                    <Box
                      key={`${tIdx}-${iIdx}`}
                      sx={{ flex: 1 }}
                      className="dt-value-column-page5 dt-relative"
                      onMouseEnter={() => setHovered({ t: tIdx, i: iIdx })}
                      onMouseLeave={() => setHovered({ t: null, i: null })}
                    >
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
                      {renderHoverActions(tIdx, iIdx)}
                    </Box>
                  );
                })}
              </Box>
            ))}
          </Box>
        );
      })}

      {/* ================= SUMMARY + STATEMENT ================= */}
      {ungroupedItems.map(renderUngroupedItem)}
    </Box>
  );
};
