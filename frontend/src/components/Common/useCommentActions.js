/* eslint-disable */
import { useState, useRef } from 'react';
import { getLoggedInUser } from './getLoggedInUser';

export const useCommentActions = (sheet) => {
  const [isCommentOpen, setIsCommentOpen] = useState(false);
  const [commentHistory, setCommentHistory] = useState([]);
  const [currentCommentText, setCurrentCommentText] = useState('');
  const commentTargetRef = useRef(null);

  /* -------- OPEN COMMENT -------- */
  const openComment = (sheetNo, index) => {
    commentTargetRef.current = { sheetNo, index };

    const item = sheet.Items[index];

    const history = Array.isArray(item?.user_comments)
      ? item.user_comments
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

    const newComment = {
      comment: currentCommentText,
      Submited_By: getLoggedInUser(),
      Submited_at: new Date().toISOString(),
    };

    sheet.Items[index].user_comments = [
      ...(sheet.Items[index].user_comments || []),
      newComment,
    ];

    setCommentHistory(sheet.Items[index].user_comments);
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
