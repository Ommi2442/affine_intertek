/* eslint-disable */
import React, { useEffect, useRef, forwardRef } from "react";
import * as pdfjsLib from "pdfjs-dist";

// Worker for v4
import workerSrc from "pdfjs-dist/build/pdf.worker.min.mjs?url";
pdfjsLib.GlobalWorkerOptions.workerSrc = workerSrc;

import { PDFViewer, EventBus } from "pdfjs-dist/web/pdf_viewer.mjs";
import "pdfjs-dist/web/pdf_viewer.css";

const PdfViewer = forwardRef((props, ref) => {
  const containerRef = useRef(null);
  const viewerRef = useRef(null);
  const pdfRef = useRef(null);

  // ---------------- INIT ----------------
  useEffect(() => {
    const eventBus = new EventBus();

    viewerRef.current = new PDFViewer({
      container: containerRef.current,
      eventBus,
      textLayerMode: 2,
    });
  }, []);

  React.useImperativeHandle(ref, () => ({
    loadPdfFromUrl,
    goToCitation,
  }));

  // ---------------- LOAD PDF (FROM INDEXEDDB URL) ----------------
  async function loadPdfFromUrl(objectUrl) {
    try {
      const loadingTask = pdfjsLib.getDocument({
        url: objectUrl,
      });

      const pdf = await loadingTask.promise;
      pdfRef.current = pdf;
      viewerRef.current.setDocument(pdf);

      setTimeout(() => {
        viewerRef.current.currentPageNumber = 1;
      }, 200);
    } catch (err) {
      console.error("PDF load error:", err);
    }
  }

  // ---------------- NAVIGATION ----------------
  function goToCitation(pageNumber, phrase) {
    const viewer = viewerRef.current;
    if (!viewer || !phrase) return;

    viewer.currentPageNumber = pageNumber;
    const eventBus = viewer.eventBus;

    eventBus.on("textlayerrendered", function handler(e) {
      if (e.pageNumber !== pageNumber) return;
      eventBus.off("textlayerrendered", handler);
      setTimeout(() => highlightPhrase(pageNumber, phrase), 200);
    });
  }

  // ---------------- HIGHLIGHT ----------------
  function highlightPhrase(pageNumber, phrase) {
    const viewer = viewerRef.current;
    const pageView = viewer.getPageView(pageNumber - 1);
    if (!pageView) return;

    const textLayer = pageView.textLayer;
    if (!textLayer) return;

    const textLayerDiv =
      textLayer.textLayerDiv ||
      textLayer.div ||
      pageView.div?.querySelector(".textLayer");

    if (!textLayerDiv) return;

    const spans = textLayerDiv.shadowRoot
      ? Array.from(textLayerDiv.shadowRoot.querySelectorAll("span"))
      : Array.from(textLayerDiv.querySelectorAll("span"));

    const target = phrase.toLowerCase().trim();

    textLayerDiv
      .querySelectorAll(".citation-highlight")
      .forEach((n) => n.remove());

    spans.forEach((span) => {
      if (!span.textContent.toLowerCase().includes(target)) return;

      const rect = span.getBoundingClientRect();
      const containerRect = textLayerDiv.getBoundingClientRect();

      const mark = document.createElement("div");
      mark.className = "citation-highlight";
      mark.style.position = "absolute";
      mark.style.left = `${rect.left - containerRect.left}px`;
      mark.style.top = `${rect.top - containerRect.top}px`;
      mark.style.width = `${rect.width}px`;
      mark.style.height = `${rect.height}px`;
      mark.style.background = "rgba(255,255,0,0.45)";
      mark.style.pointerEvents = "none";
      mark.style.zIndex = 500;

      textLayerDiv.appendChild(mark);
    });
  }

  return (
    <div
      ref={containerRef}
      style={{
        width: "100%",
        height: "100%",
        overflow: "auto",
        position: "absolute",
        top: 0,
        left: 0,
        background: "#f3f3f3",
      }}
    >
      <div className="pdfViewer" />
    </div>
  );
});

export default PdfViewer;
