/* eslint-disable */
import React, { useEffect, useRef, useState, useCallback } from 'react';
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
  DialogContentText,
} from '@mui/material';
import { useNavigate, useNavigationType, useLocation } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import './ReportPage.css';
import CloseIcon from '@mui/icons-material/Close';
//import localLetterJson from '../../utils/letter_output_4.json';
import LetterReport from '../../components/LetterReport/LetterReport';
import ConfidenceScore from './ConfidenceScore';
import { idb_get, idb_set, STORES, idb_clear_all } from '../../utils/idb';
import LetterLoader from '../../components/LetterReport/LetterLoader';
import { truncateWords } from '../../Helpers/truncateWords';
import { normalizeNewLines } from '../../Helpers/normalizeNewLines';
import { DownloadMissingFieldsExcel } from './DownloadMissingFieldsExcel';
import PdfViewer from '../../components/PdfViewer';
import { loadPdfWithCache } from '../../components/loadPdfWithCache';
import { triggerGenerateLetterApi } from '../../redux/api/generateLetterApi';
import { finaliseLetterReportRequest } from '../../redux/features/finaliseLetterReport/finaliseLetterReportSlice';
import { reGenerateLetterClear } from '../../redux/api/RegenerateApi';

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

  const pdfViewerRef = useRef(null);
  const [pdfViewerOpen, setPdfViewerOpen] = useState(false);
  const [headerJson, setHeaderJson] = useState({});

  const [openConfirm, setOpenConfirm] = useState(false);
  const [regenloading, setRegenLoading] = useState(false);
  const [message, setMessage] = useState('');

  const finaliseOnceRef = useRef(false);

  const location = useLocation();

  const { trfBlobUrl, cdrBlobUrl, standard, clientName, product } =
    location.state || {};

  /* ---------------- SAVE EVERY CHANGE ---------------- */
  useEffect(() => {
    if (!dataTableRef.current) return;

    const updated = dataTableRef.current.getUpdatedJson();

    // DO NOT overwrite valid IDB with empty
    if (
      !updated ||
      !Array.isArray(updated?.Tables) ||
      updated.Tables.length === 0 ||
      !headerJson ||
      Object.keys(headerJson).length === 0
    ) {
      return;
    }

    const payload = {
      Letter_header_json: updated,
      Letter_json_body: headerJson,
    };

    idb_set(storageKey, payload, STORES.LETTER);
    setLiveLetterData(updated);
  }, [confidenceTick, headerJson]);

  const autoFinaliseLetter = async () => {
    if (!dataTableRef.current) return;
    if (!headerJson || Object.keys(headerJson).length === 0) return;

    const payload = dataTableRef.current.getUpdatedJson();
    if (!payload) return;

    const letter_payload = {
      Letter_header_json: payload,
      Letter_json_body: headerJson,
    };

    // Persist first (same as manual finalize)
    await idb_set(storageKey, letter_payload, STORES.LETTER);

    dispatch(
      finaliseLetterReportRequest({
        projectId,
        data: letter_payload,
      })
    );

    setFinalised(true);
  };

  useEffect(() => {
    if (
      loading === false &&
      letterJson &&
      headerJson &&
      dataTableRef.current &&
      !finaliseOnceRef.current
    ) {
      finaliseOnceRef.current = true;
      if (message === 'Letter Generated Successfully') {
        autoFinaliseLetter();
      }
    }
  }, [loading, letterJson, headerJson]);

  const loadLetter = useCallback(async () => {
    if (!projectId) return;

    setLoading(true);

    //  Always try IndexedDB first
    const cached = await idb_get(storageKey, STORES.LETTER);
    if (cached) {
      setLetterJson(cached.Letter_header_json);
      setHeaderJson(cached.Letter_json_body);
      setLoading(false);
      return;
    }

    //  Hard refresh + no cache → do nothing yet
    if (isHardRefresh) {
      console.warn('Hard refresh but no LETTER cache found → holding state');
      setLoading(false);
      return;
    }

    console.log('Calling backend to generate Letter...');
    let res;

    // Case 1: blobs were passed from Upload page
    if (trfBlobUrl || cdrBlobUrl) {
      res = await triggerGenerateLetterApi(projectId, trfBlobUrl, cdrBlobUrl);
    }
    // Case 2: blobs NOT available
    else {
      res = await triggerGenerateLetterApi(projectId);
    }

    if (res) {
      setMessage(res?.Message);
      const payload = {
        Letter_header_json: res?.Data?.Letter_header_json,
        Letter_json_body: res?.Data?.Letter_json_body,
      };

      await idb_set(storageKey, payload, STORES.LETTER);
      setLetterJson(payload.Letter_header_json);
      setHeaderJson(payload.Letter_json_body);
    }

    setLoading(false);
  }, [projectId, isHardRefresh, trfBlobUrl, cdrBlobUrl, storageKey]);

  /* ---------------- LOAD LOGIC ---------------- */
  useEffect(() => {
    loadLetter();
  }, [loadLetter]);

  const handleCitationLinkClick = (filename, page, text, blob_url) => {
    // ---- XLSX and DOCX → DOWNLOAD ----
    if (
      filename?.toLowerCase().endsWith('.xlsx') ||
      filename?.toLowerCase().endsWith('.docx')
    ) {
      if (!blob_url) {
        console.error('Missing blob_url for:', filename);
        return;
      }

      const cleanUrl = blob_url.startsWith('/') ? blob_url.slice(1) : blob_url;

      const link = document.createElement('a');
      link.href = cleanUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      return;
    }

    // ---- PDF → INDEXEDDB → VIEWER ----
    setPdfViewerOpen(true);

    setTimeout(async () => {
      if (!pdfViewerRef.current) return;

      await loadPdfWithCache(projectId, filename, blob_url, pdfViewerRef);

      setTimeout(() => {
        pdfViewerRef.current.goToCitation(page, text);
      }, 1200);
    }, 200);
  };

  /* ---------------- ACTIONS ---------------- */
  const handleFinalise = async () => {
    if (!dataTableRef.current) return;

    const payload = dataTableRef.current.getUpdatedJson();

    if (!payload) return;

    // Persist to IndexedDB
    const letter_payload = {
      Letter_header_json: payload,
      Letter_json_body: headerJson,
    };

    await idb_set(storageKey, letter_payload, STORES.LETTER);

    setLetterJson(payload);
    setFinalised(true);
    setEditMode(false);

    dispatch(
      finaliseLetterReportRequest({
        projectId,
        data: letter_payload,
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

  const handleConfirmRegenerate = async () => {
    try {
      setRegenLoading(true);

      const payload = {
        projectId,
      };

      await reGenerateLetterClear(payload);

      setRegenLoading(false);
      setOpenConfirm(false);
      idb_clear_all();

      navigate('/create-project-letter');
      // , {
      // state: {
      //   standard: row?.Standard,
      //   projectId,
      //   clientName: row?.Client_Name,
      //   product: row?.Product,
      //   source: type,
      //   letterPercentage: row?.letter_percentage ?? 0,
      // },
      // });
    } finally {
      // setRegenLoading(false);
      // setOpenConfirm(false);
      // idb_clear_all();
      // await loadLetter();
    }
  };

  const getCitationDialogText = () => {
    if (!selectedCitation) return '';
    return normalizeNewLines(selectedCitation.preview_text || '');
  };
  console.log('letterLoading', loading);

  /* ---------------- UI ---------------- */
  return (
    <Box>
      {/* Header same as CDR */}
      <Box className="report-title-container">
        <Typography sx={{ fontWeight: 700, fontSize: 20 }}>
          LETTER REPORT
        </Typography>
      </Box>

      <Box className="report-container">
        {/* ---------------- LEFT PANEL ---------------- */}
        <Box className="left-panel-letter">
          {loading && <LetterLoader />}

          {!loading && letterJson && (
            <>
              <LetterReport
                ref={dataTableRef}
                jsonData={letterJson}
                editMode={editMode}
                projectId={projectId}
                onConfidenceChange={() => setConfidenceTick((v) => v + 1)}
                onBookmarkClick={handleBookmarkFromChild}
                isHardRefresh={isHardRefresh}
                onPageChange={(p) => setCurrentPage(p)}
              />

              {/* -------- PAGINATION BAR -------- */}
              <Box className="letter-pagination">
                <Button
                  size="small"
                  disabled={currentPage === 1}
                  onClick={() => {
                    const prev = Math.max(1, currentPage - 1);
                    setCurrentPage(prev);
                    dataTableRef.current?.scrollToPage(prev);
                  }}
                >
                  ‹
                </Button>

                {Array.from({ length: 6 }).map((_, i) => {
                  const page = i + 1;
                  const isActive = page === currentPage;

                  return (
                    <Button
                      key={page}
                      size="small"
                      onClick={() => {
                        setCurrentPage(page);
                        dataTableRef.current?.scrollToPage(page);
                      }}
                      sx={{
                        minWidth: 36,
                        mx: 0.5,
                        fontWeight: isActive ? 700 : 400,
                        backgroundColor: isActive ? '#000' : 'transparent',
                        color: isActive ? '#fff' : '#000',
                        '&:hover': {
                          backgroundColor: isActive ? '#000' : '#eee',
                        },
                      }}
                    >
                      {page}
                    </Button>
                  );
                })}

                <Button
                  size="small"
                  disabled={currentPage === 6}
                  onClick={() => {
                    const next = Math.min(6, currentPage + 1);
                    setCurrentPage(next);
                    dataTableRef.current?.scrollToPage(next);
                  }}
                >
                  ›
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
              const rawText = item?.preview_text || '';
              const cleanedText = normalizeNewLines(rawText);
              const isTruncated = cleanedText.split(/\s+/).length > 20;
              const truncatedText = truncateWords(cleanedText, 20);

              return (
                <Card key={idx} sx={{ mb: 2, mr: 3 }}>
                  <CardContent>
                    {/* Truncated text */}
                    <Typography sx={{ whiteSpace: 'pre-wrap', fontSize: 14 }}>
                      {truncatedText}
                      {isTruncated && (
                        <Typography
                          component="span"
                          sx={{
                            ml: 0.5,
                            color: '#0077cc',
                            cursor: 'pointer',
                            fontWeight: 500,
                          }}
                          onClick={() => {
                            setSelectedCitation(item);
                            setOpenCitationDialog(true);
                          }}
                        >
                          ...more
                        </Typography>
                      )}
                    </Typography>

                    {/* ---------- LETTER LINK ---------- */}
                    {item?.filename && (
                      <Typography
                        sx={{
                          fontSize: 13,
                          mt: 1,
                          color: '#1976d2',
                          cursor: 'pointer',
                          textDecoration: 'underline',
                          wordBreak: 'break-word',
                        }}
                        onClick={() =>
                          handleCitationLinkClick(
                            item.filename,
                            item.page,
                            item.preview_text || '',
                            item.url
                          )
                        }
                      >
                        {item.filename}
                        {item.filename.toLowerCase().endsWith('.xlsx') &&
                        item.sheet
                          ? ` (Sheet: ${item.sheet})`
                          : item.filename.toLowerCase().endsWith('.docx') &&
                              item.table
                            ? ` (Table: ${item.table})`
                            : item.page
                              ? ` (${item.page})`
                              : ''}
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
                        handleMissingField(letterJson, projectId, 'letter'),
                    },
                    {
                      text: 'Regenerate',
                      bg: '#417581',
                      icon: '/images/regenrate_icon.png',
                      action: () => setOpenConfirm(true),
                    },
                  ].map((btn, i) => (
                    <Button
                      key={i}
                      fullWidth
                      variant="contained"
                      className="action-button"
                      onClick={btn.action}
                      style={{
                        background: !letterJson ? '#A9A9A9' : btn.bg,
                        cursor: !letterJson ? 'not-allowed' : 'pointer',
                        opacity: !letterJson ? 0.7 : 1,
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

            {(liveLetterData?.Letter_header_json || letterJson) && (
              <ConfidenceScore
                data={liveLetterData?.Letter_header_json || letterJson}
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

              {selectedCitation?.filename && (
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
                      getCitationDialogText(),
                      selectedCitation.url
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
      {/* PDF VIEWER POPUP MODAL */}
      {pdfViewerOpen && (
        <Box
          sx={{
            position: 'fixed',
            top: 0,
            left: 0,
            width: '100vw',
            height: '100vh',
            background: 'rgba(0,0,0,0.65)',
            zIndex: 2000,
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            backdropFilter: 'blur(3px)',
          }}
        >
          <Box
            sx={{
              width: '90%',
              height: '90%',
              background: '#fff',
              borderRadius: '8px',
              overflow: 'hidden',
              position: 'relative',
              boxShadow: '0px 5px 20px rgba(0,0,0,0.3)',
            }}
          >
            <Button
              onClick={() => setPdfViewerOpen(false)}
              sx={{
                position: 'absolute',
                top: 10,
                right: 10,
                zIndex: 2100,
                background: 'rgba(0,0,0,0.6)',
                color: '#fff',
                '&:hover': { background: 'rgba(0,0,0,0.8)' },
              }}
            >
              Close
            </Button>

            <PdfViewer ref={pdfViewerRef} />
          </Box>
        </Box>
      )}
      <Dialog
        open={openConfirm}
        onClose={() => setOpenConfirm(false)}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle>Confirm Regeneration</DialogTitle>

        <DialogContent>
          <DialogContentText>
            This action will delete the existing letter report files and
            regenerate the project. Are you sure you want to continue?
          </DialogContentText>
        </DialogContent>

        <DialogActions>
          <Button
            onClick={() => setOpenConfirm(false)}
            color="inherit"
            disabled={regenloading}
          >
            Cancel
          </Button>

          <Button
            onClick={handleConfirmRegenerate}
            variant="contained"
            color="primary"
            sx={{
              backgroundColor: 'rgb(65, 117, 129)',
              '&:hover': {
                backgroundColor: 'rgb(55, 100, 110)',
              },
            }}
            disabled={regenloading}
          >
            {regenloading ? 'Processing...' : 'Proceed'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default LetterReportPage;
