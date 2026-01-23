/* eslint-disable */
import React from 'react';
import { IconButton } from '@mui/material';
import './HoverActionsWrapper.css';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ChatBubbleOutlineOutlinedIcon from '@mui/icons-material/ChatBubbleOutlineOutlined';
import MenuBookOutlinedIcon from '@mui/icons-material/MenuBookOutlined';

/**
 * Common hover action container
 */
const HoverActionWrapper = ({ show, onApprove, onComment, onBookmark }) => {
  if (!show) return null;

  return (
    <div className="dt-hover-actions-cdr">
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
        <IconButton size="small" onClick={onBookmark}>
          <MenuBookOutlinedIcon className="dt-icon-bookmark" />
        </IconButton>
      )}
    </div>
  );
};

export default HoverActionWrapper;
