import React, { useRef, useState, useEffect } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Divider,
} from "@mui/material";
import { generateTrfApi } from "../../redux/api/generateTrfApi";
import "./ReportPage.css";
import { useDispatch } from "react-redux";
import DataTable1 from "../../components/DataTable1";
import { finaliseReportRequest } from "../../redux/features/finaliseReport/finaliseReportSlice";

const ReportPage = () => {
  const [bookmarkOpen, setBookmarkOpen] = useState(false);
  const [bookmarkData, setBookmarkData] = useState(null);
  const [trfJson, setTrfJson] = useState(null);

  const debugShowLeftPanel = true;

  const dispatch = useDispatch();
  const dataTableRef = useRef(null);

// ----------------------------------------------------------
// PROGRESS STATE
// ----------------------------------------------------------
const [status, setStatus] = useState("Indexing in Progress"); // for testing
const [progress, setProgress] = useState(0);
const [refreshing, setRefreshing] = useState(false);

// Correct mapping (use ?? to avoid fallback bugs)
const STAGE_PERCENT = {
  "Pending": 0,
  "Upload Complete": 25,
  "Indexing in Progress": 50,
  "Ready for Report Generation": 75,
  "Generating Report": 90,
  "Completed": 100,
};

// Step definitions (no change)
const STAGES = [
  { label: "Upload", key: "Upload Complete" },
  { label: "Indexing", key: "Indexing in Progress" },
  { label: "TRF Report in Progress", key: "Ready for Report Generation" },
  { label: "Report Generated", key: "Completed" },
];

// ----------------------------------------------------------
// POLLING STATUS FUNCTION — fully fixed
// ----------------------------------------------------------
const checkStatus = async () => {
  try {
    setRefreshing(true);

    const res = await fetch("/api/project/status?id=PRJ_000001");
    const data = await res.json();

    console.log("STATUS RECEIVED:", data?.status);

    if (data?.status) {
      setStatus(data.status);
      setProgress(STAGE_PERCENT[data.status] ?? 0);
    }
  } catch (err) {
    console.error("STATUS CHECK FAILED:", err);
  } finally {
    setRefreshing(false);
  }
};

// ----------------------------------------------------------
// INITIAL AUTO-RUN + 30s POLLING
// ----------------------------------------------------------
useEffect(() => {
  checkStatus(); // first call immediately

  const poll = setInterval(checkStatus, 30000);
  return () => clearInterval(poll);
}, []);

// ----------------------------------------------------------
// DEBUG: REMOVE WHEN CONNECTED TO LIVE BACKEND
// PROGRESS UPDATES IN REAL TIME FOR TESTING
// ----------------------------------------------------------
useEffect(() => {
  setProgress(STAGE_PERCENT[status] ?? 0);
}, [status]);


  // ----------------------------------------------------------
  // BOOKMARK HANDLER
  // ----------------------------------------------------------
  const handleBookmarkFromChild = (data) => {
    setBookmarkData(data);
    setBookmarkOpen(true);
  };

  const handleFinalise = () => {
    if (!dataTableRef.current) return;
    const updatedPayload = dataTableRef.current.getUpdatedJson();
    dispatch(finaliseReportRequest(updatedPayload));
  };

  // ----------------------------------------------------------
  // RENDER LEFT PANEL (Progress or TRF)
  // ----------------------------------------------------------
  const renderLeftPanel = () => {
    if (status !== "Completed" || !trfJson) {
      return (
        <Card className="progress-advanced-card left-card">
          <Typography className="progress-advanced-title">
            Processing TRF Report
          </Typography>

          {/* STEP INDICATORS */}
          <Box className="steps-container">
            {STAGES.map((stage, index) => {
              const reached = progress >= STAGE_PERCENT[stage.key];
              return (
                <Box key={index} className="step-item">
                  <Box className={`step-circle ${reached ? "active" : ""}`}>
                    {reached ? "✔" : index + 1}
                  </Box>
                  <Typography className="step-label">{stage.label}</Typography>

                  {index !== STAGES.length - 1 && (
                    <Box className={`step-line ${reached ? "active" : ""}`} />
                  )}
                </Box>
              );
            })}
          </Box>

          {/* PROGRESS BAR */}
          <Box className="progress-advanced-bar">
            <Box
              className="progress-advanced-fill"
              style={{ width: `${progress}%` }}
            />
          </Box>


          <Typography className="progress-advanced-status">
            {status}
          </Typography>

          <Button
            disabled={refreshing}
            className="refresh-advanced-btn"
            onClick={checkStatus}
          >
            {refreshing ? "Refreshing..." : "Refresh Status"}
          </Button>
        </Card>
      );
    }

    // --------------------- SHOW ORIGINAL LEFT PANEL ---------------------
    return (
      <Card className="left-card">
        <CardContent className="left-content">
          <Box className="report-header">
            <img
              src="/images/trf_image1.jpg"
              className="header-image"
              alt="header"
            />

            <Typography className="header-text">
              Test Report issued under the responsibility of:
            </Typography>
          </Box>

          <Box className="report-title-container">
            <Typography sx={{ fontWeight: 700, fontSize: "20px" }}>
              TEST REPORT
            </Typography>
            <Typography sx={{ fontWeight: 700, fontSize: "20px" }}>
              IEC 61010-1
            </Typography>
            <Typography sx={{ fontWeight: 700, fontSize: "20px" }}>
              Safety requirements for electrical equipment for measurement,
              control, and laboratory use
            </Typography>
            <Typography sx={{ fontWeight: 700, fontSize: "20px" }}>
              Part 1: General requirements
            </Typography>
          </Box>

          <DataTable1
            ref={dataTableRef}
            jsonData={trfJson}
            onBookmarkClick={handleBookmarkFromChild}
          />
        </CardContent>
      </Card>
    );
  };

  // ----------------------------------------------------------
  // FINAL PAGE LAYOUT
  // ----------------------------------------------------------
  return (
    <Box className="report-container">
      {/* LEFT SIDE — Shows progress OR final TRF */}
      <Box className="left-panel">{renderLeftPanel()}</Box>

      {/* RIGHT SIDE — Always visible */}
      {bookmarkOpen ? (
        <Box className="bookmark-panel">
          <Box className="bookmark-header">
            <Typography className="bookmark-title">Citation</Typography>
            <Button size="small" onClick={() => setBookmarkOpen(false)}>
              ✕
            </Button>
          </Box>

          <Typography className="bookmark-field">{bookmarkData?.field}</Typography>
          <Typography className="bookmark-value">{bookmarkData?.value}</Typography>
        </Box>
      ) : (
        <Box className="right-panel">
          {/* ACTION CARD */}
          <Card className="action-card">
            <CardContent>
              <Typography variant="h6" className="action-title">
                Actions
              </Typography>

              <Box className="button-stack">
                {[
                  { text: "Edit / Refine", icon: "/images/edit_icon.svg", bg: "#2C2C2C" },
                  { text: "Finalise", icon: "/images/approve_icon.png", bg: "#396872ff", action: handleFinalise },
                  { text: "Download", icon: "/images/download_icon.png", bg: "#77D5EA" },
                  { text: "Missing Field Re..", icon: "/images/file_icon.png", bg: "#5191a0ff" },
                  { text: "Regenerate", icon: "/images/regenrate_icon.png", bg: "#417581" },
                ].map((btn, i) => (
                  <Button
                    key={i}
                    fullWidth
                    variant="contained"
                    className="action-button"
                    onClick={btn.action}
                    style={{ background: btn.bg }}
                  >
                    <img src={btn.icon} alt="" className="icon-img icon-white" />
                    {btn.text}
                  </Button>
                ))}
              </Box>

              <Typography className="generate-title">Generate</Typography>

              <Box className="generate-row">
                {["CDR", "Letter"].map((label, i) => (
                  <Button
                    key={i}
                    variant="contained"
                    className="generate-btn"
                    style={{ background: "#417581" }}
                  >
                    <img
                      src="/images/approve_icon.png"
                      className="icon-img icon-white"
                      alt=""
                    />
                    {label}
                  </Button>
                ))}
              </Box>
            </CardContent>
          </Card>

          {/* CONFIDENCE CARD */}
          <Card className="confidence-card">
            <CardContent>
              <Typography variant="h6" className="confidence-header">
                Confidence Score
              </Typography>

              <Box className="confidence-summary">
                <Typography>4/6 fields</Typography>
                <Typography fontWeight="bold">67%</Typography>
              </Box>

              <Box className="confidence-bar">
                <Box className="confidence-fill" style={{ width: "67%" }} />
              </Box>

              {[
                { label: "High", count: 4, color: "green" },
                { label: "Medium", count: 1, color: "yellow" },
                { label: "Low", count: 0, color: "red" },
                { label: "User Edited", count: 12, color: "grey" },
              ].map((row, i) => (
                <Box key={i} className="confidence-row">
                  <Box className="confidence-label">
                    <Box style={{ display: "flex", gap: "5px" }}>
                      <span className={`dot ${row.color}`} />
                      <Typography>{row.label}</Typography>
                    </Box>
                    <Typography fontWeight="bold">{row.count}</Typography>
                  </Box>

                  {i < 3 && <Divider />}
                </Box>
              ))}
            </CardContent>
          </Card>
        </Box>
      )}
    </Box>
  );
};

export default ReportPage;
