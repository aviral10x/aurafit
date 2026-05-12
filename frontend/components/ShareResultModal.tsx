"use client";

import { useState } from "react";

interface ShareResultModalProps {
  jobId: string;
  onClose: () => void;
}

export default function ShareResultModal({ jobId, onClose }: ShareResultModalProps) {
  const [copied, setCopied] = useState(false);
  const shareUrl = `${typeof window !== "undefined" ? window.location.origin : ""}/results/${jobId}`;

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for older browsers
      const input = document.createElement("input");
      input.value = shareUrl;
      document.body.appendChild(input);
      input.select();
      document.execCommand("copy");
      document.body.removeChild(input);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-on-surface/40 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-surface-container-lowest rounded-2xl shadow-2xl max-w-md w-full p-8 z-10">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 w-10 h-10 flex items-center justify-center rounded-full hover:bg-surface-container-high transition-colors"
          aria-label="Close share modal"
        >
          <span className="material-symbols-outlined text-on-surface-variant">close</span>
        </button>

        <h3 className="font-headline text-2xl mb-2">Share Your Style</h3>
        <p className="font-body text-sm text-on-surface-variant mb-8">
          Share your style manifesto with friends or save it for later.
        </p>

        <div className="space-y-4">
          {/* Copy Link */}
          <button
            onClick={copyLink}
            className="w-full flex items-center gap-4 p-4 rounded-xl border border-outline-variant/30 hover:border-primary hover:bg-primary-fixed/10 transition-all group"
          >
            <div className="w-12 h-12 rounded-full bg-primary-fixed flex items-center justify-center shrink-0">
              <span className="material-symbols-outlined text-on-primary-fixed">link</span>
            </div>
            <div className="text-left flex-1">
              <p className="font-label text-sm font-bold">
                {copied ? "Copied!" : "Copy Link"}
              </p>
              <p className="font-body text-xs text-on-surface-variant">
                Share your results page URL
              </p>
            </div>
            <span className="material-symbols-outlined text-outline group-hover:text-primary transition-colors">
              {copied ? "check" : "content_copy"}
            </span>
          </button>

          {/* Download PDF */}
          <button
            onClick={async () => {
              try {
                const { default: api } = await import("@/lib/api");
                const response = await api.get(`/report/${jobId}`, {
                  responseType: "blob",
                });
                const url = URL.createObjectURL(response.data);
                const a = document.createElement("a");
                a.href = url;
                a.download = `aurafit-style-report.pdf`;
                a.click();
                URL.revokeObjectURL(url);
              } catch {
                alert("Failed to generate report. Please try again.");
              }
            }}
            className="w-full flex items-center gap-4 p-4 rounded-xl border border-outline-variant/30 hover:border-primary hover:bg-primary-fixed/10 transition-all group"
          >
            <div className="w-12 h-12 rounded-full bg-secondary-container flex items-center justify-center shrink-0">
              <span className="material-symbols-outlined text-on-secondary-container">picture_as_pdf</span>
            </div>
            <div className="text-left flex-1">
              <p className="font-label text-sm font-bold">Download PDF</p>
              <p className="font-body text-xs text-on-surface-variant">
                Full style report as a PDF document
              </p>
            </div>
            <span className="material-symbols-outlined text-outline group-hover:text-primary transition-colors">
              download
            </span>
          </button>

          {/* Native Share (if supported) */}
          {typeof navigator !== "undefined" && "share" in navigator && (
            <button
              onClick={() => {
                navigator.share({
                  title: "My AuraFit Style Profile",
                  text: "Check out my personalized style analysis from AuraFit!",
                  url: shareUrl,
                });
              }}
              className="w-full flex items-center gap-4 p-4 rounded-xl border border-outline-variant/30 hover:border-primary hover:bg-primary-fixed/10 transition-all group"
            >
              <div className="w-12 h-12 rounded-full bg-tertiary-container flex items-center justify-center shrink-0">
                <span className="material-symbols-outlined text-on-tertiary-container">share</span>
              </div>
              <div className="text-left flex-1">
                <p className="font-label text-sm font-bold">Share via...</p>
                <p className="font-body text-xs text-on-surface-variant">
                  Use your device&apos;s native share menu
                </p>
              </div>
              <span className="material-symbols-outlined text-outline group-hover:text-primary transition-colors">
                arrow_forward
              </span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
