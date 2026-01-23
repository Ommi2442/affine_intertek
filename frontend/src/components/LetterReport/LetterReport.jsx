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
import { idb_get, idb_set, STORES } from '../../utils/idb';

const TOTAL_PAGES = 6;

const LetterReport = forwardRef(
  (
    {
      jsonData,
      editMode,
      projectId,
      onPageChange,
      onConfidenceChange,
      onBookmarkClick,
    },
    ref
  ) => {
    const storageKey = `letter_report_${projectId ?? 'default'}`;

    const pageRefs = useRef([]);
    const containerRef = useRef(null);
    const [fullJson, setFullJson] = React.useState(null);
    const effectiveJson = fullJson || jsonData;

    const {
      isCommentOpen,
      setIsCommentOpen,
      commentHistory,
      currentCommentText,
      setCurrentCommentText,
      openComment,
      saveComment,
    } = useLetterCommentActions(effectiveJson);

    useImperativeHandle(ref, () => ({
      getUpdatedJson: () => effectiveJson,
      scrollToPage: (page) => {
        const el = pageRefs.current[page - 1];
        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      },
    }));

    const handleApprove = async (item) => {
      if (!item) return;

      let updatedJson = null;

      setFullJson((prev) => {
        if (!prev) return prev;

        const next = JSON.parse(JSON.stringify(prev));

        next.Tables.forEach((t) => {
          t.Items.forEach((i) => {
            if (
              (i.field && item.field && i.field === item.field) ||
              (i.label && item.label && i.label === item.label)
            ) {
              const c = Number(i.confidence);
              const normalized = c <= 1 ? Math.round(c * 100) : Math.round(c);
              const isMediumOrLow =
                !Number.isNaN(normalized) && normalized < 75;

              i.is_user_edited = true;
              i.is_user_approved = true;
              i.confidence = isMediumOrLow ? 100 : i.confidence;
            }
          });
        });

        updatedJson = next;
        return next;
      });

      if (updatedJson) {
        await idb_set(storageKey, updatedJson, STORES.LETTER);
      }

      onConfidenceChange?.();
    };

    useEffect(() => {
      if (!projectId) return;

      let cancelled = false;

      const load = async () => {
        const saved = await idb_get(storageKey, STORES.LETTER);

        // CASE 1: IndexedDB exists → use it (refresh / revisit)
        if (saved) {
          console.log('Letter loaded from IndexedDB');
          if (!cancelled) setFullJson(normalizeLetterJson(saved));
          return;
        }

        // CASE 2: First time for this project → use API and cache it
        if (jsonData) {
          console.log('Letter loaded from API and cached');
          const normalized = normalizeLetterJson(jsonData);
          if (!cancelled) setFullJson(normalized);
          await idb_set(storageKey, normalized, STORES.LETTER);
        }
      };

      load();

      return () => {
        cancelled = true;
      };
    }, [storageKey]);

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
    if (!effectiveJson) return null;

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
                  json={effectiveJson}
                  editMode={editMode}
                  handleApprove={handleApprove}
                  openComment={openComment}
                  onBookmarkClick={onBookmarkClick}
                  onConfidenceChange={onConfidenceChange}
                />
              )}
              {p === 2 && (
                <LetterPage2
                  json={effectiveJson}
                  editMode={editMode}
                  handleApprove={handleApprove}
                  openComment={openComment}
                  onBookmarkClick={onBookmarkClick}
                  onConfidenceChange={onConfidenceChange}
                />
              )}
              {p === 3 && (
                <LetterPage3
                  json={effectiveJson}
                  editMode={editMode}
                  handleApprove={handleApprove}
                  openComment={openComment}
                  onBookmarkClick={onBookmarkClick}
                  onConfidenceChange={onConfidenceChange}
                />
              )}
              {p === 4 && (
                <LetterPage4
                  json={effectiveJson}
                  editMode={editMode}
                  handleApprove={handleApprove}
                  openComment={openComment}
                  onBookmarkClick={onBookmarkClick}
                  onConfidenceChange={onConfidenceChange}
                />
              )}
              {p === 5 && (
                <LetterPage5
                  json={effectiveJson}
                  editMode={editMode}
                  handleApprove={handleApprove}
                  openComment={openComment}
                  onBookmarkClick={onBookmarkClick}
                  onConfidenceChange={onConfidenceChange}
                />
              )}
              {p === 6 && (
                <LetterPage6
                  json={effectiveJson}
                  editMode={editMode}
                  handleApprove={handleApprove}
                  openComment={openComment}
                  onBookmarkClick={onBookmarkClick}
                  onConfidenceChange={onConfidenceChange}
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
