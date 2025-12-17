/* eslint-disable */
/* eslint quotes: "off" */
import React, {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from 'react';
import {
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  IconButton,
  Divider,
  TextField,
  Button,
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ChatBubbleOutlineOutlinedIcon from '@mui/icons-material/ChatBubbleOutlineOutlined';
import MenuBookOutlinedIcon from '@mui/icons-material/MenuBookOutlined';
import CommentDialog from './CommentDialog'; // assumes you have this component
import './RemainingPagesData.css';

/**
 * RemainingPagesData
 *
 * Props:
 *  - jsonData: expected structure: [{ Page: 43, Items: [ { type: "clause_item" | "field_item", ... }, ... ] }, ...]
 *
 * ForwardRef exposes:
 *  - getUpdatedJson(): returns the current pages array (same shape as passed)
 *  - getFieldValue(fieldName): returns first matching item's value ('' if not found)
 *  - setFieldValue(fieldName, newValue): updates first matching item in-state
 *
 * Behavior:
 *  - Renders one section per page
 *  - Renders clause_item as clause + field in the left columns
 *  - Renders field_item as field/value rows
 *  - user_editable === true -> editable textarea / textfield
 *  - Hover actions (approve/comment/bookmark) visible ONLY when item is editable (strict)
 *  - Comments: opens CommentDialog (only for editable items)
 */

const RemainingPagesData = forwardRef(
  ({ jsonData = [], onBookmarkClick, onApprove }, ref) => {
    // internal state keeps a deep-ish copy so edits don't mutate original object
    const [pages, setPages] = useState([]);
    const [hovered, setHovered] = useState({ pIndex: null, itemIndex: null });
    const [isCommentOpen, setIsCommentOpen] = useState(false);
    const [currentCommentText, setCurrentCommentText] = useState('');
    const commentTargetRef = useRef({ pIndex: null, itemIndex: null });

    // initialize pages when jsonData changes
    useEffect(() => {
      if (!Array.isArray(jsonData)) {
        setPages([]);
        return;
      }
      // Clone to avoid mutating the source file object
      const deep = jsonData.map((p) => ({
        Page: p.Page,
        Items: (p.Items || []).map((it) => ({ ...it })),
      }));
      setPages(deep);
    }, [jsonData]);

    // Imperative handle for parent
    useImperativeHandle(
      ref,
      () => ({
        getUpdatedJson: () => pages,
        getFieldValue: (fieldName) => {
          for (const p of pages) {
            for (const it of p.Items || []) {
              if ((it.field ?? it.Field) === fieldName) return it.value ?? '';
            }
          }
          return '';
        },
        setFieldValue: (fieldName, newValue) => {
          setPages((prev) =>
            prev.map((pg) => ({
              ...pg,
              Items: (pg.Items || []).map((it) =>
                (it.field ?? it.Field) === fieldName
                  ? { ...it, value: newValue }
                  : it
              ),
            }))
          );
        },
      }),
      [pages]
    );

    // helper: check editable (strict)
    const isItemEditable = (item) => {
      if (!item) return false;
      const isTextbox = !(item.is_textbox === false);
      return item.user_editable === true && isTextbox;
    };

    // update cell value
    const updateCell = (pIndex, idx, val) => {
      setPages((prev) =>
        prev.map((pg, pi) =>
          pi !== pIndex
            ? pg
            : {
                ...pg,
                Items: pg.Items.map((it, ii) =>
                  ii === idx ? { ...it, value: val } : it
                ),
              }
        )
      );
    };

    // comment handling
    const openComment = (pIndex, idx) => {
      const item = pages?.[pIndex]?.Items?.[idx];
      if (!item) return;
      if (!isItemEditable(item)) return; // strict mode: only editable items can have comments
      commentTargetRef.current = { pIndex, idx };
      setCurrentCommentText(item._comment || '');
      setIsCommentOpen(true);
    };

    const saveComment = () => {
      const { pIndex, idx } = commentTargetRef.current;
      if (pIndex == null || idx == null) {
        setIsCommentOpen(false);
        return;
      }
      setPages((prev) =>
        prev.map((pg, pi) =>
          pi !== pIndex
            ? pg
            : {
                ...pg,
                Items: pg.Items.map((it, ii) =>
                  ii === idx ? { ...it, _comment: currentCommentText } : it
                ),
              }
        )
      );
      setIsCommentOpen(false);
    };

    // hover actions render
    const renderHoverActions = (pIndex, idx, editable, item) => {
      if (!editable) return null;
      if (hovered.pIndex !== pIndex || hovered.itemIndex !== idx) return null;

      return (
        <div className="rpd-hover-actions">
          <IconButton size="small" onClick={() => onApprove?.(pIndex, idx)}>
            <CheckCircleIcon className="rpd-icon-approve" />
          </IconButton>

          <IconButton size="small" onClick={() => openComment(pIndex, idx)}>
            <ChatBubbleOutlineOutlinedIcon className="rpd-icon-comment" />
          </IconButton>

          <IconButton
            size="small"
            onClick={() => onBookmarkClick?.(pIndex, idx)}
          >
            <MenuBookOutlinedIcon className="rpd-icon-bookmark" />
          </IconButton>
        </div>
      );
    };

    // Render a single item row based on type
    const renderItemRow = (item, pIndex, idx) => {
      const editable = isItemEditable(item);
      const value = item.value ?? item.Value ?? '';

      // Clause rows: show clause in left column and field text in middle
      if (item.type === 'clause_item') {
        return (
          <TableRow key={`p${pIndex}-i${idx}`}>
            <TableCell sx={{ width: '10%', verticalAlign: 'top' }}>
              {item.clause ?? ''}
            </TableCell>
            <TableCell
              sx={{ width: '45%', verticalAlign: 'top', fontWeight: 700 }}
            >
              {item.field ?? ''}
            </TableCell>

            <TableCell
              sx={{ width: '45%', verticalAlign: 'top', position: 'relative' }}
              onMouseEnter={() => setHovered({ pIndex, itemIndex: idx })}
              onMouseLeave={() => setHovered({ pIndex: null, itemIndex: null })}
            >
              {/* If editable show textarea else plain text */}
              {editable ? (
                <textarea
                  className="rpd-textarea"
                  value={value}
                  rows={item.rendering_row || 2}
                  onChange={(e) => updateCell(pIndex, idx, e.target.value)}
                />
              ) : (
                <Typography>{value}</Typography>
              )}

              {renderHoverActions(pIndex, idx, editable, item)}

              {item._comment && (
                <Typography variant="caption" className="rpd-comment-caption">
                  💬 {item._comment}
                </Typography>
              )}
            </TableCell>
          </TableRow>
        );
      }

      // Field rows: typically no clause number in left column
      return (
        <TableRow key={`p${pIndex}-i${idx}`}>
          <TableCell sx={{ width: '10%', verticalAlign: 'top' }} />
          <TableCell sx={{ width: '45%', verticalAlign: 'top' }}>
            {item.field ?? ''}
          </TableCell>

          <TableCell
            sx={{ width: '45%', verticalAlign: 'top', position: 'relative' }}
            onMouseEnter={() => setHovered({ pIndex, itemIndex: idx })}
            onMouseLeave={() => setHovered({ pIndex: null, itemIndex: null })}
          >
            {item.checkbox_answer_UI &&
            Array.isArray((value || '').split('\n')) ? (
              <Box>
                {(value || '')
                  .split('\n')
                  .map((opt, oi) => opt.trim())
                  .filter(Boolean)
                  .map((opt, oi) => (
                    <Box
                      key={oi}
                      sx={{ display: 'flex', alignItems: 'center', gap: 1 }}
                    >
                      <input type="checkbox" disabled />
                      <Typography variant="body2">{opt}</Typography>
                    </Box>
                  ))}
              </Box>
            ) : item.task_type === 'remark' ? (
              // remarks are multiline
              editable ? (
                <textarea
                  className="rpd-textarea"
                  value={value}
                  rows={item.rendering_row || 2}
                  onChange={(e) => updateCell(pIndex, idx, e.target.value)}
                />
              ) : (
                <Typography>{value}</Typography>
              )
            ) : editable ? (
              // default editable single-line
              <TextField
                fullWidth
                size="small"
                value={value}
                onChange={(e) => updateCell(pIndex, idx, e.target.value)}
              />
            ) : (
              <Typography>{value}</Typography>
            )}

            {renderHoverActions(pIndex, idx, editable, item)}

            {item._comment && (
              <Typography variant="caption" className="rpd-comment-caption">
                💬 {item._comment}
              </Typography>
            )}
          </TableCell>
        </TableRow>
      );
    };

    if (!pages || pages.length === 0) {
      return <Typography>No data to display</Typography>;
    }

    return (
      <div className="rpd-root">
        {pages.map((page, pIndex) => (
          <Paper key={`page-${page.Page}-${pIndex}`} sx={{ mb: 3, p: 2 }}>
            <Box
              sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}
            >
              <Typography variant="h6">Page {page.Page}</Typography>
              <Box>
                <Button
                  size="small"
                  variant="outlined"
                  sx={{ mr: 1 }}
                  onClick={() => {
                    // export that page's JSON as console log (debug)
                    // parent can also use getUpdatedJson()
                    console.log('Export page', page.Page, page);
                  }}
                >
                  Export Page JSON
                </Button>
              </Box>
            </Box>

            <TableContainer component={Paper} variant="outlined">
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 700, width: '10%' }}>
                      Clause
                    </TableCell>
                    <TableCell sx={{ fontWeight: 700, width: '45%' }}>
                      Requirement / Field
                    </TableCell>
                    <TableCell sx={{ fontWeight: 700, width: '45%' }}>
                      Result / Input
                    </TableCell>
                  </TableRow>
                </TableHead>

                <TableBody>
                  {(page.Items || []).map((item, idx) =>
                    renderItemRow(item, pIndex, idx)
                  )}
                </TableBody>
              </Table>
            </TableContainer>

            <Divider sx={{ mt: 1 }} />
          </Paper>
        ))}

        <CommentDialog
          open={isCommentOpen}
          onClose={() => setIsCommentOpen(false)}
          comments={[]} // adapt if you have stored comments list
          currentComment={currentCommentText}
          setCurrentComment={setCurrentCommentText}
          onSubmit={saveComment}
        />
      </div>
    );
  }
);

export default RemainingPagesData;
