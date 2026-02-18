import { useRef, useState } from 'react';
import { getLoggedInUser } from './getLoggedInUser';

export const useCommentActions = (sheet, rowKey = 'Items') => {
  const [isCommentOpen, setIsCommentOpen] = useState(false);
  const [commentHistory, setCommentHistory] = useState([]);
  const [currentCommentText, setCurrentCommentText] = useState('');
  const commentTargetRef = useRef(null);

  /* -------- OPEN COMMENT -------- */
  const openComment = (sheetNo, index) => {
    commentTargetRef.current = { sheetNo, index };

    const target = sheet?.[rowKey]?.[index];

    if (!target) return;

    const history = Array.isArray(target.user_comments)
      ? target.user_comments
      : [];

    const latestComment =
      history.length > 0 ? history[history.length - 1].comment : '';

    setCommentHistory(history);
    setCurrentCommentText(latestComment);
    setIsCommentOpen(true);
  };

  /* -------- SAVE COMMENT -------- */
  const saveComment = () => {
    const { index } = commentTargetRef.current || {};
    if (index == null) return;

    const target = sheet?.[rowKey]?.[index];
    if (!target) return;

    const newComment = {
      comment: currentCommentText,
      Submited_By: getLoggedInUser(),
      Submited_at: new Date().toISOString(),
    };

    target.user_comments = [...(target.user_comments || []), newComment];

    setCommentHistory(target.user_comments);
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
