/* eslint-disable */
import React, { useEffect, useRef, useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Dialog,
  DialogTitle,
  IconButton,
  DialogContent,
  DialogActions,
} from '@mui/material';
import { useNavigate, useNavigationType } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import './ReportPage.css';
import CloseIcon from '@mui/icons-material/Close';
import localLetterJson from '../../utils/letter_output_4.json';
import LetterReport from '../../components/LetterReport/LetterReport';
import ConfidenceScore from './ConfidenceScore';

import { finaliseReportRequest } from '../../redux/features/finaliseReport/finaliseReportSlice';
import { idb_get, idb_set, STORES } from '../../utils/idb';
import LetterLoader from '../../components/LetterReport/LetterLoader';
import { truncateWords } from '../../Helpers/truncateWords';
import { normalizeNewLines } from '../../Helpers/normalizeNewLines';
import { DownloadMissingFieldsExcel } from './DownloadMissingFieldsExcel';

const STORAGE_KEY_PREFIX = 'letter_report_';

const LetterReportPage = () => {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const dataTableRef = useRef(null);

  const projectId = localStorage.getItem('projectId');
  const storageKey = `${STORAGE_KEY_PREFIX}${projectId}`;

  /* ---------------- STATE ---------------- */
  const [letterJson, setLetterJson] = useState(null);
  const [loading, setLoading] = useState(true);

  const [editMode, setEditMode] = useState(false);
  const [finalised, setFinalised] = useState(false);
  const [confidenceTick, setConfidenceTick] = useState(0);
  const [liveLetterData, setLiveLetterData] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);

  const navigationType = useNavigationType();
  const isHardRefresh = navigationType === 'POP';
  const [bookmarkOpen, setBookmarkOpen] = useState(false);
  const [bookmarkData, setBookmarkData] = useState(null);

  const [openCitationDialog, setOpenCitationDialog] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState(null);

  /* ---------------- SAVE EVERY CHANGE ---------------- */
  useEffect(() => {
    if (!dataTableRef.current) return;
    const updated = dataTableRef.current.getUpdatedJson();
    if (!updated) return;

    idb_set(storageKey, updated, STORES.LETTER);
    setLiveLetterData(updated);
  }, [confidenceTick]);

  /* ---------------- LOAD LOGIC ---------------- */
  useEffect(() => {
    if (!projectId) return;

    const load = async () => {
      setLoading(true);

      // 1️⃣ IndexedDB first
      const cached = await idb_get(storageKey, STORES.LETTER);
      if (cached) {
        setLetterJson(cached);
        setLoading(false);
        return;
      }

      // 2️⃣ Backend (for now local JSON)
      if (!isHardRefresh) {
        setLetterJson(localLetterJson);
        await idb_set(storageKey, localLetterJson, STORES.LETTER);
      }

      setLoading(false);
    };

    load();
  }, [projectId, isHardRefresh]);

  /* ---------------- ACTIONS ---------------- */
  const handleFinalise = async () => {
    if (!dataTableRef.current) return;

    const payload = dataTableRef.current.getUpdatedJson();
    await idb_set(storageKey, payload, STORES.LETTER);

    setLetterJson(payload);
    setFinalised(true);
    setEditMode(false);

    dispatch(
      finaliseReportRequest({
        projectId,
        reportType: 'letter',
        data: payload,
      })
    );
  };

  const handleBookmarkFromChild = (data) => {
    if (!data) return;

    setBookmarkData({
      ...data,
      textSupportRaw: Array.isArray(data.text_support) ? data.text_support : [],
    });

    setBookmarkOpen(true);
  };

  const handleDownload = () => {
    const BASE_URL = import.meta.env.VITE_BACKEND_URL;
    window.open(
      `${BASE_URL}/projects/download-file?project_id=${projectId}&report_type=letter`
    );
  };

  const handleMissingField = (data, projectID, reportClick) => {
    DownloadMissingFieldsExcel(data, projectID, reportClick);
  };

  const handleRegenerate = () => navigate('/create-project');

  /* ---------------- UI ---------------- */
  return (
    <Box>
      {/* 🔷 Header same as CDR */}
      <Box className="report-title-container">
        <Typography sx={{ fontWeight: 700, fontSize: 20 }}>
          LETTER REPORT
        </Typography>
      </Box>

      <Box className="report-container">
        {/* ---------------- LEFT PANEL ---------------- */}
        <Box className="left-panel">
          {loading && <LetterLoader />}

          {!loading && localLetterJson && (
            <>
              {/* 1️⃣ White scrollable letter */}
              <Box className="letter-white-box">
                <LetterReport
                  ref={dataTableRef}
                  jsonData={localLetterJson}
                  editMode={editMode}
                  onPageChange={(p) => setCurrentPage(p)}
                  onConfidenceChange={() => setConfidenceTick((v) => v + 1)}
                  onBookmarkClick={handleBookmarkFromChild}
                />
              </Box>

              {/* 2️⃣ Bottom pagination bar */}
              <Box className="letter-page-nav">
                {/* ◀ PREVIOUS */}
                <Button
                  className="letter-page-btn nav-btn"
                  disabled={currentPage === 1}
                  onClick={() => {
                    const p = Math.max(1, currentPage - 1);
                    setCurrentPage(p);
                    dataTableRef.current?.scrollToPage(p);
                  }}
                >
                  &lt;
                </Button>

                {/* PAGE NUMBERS */}
                {[1, 2, 3, 4, 5, 6].map((p) => (
                  <Button
                    key={p}
                    onClick={() => {
                      setCurrentPage(p);
                      dataTableRef.current?.scrollToPage(p);
                    }}
                    className={`letter-page-btn ${
                      currentPage === p ? 'active' : ''
                    }`}
                  >
                    {p}
                  </Button>
                ))}

                {/* ▶ NEXT */}
                <Button
                  className="letter-page-btn nav-btn"
                  disabled={currentPage === 6}
                  onClick={() => {
                    const p = Math.min(6, currentPage + 1);
                    setCurrentPage(p);
                    dataTableRef.current?.scrollToPage(p);
                  }}
                >
                  &gt;
                </Button>
              </Box>
            </>
          )}
        </Box>

        {/* ---------------- RIGHT PANEL ---------------- */}
        {bookmarkOpen ? (
          <Box className="right-panel bookmark-panel">
            <Box className="bookmark-header">
              <Typography />
              <Button size="small" onClick={() => setBookmarkOpen(false)}>
                ✕
              </Button>
            </Box>

            {bookmarkData?.textSupportRaw?.map((item, idx) => {
              const rawText = item?.text || '';
              const truncated = truncateWords(normalizeNewLines(rawText), 20);

              return (
                <Card key={idx} sx={{ mb: 2 }}>
                  <CardContent>
                    <Typography sx={{ whiteSpace: 'pre-wrap', fontSize: 14 }}>
                      {truncated}
                    </Typography>

                    {item?.filename && (
                      <Typography
                        sx={{
                          fontSize: 13,
                          mt: 1,
                          color: '#1976d2',
                          cursor: 'pointer',
                          textDecoration: 'underline',
                        }}
                        onClick={() => window.open(item.url, '_blank')}
                      >
                        {item.filename} (Page {item.page})
                      </Typography>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </Box>
        ) : (
          <Box className="right-panel">
            <Card className="action-card">
              <CardContent>
                <Typography variant="h6" className="action-title">
                  Actions
                </Typography>

                <Box className="button-stack">
                  {[
                    {
                      text: 'Edit / Refine',
                      icon: '/images/edit_icon.svg',
                      bg: '#2C2C2C',
                      action: () => {
                        setEditMode(true);
                        setFinalised(false);
                      },
                    },
                    {
                      text: 'Finalize',
                      bg: '#396872ff',
                      icon: '/images/approve_icon.png',
                      action: handleFinalise,
                    },
                    {
                      text: 'Download',
                      bg: '#77D5EA',
                      icon: '/images/download_icon.png',
                      action: handleDownload,
                    },
                    {
                      text: 'Missing Field Re..',
                      icon: '/images/file_icon.png',
                      bg: '#5191a0ff',
                      action: () =>
                        handleMissingField(
                          localLetterJson,
                          projectId,
                          'letter'
                        ),
                    },
                    {
                      text: 'Regenerate',
                      bg: '#417581',
                      icon: '/images/regenrate_icon.png',
                      action: handleRegenerate,
                    },
                  ].map((btn, i) => (
                    <Button
                      key={i}
                      fullWidth
                      variant="contained"
                      className="action-button"
                      onClick={btn.action}
                      style={{
                        background: !localLetterJson ? '#A9A9A9' : btn.bg,
                        cursor: !localLetterJson ? 'not-allowed' : 'pointer',
                        opacity: !localLetterJson ? 0.7 : 1,
                      }}
                    >
                      {btn.text === 'Finalize' && (
                        <span
                          className={`finalize-status-dot ${
                            finalised ? 'green' : editMode ? 'red' : 'green'
                          }`}
                        />
                      )}
                      <img
                        src={btn.icon}
                        alt=""
                        className={`icon-img icon-white`}
                      />
                      {btn.text}
                    </Button>
                  ))}
                </Box>
              </CardContent>
            </Card>

            {localLetterJson && (
              <ConfidenceScore
                data={localLetterJson}
                reportType="letter"
                confidenceTick={confidenceTick}
                projectId={projectId}
              />
            )}
          </Box>
        )}
      </Box>
      <Dialog
        open={openCitationDialog}
        onClose={() => setOpenCitationDialog(false)}
        maxWidth="md"
        fullWidth
      >
        {/* ---------- Header with Close Icon ---------- */}
        <DialogTitle
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            pr: 1,
          }}
        >
          Citation Details
          <IconButton
            onClick={() => setOpenCitationDialog(false)}
            sx={{
              color: '#000',
            }}
          >
            <CloseIcon />
          </IconButton>
        </DialogTitle>

        {/* ---------- Content ---------- */}
        <DialogContent
          dividers
          sx={{
            overflowX: 'hidden',
          }}
        >
          {selectedCitation && (
            <>
              <Typography
                sx={{
                  fontSize: 14,
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  overflowWrap: 'anywhere',
                  mb: 2,
                }}
              >
                {getCitationDialogText()}
                {/* {normalizeNewLines(selectedCitation.text)} */}
              </Typography>

              {reportClick === 'letter' && selectedCitation?.filename && (
                <Typography
                  sx={{
                    fontSize: 13,
                    fontWeight: 500,
                    color: '#1976d2',
                    cursor: 'pointer',
                    textDecoration: 'underline',
                  }}
                  onClick={() =>
                    handleCitationLinkClick(
                      item?.filename,
                      selectedCitation.page + 1,
                      selectedCitation.preview_text,
                      selectedCitation.url
                    )
                  }
                >
                  {selectedCitation.filename} (Page {selectedCitation.page + 1})
                </Typography>
              )}

              {reportClick === 'letter' && selectedCitation?.filename && (
                <Typography
                  sx={{
                    fontSize: 13,
                    fontWeight: 500,
                    color: '#1976d2',
                    cursor: 'pointer',
                    textDecoration: 'underline',
                  }}
                  onClick={() =>
                    handleCitationLinkClick(
                      selectedCitation.filename,
                      selectedCitation.page,
                      getCitationDialogText()
                    )
                  }
                >
                  {selectedCitation.filename} (Page {selectedCitation.page})
                </Typography>
              )}
            </>
          )}
        </DialogContent>

        {/* ---------- Footer with Black Button ---------- */}
        <DialogActions sx={{ p: 2 }}>
          <Button
            variant="contained"
            onClick={() => setOpenCitationDialog(false)}
            sx={{
              backgroundColor: '#000',
              color: '#fff',
              textTransform: 'none',
              '&:hover': {
                backgroundColor: '#000',
              },
            }}
          >
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default LetterReportPage;
