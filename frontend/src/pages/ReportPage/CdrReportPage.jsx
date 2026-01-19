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
//import localCDRJson from '../../utils/iec_output_cdr_PRJ_0000011.json';
import CdrReport from '../../components/CdrReport/CdrReport';
import CdrLoader from '../../components/CdrReport/CdrLoader';
import ConfidenceScore from './ConfidenceScore';
import CloseIcon from '@mui/icons-material/Close';

import { triggerGenerateCdrApi } from '../../redux/api/generateCdrApi';
import { finaliseReportRequest } from '../../redux/features/finaliseReport/finaliseReportSlice';
import { DownloadMissingFieldsExcel } from './DownloadMissingFieldsExcel';

import { idb_get, idb_set, STORES } from '../../utils/idb';

import { truncateWords } from '../../Helpers/truncateWords';
import { normalizeNewLines } from '../../Helpers/normalizeNewLines';
import { RenderImageThumbnails } from '../../Helpers/renderImageThumbnails';

const STORAGE_KEY_PREFIX = 'cdr_report_';

const CdrReportPage = () => {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const dataTableRef = useRef(null);

  const projectId = localStorage.getItem('projectId');
  const storageKey = `${STORAGE_KEY_PREFIX}${projectId}`;

  /* ---------------- STATE ---------------- */
  const [cdrJson, setCdrJson] = useState(null);
  const [loading, setLoading] = useState(true);

  const [editMode, setEditMode] = useState(false);
  const [finalised, setFinalised] = useState(false);
  const [confidenceTick, setConfidenceTick] = useState(0);

  const [bookmarkOpen, setBookmarkOpen] = useState(false);
  const [bookmarkData, setBookmarkData] = useState(null);

  const [openCitationDialog, setOpenCitationDialog] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState(null);
  const [liveCdrData, setLiveCdrData] = useState(null);

  const navigationType = useNavigationType();
  const isHardRefresh = navigationType === 'POP';

  /* ---------------- SAVE EVERY APPROVE ---------------- */
  useEffect(() => {
    if (!dataTableRef.current) return;
    const updated = dataTableRef.current.getUpdatedJson();
    if (!updated) return;

    idb_set(storageKey, updated, STORES.CDR);
    //setCdrJson(updated);
    setLiveCdrData(updated);
  }, [confidenceTick]);

  /* ---------------- LOAD LOGIC ---------------- */
  useEffect(() => {
    if (!projectId) return;

    const load = async () => {
      setLoading(true);

      // Always try IndexedDB first
      const cached = await idb_get(storageKey, STORES.CDR);
      if (cached) {
        setCdrJson(cached);
        setLoading(false);
        return;
      }

      //  HARD REFRESH + no cache → do NOT wipe UI or call backend yet
      if (isHardRefresh) {
        console.warn('Hard refresh but no CDR cache found → holding state');
        setLoading(false);
        return;
      }

      // Only call backend if this is NOT a refresh
      if (!isHardRefresh) {
        const res = await triggerGenerateCdrApi(projectId);
        if (res?.data) {
          await idb_set(storageKey, res.data, STORES.CDR); // overwrite
          setCdrJson(res.data); // render only backend data
        }
      }

      setLoading(false);
    };

    load();
  }, [projectId, isHardRefresh]);

  /* ---------------- ACTIONS ---------------- */
  const handleFinalise = async () => {
    if (!dataTableRef.current) return;

    const payload = dataTableRef.current.getUpdatedJson();
    if (!payload) return;

    //  THIS IS MISSING TODAY
    await idb_set(storageKey, payload, STORES.CDR);

    setCdrJson(payload); // local UI
    setFinalised(true);
    setEditMode(false);

    dispatch(
      finaliseReportRequest({
        projectId,
        reportType: 'cdr',
        data: payload,
      })
    );
  };

  const handleDownload = () => {
    const BASE_URL = import.meta.env.VITE_BACKEND_URL;
    //http://127.0.0.1:8000/projects/download-file?project_id=PRJ_0000011&report_type=cdr
    window.open(
      `${BASE_URL}/projects/download-file?project_id=${projectId}&report_type=cdr`
    );
  };

  const handleRegenerate = () => navigate('/create-project');
  const handleGenerateLetter = () => {
    finalised && navigate('/create-project-letter');
  };

  /* ---------------- BOOKMARK ---------------- */
  const handleBookmarkFromChild = (data) => {
    if (!data) return;

    setBookmarkData({
      ...data,
      textSupportRaw: Array.isArray(data.text_support) ? data.text_support : [],
    });

    setBookmarkOpen(true);
  };

  const handleMissingField = (data, projectID, reportClick) => {
    DownloadMissingFieldsExcel(data, projectID, reportClick);
  };

  /* ---------------- UI ---------------- */
  return (
    <Box>
      <Box className="report-title-container">
        <Typography sx={{ fontWeight: 700, fontSize: 20 }}>
          CDR REPORT
        </Typography>
      </Box>

      <Box className="report-container">
        {/* LEFT PANEL */}
        <Box className="left-panel">
          {loading && <CdrLoader />}

          {!loading && cdrJson && (
            <CdrReport
              ref={dataTableRef}
              jsonData={cdrJson}
              editMode={editMode}
              projectId={projectId}
              cdrFinalised={finalised}
              onBookmarkClick={handleBookmarkFromChild}
              onConfidenceChange={() => setConfidenceTick((v) => v + 1)}
              isHardRefresh={isHardRefresh}
            />
          )}
        </Box>

        {/* RIGHT PANEL */}
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
                      icon: '/images/approve_icon.png',
                      bg: '#396872ff',
                      action: handleFinalise,
                    },
                    {
                      text: 'Download',
                      icon: '/images/download_icon.png',
                      bg: '#77D5EA',
                      action: handleDownload,
                    },
                    {
                      text: 'Missing Field Re..',
                      icon: '/images/file_icon.png',
                      bg: '#5191a0ff',
                      action: () =>
                        handleMissingField(cdrJson, projectId, 'cdr'),
                    },
                    {
                      text: 'Regenerate',
                      icon: '/images/regenrate_icon.png',
                      bg: '#417581',
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
                        background: !cdrJson ? '#A9A9A9' : btn.bg, // grey out
                        cursor: !cdrJson ? 'not-allowed' : 'pointer',
                        opacity: !cdrJson ? 0.7 : 1,
                      }}
                    >
                      {/* STATUS DOT (only for Finalize) */}
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

                <Typography className="generate-title">Generate</Typography>

                <Box className="generate-row">
                  <Button
                    variant="contained"
                    className="generate-btn"
                    style={{
                      background: finalised ? '#417581' : '#A9A9A9',
                    }}
                    onClick={handleGenerateLetter}
                  >
                    Letter
                  </Button>
                </Box>
              </CardContent>
            </Card>

            {(liveCdrData || cdrJson) && (
              <ConfidenceScore
                data={liveCdrData || cdrJson}
                reportType="cdr"
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

              {reportClick === 'trf' && selectedCitation?.filename && (
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

              {reportClick === 'cdr' && selectedCitation?.filename && (
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

export default CdrReportPage;
