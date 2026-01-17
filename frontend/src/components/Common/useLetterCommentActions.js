/* eslint-disable */
import { useState, useRef } from 'react';
import { getLoggedInUser } from './getLoggedInUser';

/**
 * Letter comments work on flat items (not sheet + index like CDR)
 */
export const useLetterCommentActions = (letterJson) => {
  const [isCommentOpen, setIsCommentOpen] = useState(false);
  const [commentHistory, setCommentHistory] = useState([]);
  const [currentCommentText, setCurrentCommentText] = useState('');
  const commentTargetRef = useRef(null);

  /* -------- OPEN COMMENT -------- */
  const openComment = (item) => {
    if (!item) return;

    commentTargetRef.current = item;

    const history = Array.isArray(item.user_comments) ? item.user_comments : [];

    const latest =
      history.length > 0 ? history[history.length - 1].comment : '';

    setCommentHistory(history);
    setCurrentCommentText(latest);
    setIsCommentOpen(true);
  };

  /* -------- SAVE COMMENT -------- */
  const saveComment = () => {
    const item = commentTargetRef.current;
    if (!item) return;

    const newComment = {
      comment: currentCommentText,
      Submited_By: getLoggedInUser(),
      Submited_at: new Date().toISOString(),
    };

    item.user_comments = [...(item.user_comments || []), newComment];

    setCommentHistory(item.user_comments);
    setIsCommentOpen(false);
  };

  return {
    isCommentOpen,
    setIsCommentOpen,
    commentHistory,
    currentCommentText,
    setCurrentCommentText,
    openComment,
    saveComment,
  };
};
