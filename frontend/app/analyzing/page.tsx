"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { getJobStatus } from "@/lib/api";

const steps = [
  "Photos uploaded securely",
  "Reading facial features & skin tone...",
  "Analyzing body proportions...",
  "Detecting your style vibe...",
  "Matching your color palette...",
  "Curating your outfits...",
];

const bgImages = [
  "https://lh3.googleusercontent.com/aida-public/AB6AXuALINxaMZ76ueV040ItXgBzwUwOpZk4ESM1PdOFPlQwvbEoWcEzdBtCcq3t_v70luQfBpLTlZnQZzdexJN9dDxfAR1AsDEAeo2h-kEcBza3aNpFSFtqNXCL5BVXDenr9VIEdFY-CXnjikmxaXeEuu8PlBegaaU5xYW_r5NQ1kGOBSJu20hxse6SwV5ks8Jaum_Qkn2ctc1Jy8eqlKeNqAPyjVQl8A0jxgt8SbBVPyE61at5y5_KHhKwvmZsqsOkStQvFjFNMJSaOjY",
  "https://lh3.googleusercontent.com/aida-public/AB6AXuDUD_eVZCWJDYxItJ6ClocJOe0i7Oue-AcSaJmYj1Xry1_nF_K3L4_EgFbZt_RCVUODQ6mRaYCwSpeP6SBk6adQvebV2-huqc8vFyzlGj8zOsePxHBssX6rrM49eMX9YiHkWBcrzv2MmxWfjLDBIPirTQvKi7MH5o5gQALJKIaSF9HNsSvEj0V5QPo_ws76USXp47_GVsAmLP6Xjp6aPDISEVhOFK2O9m0elMPIoHAXDuAIAgFREckSYr0xoV8XPqFLz9-gJJsqZ-s",
  "https://lh3.googleusercontent.com/aida-public/AB6AXuCyc8S4PMPIAc0jtfqzWthq9reUF1AxYriPXrBNS2xdt3tZJFZIvg6GKW0sAzdhvHNGwttKaoRRQOL7eSrwO_hyQ-2GY2vf5Wq0gFTTOuFnHb-m3Ba_Mji8dIWjB9ghmlLp68l0tLfVdh0JIwi549cATK_Ts9L5IZSrX6NjNlDVFAC_c6StLIrfaic7lYjkEjfX9Hc9WHeGXXuvU1fJhtg9GMQDm9zshuszJIR7SAelY1nmq_VqFSWVPKwlAm_KlD03Z3z1GHrF5MA",
  "https://lh3.googleusercontent.com/aida-public/AB6AXuBSYkfCSQ_6WWIx7N7lSzU_KlCClh9I-u0WXOMuH3gXmnw7YnQQJve7ByD4fpQlbTH3wxUwJQ_SqG7sE1wMQH2BtYU9iQGZh-ftl6yqAjXe8JYHc0JIq5MVY9fax7sSF9QSgIVuw_nCRjoLiypIRkxbG3NbiqFx9E9MbYCjWgehZp-VZsZgw15pko9bIivkRVaVT8xgNVV2FsnziXmPGzZswyzQXk83x8yumV8s_93Q_VnNxhZUj7lqg1cYctvuX5gJNlxmqxH0bHE",
  "https://lh3.googleusercontent.com/aida-public/AB6AXuARLNdA85MmRQ3_vY79ptvW3pQxtsKGrjQJCCKhnN27WxuMTm3ya5l1Hrju59hF9RNRjiKME2V8FMgoO_1Fwyfc_S7UU4ZpZzSmPRxJbS48kb_bY0mO1FMyZGqkJFjpQtzacTkeMToeRoXLdYd5SPOBfCxZPM_gb_t1ASIz_jfUYG99WWslYaAstRnwOl8VQXnOkjK-sA8H5jA4Cko1VcqA1OjaMWzmn4kvTxArKtBrmzFjaWesSkimEeif19MieE7e9XFWPDBS8yc",
  "https://lh3.googleusercontent.com/aida-public/AB6AXuCtZCNQ-d5yGTpuIAbCF34TQEu6N7-EiQUbbN5XQ5s6763Hfaesj78Fxs_n2hkRyOM3cY7okPQyVtQv7f6YYJP1tIU0kAM7-11GCwbDPEo0CGrpu15htzhkAWRJ-P1005ghPADpjHxqaNQX2JIQplaIknxOlbEWXGy2RZ8tX4WPI-aJgwUybo9IWcQD8IpDSzN4IVGyrz04Ogx2tldgLWIvoQKA6eckoSAGHb_XGuoekLDWzmqOk1tGbvFAsKlcHIwGB__wwo5bqfY",
  "https://lh3.googleusercontent.com/aida-public/AB6AXuCHDbr4GNm4XvUNIXWqvdjEDKjDoOlz2qvjGrHQE7KYpGYOmO1YJfaTJ6bBYn-x9KeZJvvCGcDTb8a2HD24fD91OX2caHHGo-Iism9xr_m3DjX9SjviHJGS0pZeYm9xFz4oAU9NMQe3FS46MmnrBpmlT5lbVwC0x1SU_cl4OIrTcKVKe1VFPZrG9YkJYMZnQI-pJcpysJn8xX_KbKDEnKIas13MHvi1FA11MJC0e6a29YUn_ILyyrDVUCzfr825lHSUi6D7OsdIwgA",
  "https://lh3.googleusercontent.com/aida-public/AB6AXuB1AmCv0k3N9vRR92oSFqqeq_k1yZhdeZJ10pvEmVPioWWrZ8gK6CTxDRulk0bNHGq4vcj9NWB5PP8xMSb-h6urXzgGFz3lDd7b5mYR3Z7bFlcnoV6pQywN3rN77MNixMlDL7dTYPp21nT9ZI65iRWSsIgf-nvkvZUOgIM4bbAXDiDOhttJHzhCzI4qOds2LF3kWAM5xTaI68arZi9bnFXNz8sXmOBJcCQD-bEgxIEEvxoH0umN4FTGB_EmvXC2SilCPKqRme5Nc0g",
];

