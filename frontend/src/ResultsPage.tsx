import { useEffect, useState, useCallback } from "react"
import { api } from "./api/client"
import { PredictionResult, UserProfile } from "./api/types"

interface ResultsPageProps {
  result: PredictionResult
  profile: UserProfile
  onNewAnalysis: () => void
  onProfile: () => void
}

export function ResultsPage({
  result,
  profile,
  onNewAnalysis,
  onProfile,
}: ResultsPageProps) {
  const [zoom, setZoom] = useState(1)
  const [downloading, setDownloading] = useState(false)
  
  // Authenticated Image State
  const [imageBlobUrl, setImageBlobUrl] = useState<string | null>(null)
  const [imageLoading, setImageLoading] = useState(true)
  const [imageError, setImageError] = useState(false)

  const loadImage = useCallback(async () => {
    setImageLoading(true)
    setImageError(false)
    try {
      const blob = await api.getReportImageBlob(result.report_id)
      const url = URL.createObjectURL(blob)
      setImageBlobUrl(url)
    } catch (err) {
      console.error("Failed to load radiograph image:", err)
      setImageError(true)
    } finally {
      setImageLoading(false)
    }
  }, [result.report_id])

  useEffect(() => {
    let activeUrl: string | null = null

    loadImage().then(() => {
      // url managed inside state
    })

    return () => {
      if (imageBlobUrl) {
        URL.revokeObjectURL(imageBlobUrl)
      }
    }
  }, [result.report_id])

  const handleZoomIn = () => setZoom((z) => Math.min(z + 0.25, 3))
  const handleZoomOut = () => setZoom((z) => Math.max(z - 0.25, 0.75))
  const handleZoomReset = () => setZoom(1)

  const handleDownload = async () => {
    try {
      setDownloading(true)
      await api.downloadReportPdf(result.report_id)
    } catch (err) {
      console.error("PDF download failed:", err)
      alert("Failed to download PDF report. Please try again.")
    } finally {
      setDownloading(false)
    }
  }

  // Format probabilities
  const rawProbs = result.probabilities || result.all_probabilities || {}
  const isChest = result.module === "chest"
  const isSpine = result.module === "spine"
  const isKnee = result.module === "knee"
  const isTumor = result.module === "tumor"

  // For chest, sort 14 bars descending
  let probEntries = Object.entries(rawProbs)
  if (isChest) {
    probEntries.sort((a, b) => b[1] - a[1])
  }

  const threshold = isChest ? (result.decision_threshold ?? 0.5) : undefined

  return (
    <div className="app-shell">
      {/* Top Header */}
      <header className="app-header">
        <div className="page-width app-header-inner">
          <button className="logo" onClick={onNewAnalysis} type="button">
            <span className="logo-mark">
              <svg fill="none" height={19} viewBox="0 0 24 24" width={19} className="icon">
                <path d="M4 9V5a1 1 0 0 1 1-1h4m6 0h4a1 1 0 0 1 1 1v4m0 6v4a1 1 0 0 1-1 1h-4M9 20H5a1 1 0 0 1-1-1v-4" />
                <circle cx="12" cy="12" r="3" />
              </svg>
            </span>
            <span>
              MediSense<span className="text-green">AI</span>
            </span>
          </button>
          <nav aria-label="Authenticated navigation" className="app-nav">
            <button className="app-nav-active" onClick={onNewAnalysis} type="button">
              Home
            </button>
          </nav>
          <button
            aria-label="Open profile"
            className="avatar-button"
            onClick={onProfile}
            type="button"
          >
            <span className="patient-avatar avatar-initials">
              {(profile.name || "User").slice(0, 2).toUpperCase()}
            </span>
            <span className="avatar-status" />
          </button>
        </div>
      </header>

      <main className="results-main page-width" style={{ padding: "32px 0 60px" }}>
        {/* Header Information Strip */}
        <section
          style={{
            background: "#ffffff",
            border: "1px solid #e5ebe7",
            borderRadius: "20px",
            padding: "20px 24px",
            marginBottom: "24px",
            display: "flex",
            flexWrap: "wrap",
            justifyContent: "space-between",
            alignItems: "center",
            boxShadow: "0 4px 20px rgba(0, 0, 0, 0.03)",
            gap: "16px",
          }}
        >
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "4px" }}>
              <span
                style={{
                  background: "#e8f8ee",
                  color: "#00c853",
                  padding: "4px 12px",
                  borderRadius: "999px",
                  fontSize: "12px",
                  fontWeight: 700,
                  textTransform: "uppercase",
                  letterSpacing: "0.04em",
                }}
              >
                {result.module_name}
              </span>
              <span style={{ color: "#8a9891", fontSize: "13px" }}>
                Architecture: <strong>{result.model_architecture}</strong>
              </span>
              {result.analysis_mode && (
                <span
                  style={{
                    background: result.analysis_mode === "roi_cropped" ? "#eff6ff" : "#fffbeb",
                    color: result.analysis_mode === "roi_cropped" ? "#2563eb" : "#d97706",
                    padding: "3px 10px",
                    borderRadius: "999px",
                    fontSize: "11px",
                    fontWeight: 700,
                  }}
                >
                  {result.analysis_mode === "roi_cropped" ? "ROI-Cropped Analysis" : "Whole Image Analysis"}
                </span>
              )}
            </div>
            <h1 style={{ fontSize: "22px", fontWeight: 800, margin: "2px 0 0", color: "#0f1a14" }}>
              Analysis Results &amp; Evaluation
            </h1>
          </div>

          <div style={{ display: "flex", flexWrap: "wrap", gap: "20px", fontSize: "13px", color: "#5b6b63" }}>
            <div>
              <span style={{ color: "#8a9891", display: "block", fontSize: "11px", fontWeight: 600 }}>REPORT ID</span>
              <strong style={{ color: "#0f1a14" }}>{result.report_id}</strong>
            </div>
            <div>
              <span style={{ color: "#8a9891", display: "block", fontSize: "11px", fontWeight: 600 }}>ACQUISITION DATE</span>
              <strong style={{ color: "#0f1a14" }}>
                {result.timestamp ? result.timestamp.slice(0, 19).replace("T", " ") : "Just now"} UTC
              </strong>
            </div>
            <div>
              <span style={{ color: "#8a9891", display: "block", fontSize: "11px", fontWeight: 600 }}>INFERENCE TIME</span>
              <strong style={{ color: "#00c853" }}>{result.inference_time_ms} ms</strong>
            </div>
          </div>
        </section>

        {/* Two-Column Workspace */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1.15fr", gap: "24px", alignItems: "start" }}>
          {/* Left Column: Radiograph Viewer */}
          <div
            style={{
              background: "#ffffff",
              border: "1px solid #e5ebe7",
              borderRadius: "20px",
              padding: "20px",
              boxShadow: "0 6px 25px rgba(0,0,0,0.03)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <div>
                <strong style={{ fontSize: "15px", color: "#0f1a14", display: "block" }}>Radiograph Image</strong>
                <small style={{ color: "#8a9891", fontSize: "12px" }}>
                  {result.filename} {result.analysis_mode === "roi_cropped" && "(Lesion ROI highlighted)"}
                </small>
              </div>

              {/* Zoom Buttons */}
              <div style={{ display: "flex", gap: "6px" }}>
                <button
                  onClick={handleZoomOut}
                  title="Zoom Out"
                  style={{
                    border: "1px solid #e5ebe7",
                    background: "#f8faf9",
                    borderRadius: "8px",
                    width: "32px",
                    height: "32px",
                    cursor: "pointer",
                    fontWeight: 700,
                  }}
                >
                  &minus;
                </button>
                <button
                  onClick={handleZoomReset}
                  title="Reset Zoom"
                  style={{
                    border: "1px solid #e5ebe7",
                    background: "#f8faf9",
                    borderRadius: "8px",
                    padding: "0 8px",
                    height: "32px",
                    fontSize: "12px",
                    cursor: "pointer",
                  }}
                >
                  {Math.round(zoom * 100)}%
                </button>
                <button
                  onClick={handleZoomIn}
                  title="Zoom In"
                  style={{
                    border: "1px solid #e5ebe7",
                    background: "#f8faf9",
                    borderRadius: "8px",
                    width: "32px",
                    height: "32px",
                    cursor: "pointer",
                    fontWeight: 700,
                  }}
                >
                  +
                </button>
              </div>
            </div>

            {/* Image viewport container */}
            <div
              style={{
                width: "100%",
                height: "440px",
                background: "#0d1611",
                borderRadius: "14px",
                overflow: "hidden",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                position: "relative",
              }}
            >
              {imageLoading && (
                <div style={{ color: "#86efac", fontSize: "13px", textAlign: "center" }}>
                  <div
                    style={{
                      width: "36px",
                      height: "36px",
                      border: "3px solid #1e3a29",
                      borderTopColor: "#00c853",
                      borderRadius: "50%",
                      animation: "spin 1s linear infinite",
                      margin: "0 auto 12px",
                    }}
                  />
                  <span>Loading acquired radiograph...</span>
                </div>
              )}

              {imageError && !imageLoading && (
                <div style={{ color: "#ef4444", fontSize: "13px", textAlign: "center", padding: "20px" }}>
                  <div style={{ marginBottom: "8px", fontWeight: 600 }}>Could not display radiograph</div>
                  <button
                    onClick={loadImage}
                    style={{
                      background: "#00c853",
                      color: "#ffffff",
                      border: "none",
                      borderRadius: "8px",
                      padding: "6px 14px",
                      fontSize: "12px",
                      fontWeight: 600,
                      cursor: "pointer",
                    }}
                  >
                    Retry
                  </button>
                </div>
              )}

              {imageBlobUrl && !imageLoading && (
                <img
                  src={imageBlobUrl}
                  alt="Analyzed X-ray scan"
                  style={{
                    maxWidth: "100%",
                    maxHeight: "100%",
                    objectFit: "contain",
                    transform: `scale(${zoom})`,
                    transition: "transform 150ms ease",
                  }}
                />
              )}
            </div>

            {/* Note on Grad-CAM */}
            {/* TODO: Grad-CAM / heatmap visualization to be implemented in future research release */}
          </div>

          {/* Right Column: AI Findings, Probabilities, Notices, Patient Info */}
          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            {/* Primary Finding / Confidence Hero Card */}
            <div
              style={{
                background: "#e8f8ee",
                border: "1.5px solid #00c853",
                borderRadius: "20px",
                padding: "24px",
                boxShadow: "0 4px 15px rgba(0, 200, 83, 0.08)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "12px" }}>
                <div>
                  <span style={{ fontSize: "12px", fontWeight: 700, color: "#00a947", textTransform: "uppercase" }}>
                    AI Prediction
                  </span>
                  <div style={{ fontSize: "28px", fontWeight: 800, color: "#0f1a14", marginTop: "4px" }}>
                    {isChest ? (
                      result.derived_no_finding ? (
                        <span style={{ color: "#00c853" }}>No Finding</span>
                      ) : (
                        <span>{result.findings_count} Flagged Finding(s)</span>
                      )
                    ) : (
                      result.prediction
                    )}
                  </div>
                  {isChest && (
                    <small style={{ color: "#5b6b63", fontSize: "12px", display: "block", marginTop: "2px" }}>
                      {result.derived_status}
                    </small>
                  )}
                </div>

                {/* Confidence Badge */}
                <div style={{ textAlign: "right" }}>
                  <span style={{ fontSize: "12px", fontWeight: 700, color: "#5b6b63", textTransform: "uppercase" }}>
                    {isSpine ? "Decision Threshold" : "Model Confidence"}
                  </span>
                  <div style={{ fontSize: "24px", fontWeight: 800, color: "#00c853", marginTop: "4px" }}>
                    {isSpine
                      ? `${((result.decision_threshold ?? 0.7574) * 100).toFixed(1)}%`
                      : result.confidence !== undefined
                      ? `${(result.confidence * 100).toFixed(1)}%`
                      : "Multi-Label"}
                  </div>
                  {result.low_confidence && (
                    <span
                      style={{
                        background: "#fffbeb",
                        color: "#d97706",
                        border: "1px solid #fde68a",
                        borderRadius: "6px",
                        fontSize: "11px",
                        fontWeight: 700,
                        padding: "2px 6px",
                        display: "inline-block",
                        marginTop: "4px",
                      }}
                    >
                      Low Confidence
                    </span>
                  )}
                </div>
              </div>

              {/* Spine Abnormal probability specifics */}
              {isSpine && (
                <div style={{ marginTop: "16px", paddingTop: "14px", borderTop: "1px solid #c8e6c9", fontSize: "13px", color: "#1b5e20" }}>
                  <strong>Abnormal Probability:</strong> {((result.probability_abnormal ?? 0) * 100).toFixed(2)}% vs. Threshold {((result.decision_threshold ?? 0.7574) * 100).toFixed(2)}%
                </div>
              )}

              {/* Interpretation Note */}
              {result.interpretation_note && (
                <div style={{ marginTop: "14px", fontSize: "13px", color: "#2e7d32", lineHeight: 1.5 }}>
                  {result.interpretation_note}
                </div>
              )}
            </div>

            {/* Tumor Whole-Image Caveat Warning Box */}
            {isTumor && result.analysis_mode === "whole_image_no_roi" && (
              <div
                style={{
                  background: "#fffbeb",
                  border: "1.5px solid #f59e0b",
                  borderRadius: "16px",
                  padding: "16px 20px",
                  color: "#92400e",
                  fontSize: "13px",
                  lineHeight: 1.5,
                }}
              >
                <strong>⚠️ Note on Whole-Image Bone Tumor Evaluation:</strong>
                <p style={{ margin: "4px 0 0" }}>
                  The bone tumor ensemble model was trained strictly on ROI-cropped lesion regions. Whole-image analysis is outside the model's training setup. Results may be unreliable and <strong>are not a screening result</strong>.
                </p>
              </div>
            )}

            {/* Probability Bars Card */}
            <div
              style={{
                background: "#ffffff",
                border: "1px solid #e5ebe7",
                borderRadius: "20px",
                padding: "22px 24px",
                boxShadow: "0 4px 20px rgba(0, 0, 0, 0.03)",
              }}
            >
              <h2 style={{ fontSize: "15px", fontWeight: 700, color: "#0f1a14", marginBottom: "16px" }}>
                Class Probabilities Distribution
              </h2>

              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {probEntries.map(([label, prob]) => {
                  const pct = (prob * 100).toFixed(1)
                  const isTop =
                    threshold !== undefined
                      ? prob >= threshold
                      : prob === Math.max(...Object.values(rawProbs))

                  return (
                    <div key={label}>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "13px", marginBottom: "4px" }}>
                        <span style={{ fontWeight: isTop ? 700 : 500, color: isTop ? "#0f1a14" : "#5b6b63" }}>
                          {label.replace("_", " ")}
                        </span>
                        <span style={{ fontWeight: isTop ? 700 : 500, color: isTop ? "#00c853" : "#5b6b63" }}>
                          {pct}%
                        </span>
                      </div>
                      <div
                        style={{
                          height: "8px",
                          background: "#f1f5f9",
                          borderRadius: "4px",
                          overflow: "hidden",
                        }}
                      >
                        <div
                          style={{
                            width: `${Math.min(100, Math.max(1, prob * 100))}%`,
                            height: "100%",
                            background: isTop ? "#00c853" : "#cbd5e1",
                            borderRadius: "4px",
                            transition: "width 400ms ease",
                          }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>

              {/* Knee Top-2 Differential */}
              {isKnee && result.top2 && result.top2.length > 1 && (
                <div style={{ marginTop: "14px", paddingTop: "12px", borderTop: "1px solid #f1f5f9", fontSize: "12.5px", color: "#5b6b63" }}>
                  <strong>Differential analysis:</strong> Primary: {result.top2[0].grade} ({(result.top2[0].probability * 100).toFixed(1)}%), Secondary: {result.top2[1].grade} ({(result.top2[1].probability * 100).toFixed(1)}%)
                </div>
              )}
            </div>

            {/* Knee Reference Description */}
            {isKnee && result.reference_description && (
              <div
                style={{
                  background: "#eff6ff",
                  border: "1px solid #bfdbfe",
                  borderRadius: "14px",
                  padding: "14px 18px",
                  fontSize: "13px",
                  color: "#1e3a8a",
                }}
              >
                <strong>Clinical Reference:</strong> {result.reference_description}
              </div>
            )}

            {/* Notices Box */}
            {result.notices && result.notices.length > 0 && (
              <div
                style={{
                  background: "#fffbeb",
                  border: "1px solid #fde68a",
                  borderRadius: "16px",
                  padding: "16px 20px",
                }}
              >
                <div style={{ fontWeight: 700, color: "#92400e", fontSize: "13px", marginBottom: "6px" }}>
                  Important Notices &amp; Limitations
                </div>
                <ul style={{ margin: 0, paddingLeft: "18px", color: "#78350f", fontSize: "12.5px", lineHeight: 1.6 }}>
                  {result.notices.map((notice, idx) => (
                    <li key={idx}>{notice}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Patient & Scan Info Strip */}
            <div
              style={{
                background: "#ffffff",
                border: "1px solid #e5ebe7",
                borderRadius: "16px",
                padding: "14px 20px",
                fontSize: "13px",
                display: "flex",
                flexWrap: "wrap",
                gap: "24px",
                color: "#5b6b63",
              }}
            >
              <div>
                <strong>Patient:</strong> {profile.name || "Not provided"} ({profile.age || "N/A"} y/o, {profile.sex || "N/A"})
              </div>
              <div>
                <strong>Contact:</strong> {profile.contact || profile.phone || "Not provided"}
              </div>
            </div>

            {/* Non-Diagnostic Disclaimer */}
            <div
              style={{
                background: "#f0fdf4",
                border: "1px solid #bbf7d0",
                borderRadius: "14px",
                padding: "14px 18px",
                fontSize: "12px",
                color: "#166534",
                lineHeight: 1.5,
              }}
            >
              <strong>Medical Disclaimer:</strong> This result is generated by an AI model and is intended for research/decision-support purposes only. It is not a medical diagnosis and should not replace professional medical evaluation.
            </div>

            {/* Primary Action Buttons */}
            <div style={{ display: "flex", gap: "14px", marginTop: "8px" }}>
              <button
                onClick={handleDownload}
                disabled={downloading}
                style={{
                  flex: 1.2,
                  background: downloading ? "#86efac" : "#00c853",
                  color: "#ffffff",
                  border: "none",
                  borderRadius: "14px",
                  padding: "16px",
                  fontSize: "15px",
                  fontWeight: 700,
                  cursor: downloading ? "not-allowed" : "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "8px",
                  boxShadow: "0 4px 14px rgba(0, 200, 83, 0.25)",
                }}
              >
                <svg fill="none" height={18} viewBox="0 0 24 24" width={18} stroke="currentColor" strokeWidth={2}>
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" />
                </svg>
                {downloading ? "Generating PDF..." : "Download Report"}
              </button>

              <button
                onClick={onNewAnalysis}
                style={{
                  flex: 1,
                  background: "#ffffff",
                  color: "#0f1a14",
                  border: "1.5px solid #e5ebe7",
                  borderRadius: "14px",
                  padding: "16px",
                  fontSize: "15px",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                Analyze Another X-ray
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
