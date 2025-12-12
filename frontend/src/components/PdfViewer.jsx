/* eslint-disable */
import React, { useEffect, useRef, forwardRef } from "react";
import * as pdfjsLib from "pdfjs-dist";

// Correct worker path for pdfjs-dist v4
import workerSrc from "pdfjs-dist/build/pdf.worker.min.mjs?url";
pdfjsLib.GlobalWorkerOptions.workerSrc = workerSrc;

// Correct viewer imports for v4
import { PDFViewer, EventBus } from "pdfjs-dist/web/pdf_viewer.mjs";

import "pdfjs-dist/web/pdf_viewer.css";

const PdfViewer = forwardRef((props, ref) => {
  const containerRef = useRef(null);
  const viewerRef = useRef(null);
  const pdfRef = useRef(null);

  // Initialize Viewer
  useEffect(() => {
    const eventBus = new EventBus();

    viewerRef.current = new PDFViewer({
      container: containerRef.current,
      eventBus,
      textLayerMode: 2, // ensure text layer renders
    });
  }, []);

  React.useImperativeHandle(ref, () => ({
    loadPdf,
    goToCitation,
  }));

  // Load PDF
  async function loadPdf(url) {
    try {
      const loadingTask = pdfjsLib.getDocument({ url });
      const pdf = await loadingTask.promise;

      pdfRef.current = pdf;

      viewerRef.current.setDocument(pdf);

      setTimeout(() => {
        viewerRef.current.currentPageNumber = 1;
      }, 300);
    } catch (error) {
      console.error("PDF load error:", error);
    }
  }

  // Navigate + Highlight
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

function highlightPhrase(pageNumber, phrase) {
  const viewer = viewerRef.current;
  const pageView = viewer.getPageView(pageNumber - 1);
  if (!pageView) return;

  // Detect text layer div (pdfjs v4 uses shadow DOM sometimes)
  const textLayer = pageView.textLayer;
  if (!textLayer) {
    console.warn("TextLayer not found");
    return;
  }

  // Accurate textLayerDiv
  const textLayerDiv =
    textLayer.textLayerDiv || // v3
    textLayer.div || // older fallback
    (pageView.div ? pageView.div.querySelector(".textLayer") : null); // v4 DOM

  if (!textLayerDiv) {
    console.warn("No textLayerDiv found");
    return;
  }

  // FIX FOR PDF.JS v4 → spans are in shadow DOM
  let spans = [];
  if (textLayerDiv.shadowRoot) {
    spans = Array.from(textLayerDiv.shadowRoot.querySelectorAll("span"));
  } else {
    spans = Array.from(textLayerDiv.querySelectorAll("span"));
  }

  if (!spans.length) {
    console.warn("No spans found for highlight");
    return;
  }

  // Normalize search text
  const target = phrase.toLowerCase().trim();

  // Clear old highlights
  textLayerDiv.querySelectorAll(".citation-highlight").forEach((n) => n.remove());

  spans.forEach((span) => {
    const text = span.textContent.toLowerCase();
    if (!text.includes(target)) return;

    const rect = span.getBoundingClientRect();
    const containerRect = textLayerDiv.getBoundingClientRect();

    const mark = document.createElement("div");
    mark.className = "citation-highlight";
    mark.style.position = "absolute";
    mark.style.left = `${rect.left - containerRect.left}px`;
    mark.style.top = `${rect.top - containerRect.top}px`;
    mark.style.width = `${rect.width}px`;
    mark.style.height = `${rect.height}px`;
    mark.style.background = "rgba(255, 255, 0, 0.45)";
    mark.style.pointerEvents = "none";
    mark.style.zIndex = 500;

    textLayerDiv.appendChild(mark);
  });

  console.log("Highlight applied");
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
