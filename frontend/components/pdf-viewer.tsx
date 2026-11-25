"use client";

import clsx from "clsx";
import {
  ChevronLeft,
  ChevronRight,
  Copy,
  Download,
  EyeOff,
  Eye,
  Maximize,
  Minimize,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

interface PdfViewerProps {
  open: boolean;
  onClose: () => void;
  imageUrl: string;
  pdfName: string;
  pageNumber: number;
  totalPages: number;
}

const DEFAULT_SCALE = 1;
const MIN_SCALE = 0.25;
const MAX_SCALE = 4;
const ZOOM_STEP = 0.25;

export function PdfViewer({
  open,
  onClose,
  imageUrl,
  pdfName,
  pageNumber,
  totalPages,
}: PdfViewerProps) {
  const [scale, setScale] = useState(DEFAULT_SCALE);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [lastPos, setLastPos] = useState({ x: 0, y: 0 });
  const imgRef = useRef<HTMLImageElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [fullscreen, setFullscreen] = useState(false);

  const containerWidth = useMemo(() => {
    if (!containerRef.current) return 0;
    return containerRef.current.clientWidth;
  }, [containerRef.current, fullscreen]);

  const containerHeight = useMemo(() => {
    if (!containerRef.current) return 0;
    return containerRef.current.clientHeight;
  }, [containerRef.current, fullscreen]);

  // Reset offset when scale or image changes
  useEffect(() => {
    setOffset({ x: 0, y: 0 });
  }, [scale, imageUrl, fullscreen]);

  const zoomIn = useCallback(() => {
    setScale((s) => Math.min(s + ZOOM_STEP, MAX_SCALE));
  }, []);

  const zoomOut = useCallback(() => {
    setScale((s) => Math.max(s - ZOOM_STEP, MIN_SCALE));
  }, []);

  const fitToWidth = useCallback(() => {
    if (!imgRef.current || !containerRef.current) return;
    const img = imgRef.current;
    const naturalW = img.naturalWidth || img.width;
    const newScale = containerRef.current.clientWidth / naturalW;
    setScale(Math.min(Math.max(newScale, MIN_SCALE), MAX_SCALE));
    setOffset({ x: 0, y: 0 });
  }, [containerRef.current]);

  const fitToPage = useCallback(() => {
    if (!imgRef.current || !containerRef.current) return;
    const img = imgRef.current;
    const naturalW = img.naturalWidth || img.width;
    const naturalH = img.naturalHeight || img.height;
    const scaleW = containerRef.current.clientWidth / naturalW;
    const scaleH = containerRef.current.clientHeight / naturalH;
    const newScale = Math.min(scaleW, scaleH, MAX_SCALE);
    setScale(Math.max(newScale, MIN_SCALE));
    setOffset({ x: 0, y: 0 });
  }, [containerRef.current]);

  const handleMouseDown = (e: React.MouseEvent) => {
    if (scale <= DEFAULT_SCALE) return;
    setIsDragging(true);
    setLastPos({ x: e.clientX, y: e.clientY });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    const dx = e.clientX - lastPos.x;
    const dy = e.clientY - lastPos.y;
    setOffset((prev) => ({ x: prev.x + dx, y: prev.y + dy }));
    setLastPos({ x: e.clientX, y: e.clientY });
  };

  const handleMouseUp = () => setIsDragging(false);

  const handleWheel = (e: React.WheelEvent) => {
    if (e.ctrlKey || e.metaKey) {
      e.preventDefault();
      const delta = -e.deltaY / 100;
      setScale((s) => Math.min(Math.max(s + delta * ZOOM_STEP, MIN_SCALE), MAX_SCALE));
    }
  };

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().then(() => setFullscreen(true));
    } else {
      document.exitFullscreen().then(() => setFullscreen(false));
    }
  };

  useEffect(() => {
    const onFullscreenChange = () => {
      setFullscreen(!!document.fullscreenElement);
    };
    document.addEventListener("fullscreenchange", onFullscreenChange);
    return () => document.removeEventListener("fullscreenchange", onFullscreenChange);
  }, []);

  if (!open) return null;

  const style: React.CSSProperties = {
    transform: `scale(${scale}) translate(${offset.x}px, ${offset.y}px)`,
    transformOrigin: "0 0",
    cursor: scale > DEFAULT_SCALE ? "grab" : "default",
  };

  const containerStyle: React.CSSProperties = {
    position: fullscreen ? "fixed" : "relative",
    top: 0,
    left: 0,
    width: "100%",
    height: "100%",
    overflow: fullscreen ? "hidden" : "auto",
    background: fullscreen ? "#000" : undefined,
    zIndex: fullscreen ? 60 : undefined,
    touchAction: scale > DEFAULT_SCALE ? "none" : undefined,
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label="Original PDF page viewer"
      onClick={onClose}
    >
      <div
        className="fixed inset-0 bg-black/80 backdrop-blur-sm"
        onClick={(e) => e.stopPropagation()}
      />
      <div
        className="relative z-60 w-full h-full flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header toolbar */}
        <div className="flex items-center justify-between gap-3 px-4 py-3 bg-black/90 border-b border-white/10">
          <div className="flex items-center gap-2 text-sm text-white">
            <Copy className="h-4 w-4 text-accent" />
            <span className="font-semibold truncate max-w-xs">{pdfName}</span>
          </div>
          <div className="flex items-center gap-1 text-xs text-white/80">
            <span>Page {pageNumber} of {totalPages}</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={zoomOut}
              className="w-8 h-8 rounded-lg bg-white/10 hover:bg-white/20 text-white flex items-center justify-center"
              title="Zoom out"
            >
              <ZoomOut className="h-4 w-4" />
            </button>
            <span className="text-xs text-white/90 w-12 text-center">{Math.round(scale * 100)}%</span>
            <button
              type="button"
              onClick={zoomIn}
              className="w-8 h-8 rounded-lg bg-white/10 hover:bg-white/20 text-white flex items-center justify-center"
              title="Zoom in"
            >
              <ZoomIn className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={fitToWidth}
              className="w-8 h-8 rounded-lg bg-white/10 hover:bg-white/20 text-white flex items-center justify-center"
              title="Fit to width"
            >
              <Maximize className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={fitToPage}
              className="w-8 h-8 rounded-lg bg-white/10 hover:bg-white/20 text-white flex items-center justify-center"
              title="Fit to page"
            >
              <Copy className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={toggleFullscreen}
              className="w-8 h-8 rounded-lg bg-white/10 hover:bg-white/20 text-white flex items-center justify-center"
              title={fullscreen ? "Exit fullscreen" : "Fullscreen"}
            >
              {fullscreen ? <Minimize className="h-4 w-4" /> : <Maximize className="h-4 w-4" />}
            </button>
            <a
              href={imageUrl}
              download={`${pdfName.replace(/\s+/g, "_")}_p${pageNumber}.png`}
              className="w-8 h-8 rounded-lg bg-white/10 hover:bg-white/20 text-white flex items-center justify-center"
              title="Download page image"
            >
              <Download className="h-4 w-4" />
            </a>
            <button
              type="button"
              onClick={onClose}
              className="w-8 h-8 rounded-lg bg-white/10 hover:bg-white/20 text-white flex items-center justify-center"
              title="Close"
            >
              <EyeOff className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Image container */}
        <div
          ref={containerRef}
          className={clsx(
            "flex items-center justify-center w-full h-full p-8 overflow-auto",
            fullscreen ? "bg-black" : "bg-white/5",
          )}
          style={containerStyle}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onWheel={handleWheel}
        >
          <img
            ref={imgRef}
            src={imageUrl}
            alt={`Original PDF page ${pageNumber}`}
            className="block max-w-full max-h-full object-contain"
            style={style}
            onClick={(e) => e.stopPropagation()}
          />
        </div>

        {/* Page navigation */}
        <div className="flex items-center justify-between gap-4 px-4 py-3 bg-black/90 border-t border-white/10">
          <button
            type="button"
            onClick={() => onClose()}
            className="w-10 h-10 rounded-lg bg-white/10 hover:bg-white/20 text-white flex items-center justify-center"
          >
            <ChevronLeft className="h-5 w-5" />
          </button>
          <div className="text-xs text-white/90">
            {pageNumber} / {totalPages}
          </div>
          <button
            type="button"
            onClick={() => onClose()}
            className="w-10 h-10 rounded-lg bg-white/10 hover:bg-white/20 text-white flex items-center justify-center"
          >
            <ChevronRight className="h-5 w-5" />
          </button>
        </div>
      </div>
    </div>
  );
}