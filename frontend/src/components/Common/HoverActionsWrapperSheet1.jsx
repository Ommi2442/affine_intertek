/* eslint-disable */
import React from 'react';
import { IconButton, Tooltip } from '@mui/material';
import './HoverActionsWrapperSheet1.css';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ChatBubbleOutlineOutlinedIcon from '@mui/icons-material/ChatBubbleOutlineOutlined';
import MenuBookOutlinedIcon from '@mui/icons-material/MenuBookOutlined';

/**
 * Common hover action container
 */
const HoverActionWrapperSheet1 = ({
  show,
  onApprove,
  onComment,
  onBookmark,
  bookmarkDisabled = false,
}) => {
  if (!show) return null;

  return (
    <div className="dt-hover-actions-cdr-sheet1">
      {/* APPROVE → render ONLY when allowed */}
      {typeof onApprove === 'function' && (
        <IconButton size="small" onClick={onApprove}>
          <CheckCircleIcon className="dt-icon-approve" />
        </IconButton>
      )}

      {/*  COMMENT */}
      {typeof onComment === 'function' && (
        <IconButton size="small" onClick={onComment}>
          <ChatBubbleOutlineOutlinedIcon className="dt-icon-comment" />
        </IconButton>
      )}

      {/*  BOOKMARK */}
      {typeof onBookmark === 'function' && (
        <Tooltip
          arrow
          title={
            bookmarkDisabled
              ? 'PDF citation loading...'
              : 'View supporting citations'
          }
        >
          <span>
            <IconButton
              size="small"
              disabled={bookmarkDisabled}
              onClick={!bookmarkDisabled ? onBookmark : undefined}
              sx={{
                opacity: bookmarkDisabled ? 0.5 : 1,
                filter: bookmarkDisabled ? 'blur(1px)' : 'none',
                cursor: bookmarkDisabled ? 'not-allowed' : 'pointer',
                transition: 'all 0.2s ease',
              }}
            >
              <MenuBookOutlinedIcon className="dt-icon-bookmark" />
            </IconButton>
          </span>
        </Tooltip>
      )}
    </div>
  );
};

export default HoverActionWrapperSheet1;