const completeStatuses = new Set(["complete", "completed", "succeeded", "success"]);
const failedStatuses = new Set(["failed", "failure", "error"]);

function normalizeStatus(status: string) {
  return status.trim().toLowerCase();
}

function statusCopy(status: string, errorMessage: string) {
  if (failedStatuses.has(status)) {
    return {
      eyebrow: "Needs attention",
      title: "We hit a styling snag.",
      detail: errorMessage || "Analysis failed. Please try uploading again.",
    };
  }

  if (status === "queued") {
    return {
      eyebrow: "Queued",
      title: "You're next in the styling queue.",
      detail: "We've received your photos and will start the analysis shortly.",
    };
  }

  if (status === "checking") {
    return {
      eyebrow: "Checking",
      title: "Checking the analysis queue...",
      detail: errorMessage || "Reconnecting without restarting your job.",
    };
  }

  return {
    eyebrow: "Processing",
    title: "Reading your aura...",
    detail: "Your analysis is running now. This page will move forward automatically.",
  };
}

function AnalyzingContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const jobId = searchParams.get("jobId") || "";
  const [currentStep, setCurrentStep] = useState(0);
  const [jobStatus, setJobStatus] = useState("queued");
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentStep((prev) => {
        if (prev >= steps.length - 1) {
          clearInterval(interval);
          return prev;
        }
        return prev + 1;
      });
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!jobId) {
      setErrorMessage("Missing analysis job. Please upload your photos again.");
      setJobStatus("failed");
      return;
    }

    let cancelled = false;
    let timeoutId: ReturnType<typeof setTimeout> | undefined;

    async function pollJobStatus() {
      try {
        const data = await getJobStatus(jobId);
        if (cancelled) return;

        const normalizedStatus = normalizeStatus(data.status);
        setJobStatus(normalizedStatus);
        setErrorMessage(data.error_message || "");

        if (completeStatuses.has(normalizedStatus)) {
          router.replace(`/results/${encodeURIComponent(jobId)}`);
          return;
        }

        if (failedStatuses.has(normalizedStatus)) {
          setErrorMessage(data.error_message || "Analysis failed. Please try uploading again.");
          return;
        }

        timeoutId = setTimeout(pollJobStatus, 3000);
      } catch {
        if (cancelled) return;
        setJobStatus("checking");
        setErrorMessage("Reconnecting to the analysis queue...");
        timeoutId = setTimeout(pollJobStatus, 5000);
      }
    }

    pollJobStatus();

    return () => {
      cancelled = true;
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, [jobId, router]);

  const isFailed = failedStatuses.has(jobStatus);
  const copy = statusCopy(jobStatus, errorMessage);

  return (
    <div className="bg-[#0D0D0D] text-on-surface font-body min-h-screen flex flex-row items-center justify-center overflow-hidden relative">
      {/* Background Layer */}
      <div className="fixed inset-0 z-0 grid grid-cols-4 grid-rows-2 gap-4 p-4 bg-collage">
        {bgImages.map((url, i) => (
          <div
            key={i}
            className="w-full h-full bg-cover bg-center"
            style={{ backgroundImage: `url('${url}')` }}
          />
        ))}
      </div>

      {/* Loading Content */}
      <main className="relative z-10 flex flex-col items-center max-w-xl w-full px-6 text-center">
        {/* Logo */}
        <div className="mb-16">
          <div className="aura-pulse bg-primary/20 p-6 rounded-full inline-block mb-4">
            <h1 className="text-4xl font-headline italic tracking-tighter text-primary-fixed-dim">
              AuraFit
            </h1>
          </div>
        </div>

        {/* Scanner Visual */}
        <div className="relative w-64 h-64 mb-16 flex items-center justify-center">
          <div className="absolute inset-0 scanner-ring animate-[spin_3s_linear_infinite]"></div>
          <div className="absolute inset-4 scanner-ring animate-[spin_5s_linear_infinite_reverse] opacity-50"></div>
          <div className="relative flex flex-col items-center">
            <span className="material-symbols-outlined text-primary text-5xl mb-2">auto_awesome</span>
            <p className="font-label text-xs tracking-[0.3em] uppercase text-primary/70">{copy.eyebrow}</p>
          </div>
        </div>

        {/* Headline */}
        <div className="mb-12">
          <h2 className="text-4xl md:text-5xl font-headline text-surface-container-lowest leading-tight mb-4">
            {copy.title}
          </h2>
          <p className="font-label text-[10px] tracking-widest text-tertiary uppercase">
            {isFailed ? copy.detail : `Job ${jobId} · ${copy.eyebrow}`}
          </p>
          {!isFailed && (
            <p className="font-body text-sm text-surface-container-highest mt-3">
              {copy.detail}
            </p>
          )}
        </div>

        {/* Status Steps */}
        <div className="w-full max-w-sm space-y-4 text-left">
          {steps.map((step, i) => {
            const isCompleted = i < currentStep;
            const isActive = i === currentStep;
            const isPending = i > currentStep;

            return (
              <div key={i} className={`flex items-center gap-4 ${isPending ? (i === currentStep + 1 ? "opacity-30" : i === currentStep + 2 ? "opacity-20" : "opacity-10") : ""}`}>
                <div className="w-5 h-5 flex items-center justify-center">
                  {isCompleted ? (
                    <div className="w-5 h-5 flex items-center justify-center rounded-full border border-secondary text-secondary">
                      <span className="material-symbols-outlined text-sm" style={{ fontVariationSettings: "'FILL' 1" }}>check</span>
                    </div>
                  ) : isActive ? (
                    <span className="material-symbols-outlined text-primary text-lg animate-spin">progress_activity</span>
                  ) : (
                    <div className="w-1.5 h-1.5 rounded-full bg-outline-variant"></div>
                  )}
                </div>
                <span className={`font-body text-sm ${
                  isCompleted ? "text-secondary" :
                  isActive && !isFailed ? "text-surface-container-lowest font-medium" :
                  "text-surface-container-highest"
                }`}>
                  {step}
                </span>
              </div>
            );
          })}
        </div>
        {isFailed && (
          <button
            onClick={() => router.push("/upload")}
            className="mt-8 bg-primary text-on-primary px-6 py-3 rounded-lg font-label uppercase tracking-widest text-xs"
          >
            Upload Again
          </button>
        )}
      </main>

      {/* Footer */}
      <footer className="fixed bottom-8 w-full text-center z-10 px-8">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center opacity-40">
          <p className="font-label text-[10px] tracking-widest text-surface-container-highest uppercase">
            &copy; 2026 AuraFit. Powered by Claude AI
          </p>
          <div className="flex gap-6 mt-4 md:mt-0">
            <span className="font-label text-[10px] tracking-widest text-surface-container-highest uppercase">Encrypted</span>
            <span className="font-label text-[10px] tracking-widest text-surface-container-highest uppercase">Private</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default function AnalyzingPage() {
  return (
    <Suspense fallback={null}>
      <AnalyzingContent />
    </Suspense>
  );
}
