/* eslint-disable */
import React, {
  forwardRef,
  useImperativeHandle,
  useRef,
  useEffect,
} from 'react';

import LetterPage1 from './LetterPage1';
import LetterPage2 from './LetterPage2';
import LetterPage3 from './LetterPage3';
import LetterPage4 from './LetterPage4';
import LetterPage5 from './LetterPage5';
import LetterPage6 from './LetterPage6';
import CommentDialog from '../CommentDialog';
import { useLetterCommentActions } from '../Common/useLetterCommentActions';

const TOTAL_PAGES = 6;

const LetterReport = forwardRef(
  (
    { jsonData, editMode, onPageChange, onConfidenceChange, onBookmarkClick },
    ref
  ) => {
    const pageRefs = useRef([]);
    const containerRef = useRef(null);
    const {
      isCommentOpen,
      setIsCommentOpen,
      commentHistory,
      currentCommentText,
      setCurrentCommentText,
      openComment,
      saveComment,
    } = useLetterCommentActions(jsonData);

    useImperativeHandle(ref, () => ({
      getUpdatedJson: () => jsonData,
      scrollToPage: (page) => {
        const el = pageRefs.current[page - 1];
        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      },
    }));

    const handleApprove = (item) => {
      if (!item) return;

      const c = Number(item.confidence);
      const normalized = c <= 1 ? Math.round(c * 100) : Math.round(c);

      if (normalized < 75 || item.is_user_edited) {
        item.confidence = 100;
      }

      item.is_user_approved = true;
      onConfidenceChange?.();
    };

    /*  Detect which page is in view while scrolling */
    useEffect(() => {
      if (!containerRef.current) return;

      const observer = new IntersectionObserver(
        (entries) => {
          const visible = entries
            .filter((e) => e.isIntersecting)
            .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];

          if (!visible) return;

          const page = Number(visible.target.dataset.page);
          onPageChange?.(page);
        },
        {
          root: containerRef.current,
          threshold: [0.4, 0.6], // page must be ~half visible
        }
      );

      pageRefs.current.forEach((el) => el && observer.observe(el));

      return () => observer.disconnect();
    }, [onPageChange]);

    return (
      <div ref={containerRef} className="letter-scroll-container">
        {Array.from({ length: TOTAL_PAGES }).map((_, i) => {
          const p = i + 1;
          return (
            <div
              key={p}
              ref={(el) => (pageRefs.current[i] = el)}
              data-page={p}
              className="letter-page-wrapper"
            >
              {p === 1 && (
                <LetterPage1
                  json={jsonData}
                  editMode={editMode}
                  handleApprove={handleApprove}
                  openComment={openComment}
                  onBookmarkClick={onBookmarkClick}
                />
              )}
              {p === 2 && (
                <LetterPage2
                  json={jsonData}
                  editMode={editMode}
                  handleApprove={handleApprove}
                  openComment={openComment}
                  onBookmarkClick={onBookmarkClick}
                />
              )}
              {p === 3 && (
                <LetterPage3
                  json={jsonData}
                  editMode={editMode}
                  handleApprove={handleApprove}
                  openComment={openComment}
                  onBookmarkClick={onBookmarkClick}
                />
              )}
              {p === 4 && (
                <LetterPage4
                  json={jsonData}
                  editMode={editMode}
                  handleApprove={handleApprove}
                  openComment={openComment}
                  onBookmarkClick={onBookmarkClick}
                />
              )}
              {p === 5 && (
                <LetterPage5
                  json={jsonData}
                  editMode={editMode}
                  handleApprove={handleApprove}
                  openComment={openComment}
                  onBookmarkClick={onBookmarkClick}
                />
              )}
              {p === 6 && (
                <LetterPage6
                  json={jsonData}
                  editMode={editMode}
                  handleApprove={handleApprove}
                  openComment={openComment}
                  onBookmarkClick={onBookmarkClick}
                />
              )}
            </div>
          );
        })}
        <CommentDialog
          open={isCommentOpen}
          onClose={() => setIsCommentOpen(false)}
          comments={commentHistory}
          currentComment={currentCommentText}
          setCurrentComment={setCurrentCommentText}
          onSubmit={saveComment}
        />
      </div>
    );
  }
);

export default LetterReport;
