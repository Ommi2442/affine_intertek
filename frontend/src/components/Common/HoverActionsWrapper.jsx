/* eslint-disable */
import React from 'react';
import { IconButton } from '@mui/material';

import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ChatBubbleOutlineOutlinedIcon from '@mui/icons-material/ChatBubbleOutlineOutlined';
import MenuBookOutlinedIcon from '@mui/icons-material/MenuBookOutlined';

/**
 * Common hover action container
 */
const HoverActionWrapper = ({ show, onApprove, onComment, onBookmark }) => {
  if (!show) return null;

  return (
    <div className="dt-hover-actions">
      {/* ✅ APPROVE */}
      <IconButton size="small" onClick={onApprove} disabled={!onApprove}>
        <CheckCircleIcon className="dt-icon-approve" />
      </IconButton>

      {/* 💬 COMMENT */}
      <IconButton size="small" onClick={onComment} disabled={!onComment}>
        <ChatBubbleOutlineOutlinedIcon className="dt-icon-comment" />
      </IconButton>

      {/* 🔖 BOOKMARK */}
      <IconButton size="small" onClick={onBookmark} disabled={!onBookmark}>
        <MenuBookOutlinedIcon className="dt-icon-bookmark" />
      </IconButton>
    </div>
  );
};

export default HoverActionWrapper;
