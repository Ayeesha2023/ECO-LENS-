import {
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  useNavigate,
} from "react-router-dom";

import logo
  from "../assets/ecolens-logo.png";

import {
  API_BASE_URL,
  apiRequest,
} from "../services/api";

import "../styles/household-dashboard.css";
import "../styles/household-chat.css";


const menuItems = [
  {
    id: "overview",
    icon: "⌂",
    label: "Overview",
  },
  {
    id: "detect",
    icon: "◎",
    label: "Detect My Waste",
  },
  {
    id: "report",
    icon: "⌖",
    label: "Report Public Waste",
  },
  {
    id: "reports",
    icon: "▤",
    label: "My Reports",
  },
  {
    id: "history",
    icon: "◷",
    label: "Detection History",
  },
  {
    id: "profile",
    icon: "○",
    label: "Profile",
  },
];


function formatDate(value) {
  if (!value) {
    return "—";
  }

  const date = new Date(value);

  if (
    Number.isNaN(
      date.getTime()
    )
  ) {
    return value;
  }

  return date.toLocaleString(
    "en-BD",
    {
      dateStyle: "medium",
      timeStyle: "short",
    }
  );
}


function statusLabel(value) {
  const labels = {
    submitted:
      "Submitted",

    under_review:
      "Under Review",

    assigned:
      "Employee Assigned",

    accepted:
      "Employee Accepted",

    in_progress:
      "Cleanup In Progress",

    completed:
      "Completed",

    rejected:
      "Rejected",

    cancelled:
      "Cancelled",

    low:
      "Low",

    medium:
      "Medium",

    high:
      "High",

    critical:
      "Critical",
  };

  return (
    labels[value] ||
    String(value || "")
      .replaceAll("_", " ")
      .replace(
        /\b\w/g,
        (letter) =>
          letter.toUpperCase()
      )
  );
}


function mediaUrl(path) {
  if (!path) {
    return null;
  }

  const clean = String(path)
    .replaceAll("\\", "/")
    .replace(/^uploads\//, "");

  return (
    `${API_BASE_URL}` +
    `/api/household/dashboard/media/${clean}`
  );
}


function GoogleMap({
  latitude,
  longitude,
}) {
  if (
    latitude === null ||
    latitude === undefined ||
    latitude === "" ||
    longitude === null ||
    longitude === undefined ||
    longitude === ""
  ) {
    return (
      <div className="household-empty-map">
        <span>
          ⌖
        </span>

        <p>
          Add your exact GPS location
          to preview the public waste
          location here.
        </p>
      </div>
    );
  }

  const mapUrl =
    `https://www.google.com/maps?q=${latitude},${longitude}&output=embed`;

  return (
    <iframe
      className="household-map-frame"
      src={mapUrl}
      title="Public waste location"
      loading="lazy"
      referrerPolicy="no-referrer-when-downgrade"
    />
  );
}


function ReportProgress({
  report,
}) {
  const stages = [
    "submitted",
    "assigned",
    "in_progress",
    "completed",
  ];

  let effectiveStatus =
    report.report_status;

  if (
    report.report_status ===
      "under_review"
  ) {
    effectiveStatus =
      "submitted";
  }

  if (
    report.assignment_status ===
      "accepted"
  ) {
    effectiveStatus =
      "assigned";
  }

  if (
    report.assignment_status ===
      "in_progress"
  ) {
    effectiveStatus =
      "in_progress";
  }

  if (
    report.report_status ===
      "completed"
  ) {
    effectiveStatus =
      "completed";
  }

  const currentIndex =
    stages.indexOf(
      effectiveStatus
    );

  if (
    [
      "rejected",
      "cancelled",
    ].includes(
      report.report_status
    )
  ) {
    return (
      <div className="household-report-stopped">
        {
          statusLabel(
            report.report_status
          )
        }
      </div>
    );
  }

  return (
    <div className="household-progress">
      {stages.map(
        (
          stage,
          index
        ) => (
          <div
            className={
              index <=
              currentIndex
                ? "household-progress-step active"
                : "household-progress-step"
            }
            key={stage}
          >
            <span>
              {index <
              currentIndex
                ? "✓"
                : index + 1}
            </span>

            <small>
              {
                statusLabel(
                  stage
                )
              }
            </small>
          </div>
        )
      )}
    </div>
  );
}


function GuidanceList({
  title,
  items,
}) {
  if (
    !Array.isArray(items) ||
    items.length === 0
  ) {
    return null;
  }

  return (
    <div className="household-guidance-block">
      <strong>
        {title}
      </strong>

      <ul>
        {items.map(
          (
            item,
            index
          ) => (
            <li key={index}>
              {item}
            </li>
          )
        )}
      </ul>
    </div>
  );
}


function HouseholdDashboard() {
  const navigate =
    useNavigate();

  const [
    activeSection,
    setActiveSection,
  ] = useState(
    "overview"
  );

  const [
    data,
    setData,
  ] = useState(null);

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    error,
    setError,
  ] = useState("");


  // ========================================================
  // PERSONAL DETECTION
  // ========================================================

  const [
    detectionFile,
    setDetectionFile,
  ] = useState(null);

  const [
    detectionPreview,
    setDetectionPreview,
  ] = useState("");

  const [
    detectionLoading,
    setDetectionLoading,
  ] = useState(false);

  const [
    detectionResult,
    setDetectionResult,
  ] = useState(null);

  const [
    adviceResult,
    setAdviceResult,
  ] = useState(null);

  const [
    detectionMessage,
    setDetectionMessage,
  ] = useState("");


  // ========================================================
  // GROUNDED HOUSEHOLD FOLLOW-UP CHAT
  // ========================================================

  const [
    currentAdviceId,
    setCurrentAdviceId,
  ] = useState(null);

  const [
    chatMessages,
    setChatMessages,
  ] = useState([]);

  const [
    chatInput,
    setChatInput,
  ] = useState("");

  const [
    chatLoading,
    setChatLoading,
  ] = useState(false);

  const [
    chatError,
    setChatError,
  ] = useState("");

  const chatEndRef =
    useRef(null);


  // ========================================================
  // PUBLIC REPORT
  // ========================================================

  const [
    reportFile,
    setReportFile,
  ] = useState(null);

  const [
    reportPreview,
    setReportPreview,
  ] = useState("");

  const [
    reportLoading,
    setReportLoading,
  ] = useState(false);

  const [
    locationLoading,
    setLocationLoading,
  ] = useState(false);

  const [
    reportMessage,
    setReportMessage,
  ] = useState("");

  const [
    reportError,
    setReportError,
  ] = useState("");

  const [
    reportForm,
    setReportForm,
  ] = useState({
    title: "",
    description: "",
    location_region_id: "",
    address_text: "",
    latitude: "",
    longitude: "",
  });


  // ========================================================
  // LOAD DASHBOARD
  // ========================================================

  const loadDashboard =
    async () => {
      try {
        setLoading(true);
        setError("");

        const response =
          await apiRequest(
            "/api/household/dashboard/bootstrap"
          );

        setData(
          response
        );

        const preferredLocation =
          response.household
            ?.locality_region_id ||
          response.household
            ?.region_id ||
          "";

        setReportForm(
          (previous) => ({
            ...previous,

            location_region_id:
              previous.location_region_id ||
              String(
                preferredLocation ||
                ""
              ),

            address_text:
              previous.address_text ||
              response.household
                ?.address_text ||
              "",
          })
        );

      } catch (
        requestError
      ) {
        setError(
          requestError.message
        );

        if (
          requestError.status ===
            401 ||
          requestError.status ===
            403
        ) {
          setTimeout(
            () => {
              navigate(
                "/login"
              );
            },
            900
          );
        }

      } finally {
        setLoading(false);
      }
    };


  useEffect(
    () => {
      loadDashboard();
    },
    []
  );


  useEffect(
    () => {
      return () => {
        if (
          detectionPreview
        ) {
          URL.revokeObjectURL(
            detectionPreview
          );
        }

        if (
          reportPreview
        ) {
          URL.revokeObjectURL(
            reportPreview
          );
        }
      };
    }, [
      detectionPreview,
      reportPreview,
    ]
  );


  useEffect(
    () => {
      chatEndRef.current
        ?.scrollIntoView({
          behavior: "smooth",
        });
    },
    [
      chatMessages,
      chatLoading,
    ]
  );


  const activeReports =
    useMemo(
      () => {
        if (!data) {
          return [];
        }

        return (
          data.reports || []
        ).filter(
          (report) =>
            [
              "submitted",
              "under_review",
              "assigned",
              "in_progress",
            ].includes(
              report.report_status
            )
        );
      },
      [data]
    );


  // ========================================================
  // PERSONAL DETECT MY WASTE
  // ========================================================

  const chooseDetectionFile =
    (file) => {
      if (
        detectionPreview
      ) {
        URL.revokeObjectURL(
          detectionPreview
        );
      }

      setDetectionFile(
        file || null
      );

      setDetectionPreview(
        file
          ? URL.createObjectURL(
              file
            )
          : ""
      );

      setDetectionResult(null);
      setAdviceResult(null);
      setDetectionMessage("");
      setCurrentAdviceId(null);
      setChatMessages([]);
      setChatInput("");
      setChatError("");
    };


  const detectWaste =
    async () => {
      if (!detectionFile) {
        setDetectionMessage(
          "Choose or take a waste photo first."
        );

        return;
      }

      try {
        setDetectionLoading(
          true
        );

        setDetectionMessage("");
        setDetectionResult(null);
        setAdviceResult(null);
        setCurrentAdviceId(null);
        setChatMessages([]);
        setChatInput("");
        setChatError("");

        const formData =
          new FormData();

        formData.append(
          "image",
          detectionFile
        );

        const response =
          await apiRequest(
            "/api/household/dashboard/detect",
            {
              method: "POST",
              body: formData,
            }
          );

        const detection =
          response.detection;

        setDetectionResult(
          detection
        );

        if (
          !detection
            ?.detected_objects
            ?.length
        ) {
          setDetectionMessage(
            "No supported EcoLens waste class passed its confidence threshold. Try a clearer photo."
          );

          await loadDashboard();
          return;
        }

        setDetectionMessage(
          "Waste detected. Retrieving household guidance..."
        );

        // Existing Household RAG API.
        // The RAG pipeline reads this completed detection session,
        // maps classes -> categories, then retrieves safety and
        // verified household knowledge.
        const adviceResponse =
          await apiRequest(
            `/api/household/${data.household.user_id}/advice`,
            {
              method: "POST",

              body:
                JSON.stringify(
                  {
                    detection_session_id:
                      detection.detection_session_id,

                    language:
                      "en",

                    response_language:
                      "en",
                  }
                ),
            }
          );

        const result =
          adviceResponse.result ||
          adviceResponse.advice ||
          adviceResponse;

        const generatedAdviceId =
          adviceResponse.advice_id ||
          adviceResponse.result
            ?.advice_id ||
          null;

        setAdviceResult(
          result
        );

        setCurrentAdviceId(
          generatedAdviceId
        );

        const initialSummary =
          result?.summary ||
          result?.result
            ?.summary ||
          "EcoLens prepared grounded guidance for the detected waste.";

        const initialMode =
          result?.mode ||
          result?.result
            ?.mode ||
          adviceResponse.mode ||
          null;

        const initialSourceText =
          initialMode ===
          "gemini_grounded"
            ? "I generated the initial advice using the YOLO detection and verified EcoLens RAG context."
            : "The initial advice is currently using the grounded offline fallback because Gemini was unavailable.";

        setChatMessages(
          [
            {
              role:
                "assistant",

              content:
                `${initialSummary} ${initialSourceText} You can ask me follow-up questions about this detection.`,
            },
          ]
        );

        setDetectionMessage(
          "Detection and household guidance completed."
        );

        await loadDashboard();

      } catch (
        requestError
      ) {
        setDetectionMessage(
          requestError.message
        );

      } finally {
        setDetectionLoading(
          false
        );
      }
    };


  // ========================================================
  // HOUSEHOLD FOLLOW-UP CHAT
  // ========================================================

  const sendChatMessage =
    async (
      event = null
    ) => {
      event?.preventDefault();

      const message =
        chatInput.trim();

      if (!message) {
        return;
      }

      if (
        !detectionResult
          ?.detection_session_id
      ) {
        setChatError(
          "Complete a waste detection before using the follow-up chat."
        );

        return;
      }

      if (!currentAdviceId) {
        setChatError(
          "The initial Household advice is not available for follow-up questions."
        );

        return;
      }

      const previousMessages =
        chatMessages.slice(-10);

      const userMessage = {
        role:
          "user",

        content:
          message,
      };

      setChatMessages(
        (previous) => [
          ...previous,
          userMessage,
        ]
      );

      setChatInput("");
      setChatError("");

      try {
        setChatLoading(true);

        const response =
          await apiRequest(
            `/api/household/${data.household.user_id}/chat`,
            {
              method:
                "POST",

              body:
                JSON.stringify(
                  {
                    detection_session_id:
                      detectionResult
                        .detection_session_id,

                    advice_id:
                      currentAdviceId,

                    message:
                      message,

                    language:
                      "en",

                    history:
                      previousMessages
                        .map(
                          (
                            chatMessage
                          ) => ({
                            role:
                              chatMessage.role,

                            content:
                              chatMessage.content,
                          })
                        ),
                  }
                ),
            }
          );

        setChatMessages(
          (previous) => [
            ...previous,

            {
              role:
                "assistant",

              content:
                response.answer,

              groundingNote:
                response.grounding_note,

              localVerificationRequired:
                response
                  .local_verification_required,
            },
          ]
        );

      } catch (
        requestError
      ) {
        setChatError(
          requestError.message ||
          "The follow-up question could not be answered."
        );

      } finally {
        setChatLoading(false);
      }
    };


  // ========================================================
  // PUBLIC REPORT GPS
  // ========================================================

  const useCurrentLocation =
    () => {
      if (
        !navigator.geolocation
      ) {
        setReportError(
          "This browser does not support location access."
        );

        return;
      }

      setLocationLoading(true);
      setReportError("");

      navigator.geolocation
        .getCurrentPosition(
          (position) => {
            setReportForm(
              (previous) => ({
                ...previous,

                latitude:
                  position.coords.latitude
                    .toFixed(7),

                longitude:
                  position.coords.longitude
                    .toFixed(7),
              })
            );

            setLocationLoading(false);
          },

          (geoError) => {
            setLocationLoading(false);

            setReportError(
              geoError.message ||
              "Location permission was not granted."
            );
          },

          {
            enableHighAccuracy:
              true,

            timeout:
              12000,

            maximumAge:
              0,
          }
        );
    };


  const chooseReportFile =
    (file) => {
      if (
        reportPreview
      ) {
        URL.revokeObjectURL(
          reportPreview
        );
      }

      setReportFile(
        file || null
      );

      setReportPreview(
        file
          ? URL.createObjectURL(
              file
            )
          : ""
      );
    };


  const submitPublicReport =
    async (
      event
    ) => {
      event.preventDefault();

      if (!reportFile) {
        setReportError(
          "Upload or take a photo of the public waste."
        );

        return;
      }

      if (
        !reportForm.latitude ||
        !reportForm.longitude
      ) {
        setReportError(
          "Add the exact GPS location before submitting."
        );

        return;
      }

      try {
        setReportLoading(true);
        setReportError("");
        setReportMessage("");

        const formData =
          new FormData();

        formData.append(
          "image",
          reportFile
        );

        Object.entries(
          reportForm
        ).forEach(
          ([key, value]) => {
            formData.append(
              key,
              value
            );
          }
        );

        const response =
          await apiRequest(
            "/api/household/dashboard/reports",
            {
              method: "POST",
              body: formData,
            }
          );

        setReportMessage(
          response.message
        );

        setReportFile(null);

        if (
          reportPreview
        ) {
          URL.revokeObjectURL(
            reportPreview
          );
        }

        setReportPreview("");

        setReportForm(
          (previous) => ({
            ...previous,
            title: "",
            description: "",
            latitude: "",
            longitude: "",
          })
        );

        await loadDashboard();

        setTimeout(
          () => {
            setActiveSection(
              "reports"
            );
          },
          900
        );

      } catch (
        requestError
      ) {
        setReportError(
          requestError.message
        );

      } finally {
        setReportLoading(false);
      }
    };


  // ========================================================
  // LOGOUT
  // ========================================================

  const handleLogout =
    async () => {
      try {
        await apiRequest(
          "/api/auth/logout",
          {
            method: "POST",
          }
        );

      } finally {
        navigate(
          "/login"
        );
      }
    };


  if (loading) {
    return (
      <main className="household-loading">
        <img
          src={logo}
          alt="EcoLens"
        />

        <p>
          Loading Household Dashboard...
        </p>
      </main>
    );
  }


  if (
    error ||
    !data
  ) {
    return (
      <main className="household-loading">
        <img
          src={logo}
          alt="EcoLens"
        />

        <p>
          {error ||
            "Household dashboard could not be loaded."}
        </p>
      </main>
    );
  }


  const {
    household,
    summary,
    reports,
    detections,
    location_options:
      locationOptions,
  } = data;

  const guidance =
    adviceResult?.guidance ||
    adviceResult?.result
      ?.guidance ||
    [];

  const adviceMode =
    adviceResult?.mode ||
    adviceResult?.result
      ?.mode ||
    null;


  return (
    <main className="household-dashboard">

      {/* ====================================================
          SIDEBAR
          ==================================================== */}

      <aside className="household-sidebar">
        <div>
          <div className="household-brand">
            <img
              src={logo}
              alt="EcoLens"
            />

            <div>
              <strong>
                EcoLens
              </strong>

              <span>
                Household
              </span>
            </div>
          </div>

          <nav className="household-nav">
            {menuItems.map(
              (item) => (
                <button
                  type="button"
                  key={item.id}
                  className={
                    activeSection ===
                    item.id
                      ? "household-nav-item active"
                      : "household-nav-item"
                  }
                  onClick={() =>
                    setActiveSection(
                      item.id
                    )
                  }
                >
                  <span>
                    {item.icon}
                  </span>

                  {item.label}
                </button>
              )
            )}
          </nav>
        </div>

        <div className="household-sidebar-bottom">
          <div className="household-profile-mini">
            <div className="household-profile-letter">
              {
                household.full_name
                  ?.charAt(0)
                  ?.toUpperCase()
              }
            </div>

            <div>
              <strong>
                {household.full_name}
              </strong>

              <span>
                {
                  household.locality_name ||
                  household.ward_name ||
                  "Bangladesh"
                }
              </span>
            </div>
          </div>

          <button
            type="button"
            className="household-logout"
            onClick={
              handleLogout
            }
          >
            Log Out
          </button>
        </div>
      </aside>


      {/* ====================================================
          MAIN
          ==================================================== */}

      <section className="household-main">
        <header className="household-topbar">
          <div>
            <span>
              SMARTER WASTE ACTION
            </span>

            <h1>
              {activeSection ===
              "overview"
                ? "Overview"
                : menuItems.find(
                    (item) =>
                      item.id ===
                      activeSection
                  )?.label}
            </h1>
          </div>

          <div className="household-location-pill">
            ⌖{" "}
            {
              household.locality_name ||
              household.ward_name ||
              "Location not set"
            }
          </div>
        </header>


        {/* ==================================================
            OVERVIEW
            ================================================== */}

        {activeSection ===
          "overview" && (
          <div className="household-section">
            <section className="household-hero">
              <div>
                <span>
                  CLEANER COMMUNITIES START HERE
                </span>

                <h2>
                  Hello,
                  {" "}
                  {household.full_name}.
                </h2>

                <p>
                  Identify your own waste for
                  disposal guidance, or report
                  dumped public waste so the
                  responsible authority can send
                  a cleanup employee.
                </p>
              </div>

              <div className="household-hero-mark">
                ◎
              </div>
            </section>

            <div className="household-stat-grid">
              <article className="household-stat-card">
                <span>
                  Previous Detections
                </span>

                <strong>
                  {
                    summary.previous_detections
                  }
                </strong>
              </article>

              <article className="household-stat-card">
                <span>
                  Public Reports
                </span>

                <strong>
                  {
                    summary.total_reports
                  }
                </strong>
              </article>

              <article className="household-stat-card">
                <span>
                  Active Reports
                </span>

                <strong>
                  {
                    summary.active_reports
                  }
                </strong>
              </article>

              <article className="household-stat-card">
                <span>
                  Cleanups Completed
                </span>

                <strong>
                  {
                    summary.completed_reports
                  }
                </strong>
              </article>
            </div>

            <div className="household-section-heading">
              <div>
                <span>
                  TWO DIFFERENT ACTIONS
                </span>

                <h2>
                  What would you like to do?
                </h2>
              </div>
            </div>

            <div className="household-action-grid">
              <button
                type="button"
                className="household-action-card household-detect-card"
                onClick={() =>
                  setActiveSection(
                    "detect"
                  )
                }
              >
                <div className="household-action-icon">
                  ◎
                </div>

                <span>
                  PERSONAL WASTE HELP
                </span>

                <h3>
                  Detect My Waste
                </h3>

                <p>
                  Take or upload a photo.
                  EcoLens detects supported waste
                  classes and retrieves household
                  disposal and safety guidance.
                </p>

                <strong>
                  Start Detection →
                </strong>
              </button>

              <button
                type="button"
                className="household-action-card household-report-card"
                onClick={() =>
                  setActiveSection(
                    "report"
                  )
                }
              >
                <div className="household-action-icon">
                  ⌖
                </div>

                <span>
                  COMMUNITY CLEANUP
                </span>

                <h3>
                  Report Public Waste
                </h3>

                <p>
                  Report roadside or public dumped
                  garbage with a photo and exact
                  location. This goes to the
                  responsible ward authority.
                </p>

                <strong>
                  Create Report →
                </strong>
              </button>
            </div>

            {activeReports.length >
              0 && (
              <>
                <div className="household-section-heading">
                  <div>
                    <span>
                      TRACK CLEANUP
                    </span>

                    <h2>
                      Active Public Reports
                    </h2>
                  </div>

                  <button
                    type="button"
                    className="household-text-button"
                    onClick={() =>
                      setActiveSection(
                        "reports"
                      )
                    }
                  >
                    View all →
                  </button>
                </div>

                <div className="household-report-list">
                  {activeReports
                    .slice(0, 3)
                    .map(
                      (report) => (
                        <article
                          className="household-report-card"
                          key={
                            report.report_id
                          }
                        >
                          <div className="household-report-image">
                            {report.before_image_path ? (
                              <img
                                src={
                                  mediaUrl(
                                    report.before_image_path
                                  )
                                }
                                alt="Reported public waste"
                              />
                            ) : (
                              <span>
                                📷
                              </span>
                            )}
                          </div>

                          <div className="household-report-body">
                            <div className="household-report-top">
                              <div>
                                <span>
                                  {
                                    report.region_name
                                  }
                                </span>

                                <h3>
                                  {
                                    report.title
                                  }
                                </h3>
                              </div>

                              <span
                                className={
                                  `household-status status-${report.report_status}`
                                }
                              >
                                {
                                  statusLabel(
                                    report.report_status
                                  )
                                }
                              </span>
                            </div>

                            <ReportProgress
                              report={report}
                            />
                          </div>
                        </article>
                      )
                    )}
                </div>
              </>
            )}
          </div>
        )}


        {/* ==================================================
            DETECT MY WASTE
            ================================================== */}

        {activeSection ===
          "detect" && (
          <div className="household-section">
            <div className="household-section-heading">
              <div>
                <span>
                  PERSONAL GUIDANCE
                </span>

                <h2>
                  Detect My Waste
                </h2>

                <p>
                  This feature is for your own
                  waste item. The image runs
                  through YOLO, then Household
                  RAG retrieves disposal and
                  safety guidance.
                </p>
              </div>
            </div>

            <div className="household-detection-layout">
              <section className="household-upload-card">
                <div className="household-upload-zone">
                  {detectionPreview ? (
                    <img
                      src={detectionPreview}
                      alt="Selected waste"
                    />
                  ) : (
                    <div>
                      <span>
                        ◎
                      </span>

                      <strong>
                        Add a waste photo
                      </strong>

                      <p>
                        Take a clear photo of
                        one or more supported
                        waste objects.
                      </p>
                    </div>
                  )}
                </div>

                <label className="household-file-button">
                  Choose / Take Photo

                  <input
                    type="file"
                    accept="image/png,image/jpeg,image/webp"
                    capture="environment"
                    onChange={
                      (event) =>
                        chooseDetectionFile(
                          event.target.files?.[0] ||
                          null
                        )
                    }
                  />
                </label>

                <button
                  type="button"
                  className="household-primary-button household-full-button"
                  onClick={
                    detectWaste
                  }
                  disabled={
                    detectionLoading
                  }
                >
                  {detectionLoading
                    ? "Detecting & Retrieving Guidance..."
                    : "Detect Waste ✦"}
                </button>

                {detectionMessage && (
                  <div className="household-inline-message">
                    {detectionMessage}
                  </div>
                )}
              </section>

              <section className="household-how-card">
                <span>
                  HOW IT WORKS
                </span>

                <div className="household-mini-flow">
                  <div>
                    <b>1</b>
                    <p>
                      Upload clear photo to detect
                      waste classes
                    </p>
                  </div>

                  <div>
                    <b>2</b>
                    <p>
                     Receive guidance on disposal
                    </p>
                  </div>

                  <div>
                    <b>3</b>
                    <p>
                      Get detail guidance on disposal
                    </p>
                  </div>

                  <div>
                    <b>4</b>
                    <p>
                      In case of no result, upload a clearer picture
                    </p>
                  </div>
                </div>

                <div className="household-flow-note">
                  <strong>
                    Important
                  </strong>

                  <p>
                    This personal detection does
                    not create a municipal cleanup
                    complaint. Use Report Public
                    Waste for dumped garbage.
                  </p>
                </div>
              </section>
            </div>

            {detectionResult && (
              <section className="household-detection-result">
                <div className="household-result-heading">
                  <div>
                    <span>
                      YOLO DETECTION
                    </span>

                    <h2>
                      Detected Waste
                    </h2>
                  </div>

                  <div className="household-model-pill">
                    {
                      detectionResult.architecture
                    }
                  </div>
                </div>

                <div className="household-detected-grid">
                  {(detectionResult.detected_objects || [])
                    .map(
                      (
                        object,
                        index
                      ) => (
                        <article
                          key={
                            `${object.model_class_id}-${index}`
                          }
                        >
                          <strong>
                            {
                              object.class_name
                            }
                          </strong>

                          <span>
                            Confidence
                            {" "}
                            {
                              Math.round(
                                Number(
                                  object.confidence
                                ) *
                                100
                              )
                            }
                            %
                          </span>

                          <small>
                            Threshold:
                            {" "}
                            {
                              Math.round(
                                Number(
                                  object.class_threshold ||
                                  detectionResult.global_confidence_threshold
                                ) *
                                100
                              )
                            }
                            %
                          </small>
                        </article>
                      )
                    )}
                </div>
              </section>
            )}

            {adviceResult && (
              <section className="household-advice-section">
                <div className="household-result-heading">
                  <div>
                    <span>
                      GEMINI + GROUNDED RAG GUIDANCE
                    </span>

                    <h2>
                      What should I do?
                    </h2>
                  </div>

                  <div className="household-advice-badges">
                    {adviceMode && (
                      <span>
                        {adviceMode}
                      </span>
                    )}

                    {(adviceResult.overall_priority ||
                      adviceResult.result?.overall_priority) && (
                      <span
                        className={
                          `priority-${adviceResult.overall_priority || adviceResult.result?.overall_priority}`
                        }
                      >
                        {
                          statusLabel(
                            adviceResult.overall_priority ||
                            adviceResult.result?.overall_priority
                          )
                        }
                      </span>
                    )}
                  </div>
                </div>

                <p className="household-advice-summary">
                  {
                    adviceResult.summary ||
                    adviceResult.result?.summary ||
                    "Household guidance prepared from the detected waste."
                  }
                </p>

                <div className="household-guidance-grid">
                  {guidance.map(
                    (
                      item,
                      index
                    ) => (
                      <article
                        className="household-guidance-card"
                        key={
                          `${item.model_class_id || index}`
                        }
                      >
                        <div className="household-guidance-title">
                          <div>
                            <span>
                              {
                                item.category_name ||
                                "Waste guidance"
                              }
                            </span>

                            <h3>
                              {
                                item.class_name ||
                                item.display_name ||
                                `Waste ${index + 1}`
                              }
                            </h3>
                          </div>

                          {item.priority && (
                            <span
                              className={
                                `household-guidance-priority priority-${item.priority}`
                              }
                            >
                              {
                                statusLabel(
                                  item.priority
                                )
                              }
                            </span>
                          )}
                        </div>

                        {item.overview && (
                          <p className="household-guidance-overview">
                            {
                              item.overview
                            }
                          </p>
                        )}

                        <GuidanceList
                          title="Immediate Action"
                          items={
                            item.immediate_actions
                          }
                        />

                        <GuidanceList
                          title="Separate It"
                          items={
                            item.segregation_steps
                          }
                        />

                        <GuidanceList
                          title="Preparation"
                          items={
                            item.preparation_steps
                          }
                        />

                        <GuidanceList
                          title="Temporary Storage"
                          items={
                            item.temporary_storage_steps
                          }
                        />

                        <GuidanceList
                          title="Disposal / Transfer"
                          items={
                            item.disposal_steps
                          }
                        />

                        <GuidanceList
                          title="Safety"
                          items={
                            item.safety_precautions
                          }
                        />

                        <GuidanceList
                          title="Do Not"
                          items={
                            item.prohibited_actions
                          }
                        />

                        <GuidanceList
                          title="Recycling Opportunity"
                          items={
                            item.recycling_opportunities
                          }
                        />

                        <GuidanceList
                          title="Benefits of Proper Disposal"
                          items={
                            item.benefits_of_proper_disposal
                          }
                        />

                        <GuidanceList
                          title="Consequences of Improper Disposal"
                          items={
                            item.harms_of_improper_disposal
                          }
                        />

                        <GuidanceList
                          title="Environmental Notes"
                          items={
                            item.environmental_notes
                          }
                        />
                      </article>
                    )
                  )}
                </div>

                {(adviceResult.limitations ||
                  adviceResult.result?.limitations)
                  ?.length > 0 && (
                  <div className="household-limitations">
                    <strong>
                      Current limitations
                    </strong>

                    <ul>
                      {(adviceResult.limitations ||
                        adviceResult.result?.limitations)
                        .map(
                          (
                            item,
                            index
                          ) => (
                            <li key={index}>
                              {item}
                            </li>
                          )
                        )}
                    </ul>
                  </div>
                )}
              </section>
            )}
          </div>
        )}


        {/* ==================================================
            GROUNDED FOLLOW-UP CHAT
            ================================================== */}

        {activeSection ===
          "detect" &&
          adviceResult &&
          detectionResult &&
          currentAdviceId && (
          <div className="household-section household-chat-section-wrap">
            <section className="household-chat-section">
              <div className="household-chat-heading">
                <div>
                  <span>
                    ASK ECOLENS
                  </span>

                  <h2>
                    Follow-up Waste Guidance
                  </h2>

                  <p>
                    Ask questions about the
                    waste detected in this
                    photo. Answers remain
                    grounded in the same
                    EcoLens RAG, safety and
                    facility information used
                    for your initial guidance.
                  </p>
                </div>

                <div className="household-chat-status">
                  <span className="household-chat-status-dot" />

                  Gemini + Grounded RAG
                </div>
              </div>

              <div className="household-chat-context">
                <strong>
                  Current detection
                </strong>

                <div>
                  {(detectionResult
                    .detected_objects ||
                    [])
                    .map(
                      (
                        object,
                        index
                      ) => (
                        <span
                          key={
                            `${object.model_class_id}-${index}`
                          }
                        >
                          {
                            object.class_name
                          }
                        </span>
                      )
                    )}
                </div>

                <small>
                  Start a new waste
                  detection if you want
                  to ask about a different
                  image.
                </small>
              </div>

              <div className="household-chat-window">
                {chatMessages.map(
                  (
                    message,
                    index
                  ) => (
                    <div
                      className={
                        `household-chat-row ${
                          message.role ===
                          "user"
                            ? "household-chat-row-user"
                            : "household-chat-row-assistant"
                        }`
                      }
                      key={
                        `${message.role}-${index}`
                      }
                    >
                      <div className="household-chat-avatar">
                        {
                          message.role ===
                          "user"
                            ? household
                                .full_name
                                ?.charAt(0)
                                ?.toUpperCase() ||
                              "U"
                            : "E"
                        }
                      </div>

                      <div className="household-chat-message-wrap">
                        <span className="household-chat-role">
                          {
                            message.role ===
                            "user"
                              ? "You"
                              : "EcoLens"
                          }
                        </span>

                        <div className="household-chat-bubble">
                          {
                            message.content
                          }
                        </div>

                        {message.groundingNote && (
                          <small className="household-chat-grounding-note">
                            {
                              message.groundingNote
                            }
                          </small>
                        )}
                      </div>
                    </div>
                  )
                )}

                {chatLoading && (
                  <div className="household-chat-row household-chat-row-assistant">
                    <div className="household-chat-avatar">
                      E
                    </div>

                    <div className="household-chat-message-wrap">
                      <span className="household-chat-role">
                        EcoLens
                      </span>

                      <div className="household-chat-bubble household-chat-typing">
                        <span />
                        <span />
                        <span />
                      </div>
                    </div>
                  </div>
                )}

                <div
                  ref={
                    chatEndRef
                  }
                />
              </div>

              {chatError && (
                <div className="household-chat-error">
                  {chatError}
                </div>
              )}

              <form
                className="household-chat-composer"
                onSubmit={
                  sendChatMessage
                }
              >
                <textarea
                  rows="2"
                  maxLength="1500"
                  placeholder="Ask a follow-up question about the detected waste..."
                  value={
                    chatInput
                  }
                  onChange={
                    (event) =>
                      setChatInput(
                        event
                          .target
                          .value
                      )
                  }
                  onKeyDown={
                    (event) => {
                      if (
                        event.key ===
                          "Enter" &&
                        !event.shiftKey
                      ) {
                        event.preventDefault();

                        sendChatMessage();
                      }
                    }
                  }
                  disabled={
                    chatLoading
                  }
                />

                <button
                  type="submit"
                  disabled={
                    chatLoading ||
                    !chatInput.trim()
                  }
                >
                  {
                    chatLoading
                      ? "Thinking..."
                      : "Send"
                  }

                  {!chatLoading && (
                    <span>
                      →
                    </span>
                  )}
                </button>
              </form>

              <div className="household-chat-footer-note">
                <span>
                  ✦
                </span>

                <p>
                  EcoLens uses the current
                  detection and verified
                  Household RAG context for
                  this conversation. Confirm
                  local disposal availability
                  whenever the guidance says
                  verification is required.
                </p>
              </div>
            </section>
          </div>
        )}


        {/* ==================================================
            REPORT PUBLIC WASTE
            ================================================== */}

        {activeSection ===
          "report" && (
          <div className="household-section">
            <div className="household-section-heading">
              <div>
                <span>
                  COMMUNITY CLEANUP REQUEST
                </span>

                <h2>
                  Report Public Waste
                </h2>

                <p>
                  Use this for dumped waste on a
                  road, footpath or other public
                  place. The report is routed by
                  ward to the responsible authority.
                </p>
              </div>
            </div>

            <div className="household-report-warning">
              <strong>
                No waste detection is required here.
              </strong>

              <span>
                The authority needs evidence and
                the exact cleanup location, not a
                YOLO classification of the complaint photo.
              </span>
            </div>

            <form
              className="household-report-form-layout"
              onSubmit={
                submitPublicReport
              }
            >
              <section className="household-report-form-card">
                <label className="household-form-field">
                  <span>
                    Report title *
                  </span>

                  <input
                    type="text"
                    maxLength="200"
                    required
                    placeholder="Example: Dumped garbage beside the road"
                    value={
                      reportForm.title
                    }
                    onChange={
                      (event) =>
                        setReportForm(
                          (previous) => ({
                            ...previous,
                            title:
                              event.target.value,
                          })
                        )
                    }
                  />
                </label>

                <label className="household-form-field">
                  <span>
                    Short description *
                  </span>

                  <textarea
                    rows="4"
                    required
                    placeholder="Describe what you can see and why this public place needs cleanup."
                    value={
                      reportForm.description
                    }
                    onChange={
                      (event) =>
                        setReportForm(
                          (previous) => ({
                            ...previous,
                            description:
                              event.target.value,
                          })
                        )
                    }
                  />
                </label>

                <label className="household-form-field">
                  <span>
                    Local area / ward *
                  </span>

                  <select
                    required
                    value={
                      reportForm.location_region_id
                    }
                    onChange={
                      (event) =>
                        setReportForm(
                          (previous) => ({
                            ...previous,
                            location_region_id:
                              event.target.value,
                          })
                        )
                    }
                  >
                    <option value="">
                      Select location
                    </option>

                    {locationOptions.map(
                      (location) => (
                        <option
                          key={
                            location.location_region_id
                          }
                          value={
                            location.location_region_id
                          }
                        >
                          {
                            location.location_name
                          }
                          {
                            location.location_name !==
                            location.ward_name
                              ? ` — ${location.ward_name}`
                              : ""
                          }
                        </option>
                      )
                    )}
                  </select>
                </label>

                <label className="household-form-field">
                  <span>
                    Address / landmark
                  </span>

                  <input
                    type="text"
                    placeholder="Example: Beside community market, Road 4"
                    value={
                      reportForm.address_text
                    }
                    onChange={
                      (event) =>
                        setReportForm(
                          (previous) => ({
                            ...previous,
                            address_text:
                              event.target.value,
                          })
                        )
                    }
                  />
                </label>

                <div className="household-form-field">
                  <span>
                    Exact GPS location *
                  </span>

                  <button
                    type="button"
                    className="household-location-button"
                    onClick={
                      useCurrentLocation
                    }
                    disabled={
                      locationLoading
                    }
                  >
                    {locationLoading
                      ? "Getting location..."
                      : "⌖ Use My Current Location"}
                  </button>

                  <div className="household-coordinate-grid">
                    <input
                      type="number"
                      step="0.0000001"
                      placeholder="Latitude"
                      required
                      value={
                        reportForm.latitude
                      }
                      onChange={
                        (event) =>
                          setReportForm(
                            (previous) => ({
                              ...previous,
                              latitude:
                                event.target.value,
                            })
                          )
                      }
                    />

                    <input
                      type="number"
                      step="0.0000001"
                      placeholder="Longitude"
                      required
                      value={
                        reportForm.longitude
                      }
                      onChange={
                        (event) =>
                          setReportForm(
                            (previous) => ({
                              ...previous,
                              longitude:
                                event.target.value,
                            })
                          )
                      }
                    />
                  </div>
                </div>

                <label className="household-form-field">
                  <span>
                    Public waste photo *
                  </span>

                  <input
                    type="file"
                    accept="image/png,image/jpeg,image/webp"
                    capture="environment"
                    required
                    onChange={
                      (event) =>
                        chooseReportFile(
                          event.target.files?.[0] ||
                          null
                        )
                    }
                  />
                </label>

                {reportPreview && (
                  <img
                    className="household-report-preview"
                    src={reportPreview}
                    alt="Public waste report preview"
                  />
                )}

                {reportError && (
                  <div className="household-error-message">
                    {reportError}
                  </div>
                )}

                {reportMessage && (
                  <div className="household-success-message">
                    {reportMessage}
                  </div>
                )}

                <button
                  type="submit"
                  className="household-primary-button household-full-button"
                  disabled={
                    reportLoading
                  }
                >
                  {reportLoading
                    ? "Submitting Report..."
                    : "Submit Public Waste Report"}
                </button>
              </section>

              <section className="household-report-map-card">
                <div>
                  <span>
                    LOCATION PREVIEW
                  </span>

                  <h3>
                    Cleanup Location
                  </h3>

                  <p>
                    The employee will use these
                    coordinates to reach the
                    reported waste site.
                  </p>
                </div>

                <GoogleMap
                  latitude={
                    reportForm.latitude
                  }
                  longitude={
                    reportForm.longitude
                  }
                />

                {reportForm.latitude &&
                  reportForm.longitude && (
                  <a
                    className="household-map-link"
                    href={
                      `https://www.google.com/maps?q=${reportForm.latitude},${reportForm.longitude}`
                    }
                    target="_blank"
                    rel="noreferrer"
                  >
                    Open in Google Maps ↗
                  </a>
                )}
              </section>
            </form>
          </div>
        )}


        {/* ==================================================
            MY REPORTS
            ================================================== */}

        {activeSection ===
          "reports" && (
          <div className="household-section">
            <div className="household-section-heading">
              <div>
                <span>
                  REPORT TRACKING
                </span>

                <h2>
                  My Public Waste Reports
                </h2>

                <p>
                  Follow each cleanup from
                  submission to authority assignment,
                  field work and completion.
                </p>
              </div>
            </div>

            <div className="household-report-list">
              {reports.length ===
                0 && (
                <div className="household-empty-state">
                  You have not submitted any
                  public waste reports yet.
                </div>
              )}

              {reports.map(
                (report) => (
                  <article
                    className="household-report-card household-report-card-full"
                    key={
                      report.report_id
                    }
                  >
                    <div className="household-report-image">
                      {report.before_image_path ? (
                        <img
                          src={
                            mediaUrl(
                              report.before_image_path
                            )
                          }
                          alt="Reported public waste"
                        />
                      ) : (
                        <span>
                          📷
                        </span>
                      )}
                    </div>

                    <div className="household-report-body">
                      <div className="household-report-top">
                        <div>
                          <span>
                            {
                              report.region_name
                            }
                          </span>

                          <h3>
                            {report.title}
                          </h3>
                        </div>

                        <span
                          className={
                            `household-status status-${report.report_status}`
                          }
                        >
                          {
                            statusLabel(
                              report.report_status
                            )
                          }
                        </span>
                      </div>

                      <p>
                        {
                          report.description
                        }
                      </p>

                      <div className="household-report-meta">
                        <span>
                          ⌖{" "}
                          {
                            report.address_text ||
                            "GPS location provided"
                          }
                        </span>

                        <span>
                          ◷{" "}
                          {
                            formatDate(
                              report.submitted_at
                            )
                          }
                        </span>

                        <span>
                          Authority:
                          {" "}
                          {
                            report.authority_name ||
                            "Awaiting ward coverage"
                          }
                        </span>

                        {report.employee_name && (
                          <span>
                            Employee:
                            {" "}
                            {
                              report.employee_name
                            }
                          </span>
                        )}
                      </div>

                      <ReportProgress
                        report={report}
                      />

                      <div className="household-report-actions">
                        {report.latitude &&
                          report.longitude && (
                          <a
                            className="household-secondary-button"
                            href={
                              `https://www.google.com/maps?q=${report.latitude},${report.longitude}`
                            }
                            target="_blank"
                            rel="noreferrer"
                          >
                            Open Location ↗
                          </a>
                        )}

                        {report.after_image_path && (
                          <a
                            className="household-secondary-button"
                            href={
                              mediaUrl(
                                report.after_image_path
                              )
                            }
                            target="_blank"
                            rel="noreferrer"
                          >
                            View Cleanup Proof ↗
                          </a>
                        )}
                      </div>
                    </div>
                  </article>
                )
              )}
            </div>
          </div>
        )}


        {/* ==================================================
            DETECTION HISTORY
            ================================================== */}

        {activeSection ===
          "history" && (
          <div className="household-section">
            <div className="household-section-heading">
              <div>
                <span>
                  PERSONAL HISTORY
                </span>

                <h2>
                  Previous Waste Detections
                </h2>

                <p>
                  These are personal detection
                  sessions and advice results.
                  They are separate from public
                  cleanup reports.
                </p>
              </div>
            </div>

            <div className="household-history-grid">
              {detections.length ===
                0 && (
                <div className="household-empty-state">
                  No personal detections yet.
                </div>
              )}

              {detections.map(
                (detection) => (
                  <article
                    className="household-history-card"
                    key={
                      detection.detection_session_id
                    }
                  >
                    <div className="household-history-image">
                      {detection.annotated_image_path ||
                      detection.stored_image_path ? (
                        <img
                          src={
                            mediaUrl(
                              detection.annotated_image_path ||
                              detection.stored_image_path
                            )
                          }
                          alt="Detection history"
                        />
                      ) : (
                        <span>
                          ◎
                        </span>
                      )}
                    </div>

                    <div>
                      <div className="household-history-top">
                        <span>
                          {
                            formatDate(
                              detection.created_at
                            )
                          }
                        </span>

                        {detection.priority_level && (
                          <span
                            className={
                              `household-history-priority priority-${detection.priority_level}`
                            }
                          >
                            {
                              statusLabel(
                                detection.priority_level
                              )
                            }
                          </span>
                        )}
                      </div>

                      <h3>
                        {(detection.detected_objects || [])
                          .map(
                            (object) =>
                              object.display_name ||
                              object.class_name
                          )
                          .join(", ") ||
                          "No class detected"}
                      </h3>

                      <p>
                        {
                          detection.summary ||
                          "Detection completed."
                        }
                      </p>

                      <div className="household-history-tags">
                        {(detection.detected_objects || [])
                          .map(
                            (object) => (
                              <span
                                key={
                                  object.detected_object_id
                                }
                              >
                                {
                                  object.display_name ||
                                  object.class_name
                                }
                                {" "}
                                {
                                  Math.round(
                                    Number(
                                      object.confidence
                                    ) *
                                    100
                                  )
                                }
                                %
                              </span>
                            )
                          )}
                      </div>

                      <small>
                        {
                          detection.architecture
                        }
                        {" • "}
                        {
                          detection.gemini_model
                            ? `Gemini: ${detection.gemini_model}`
                            : "Grounded offline formatting"
                        }
                      </small>
                    </div>
                  </article>
                )
              )}
            </div>
          </div>
        )}


        {/* ==================================================
            PROFILE
            ================================================== */}

        {activeSection ===
          "profile" && (
          <div className="household-section">
            <div className="household-profile-card">
              <div className="household-large-avatar">
                {
                  household.full_name
                    ?.charAt(0)
                    ?.toUpperCase()
                }
              </div>

              <h2>
                {household.full_name}
              </h2>

              <p>
                Household Account
              </p>

              <div className="household-profile-grid">
                <div>
                  <span>
                    Email
                  </span>

                  <strong>
                    {household.email}
                  </strong>
                </div>

                <div>
                  <span>
                    Phone
                  </span>

                  <strong>
                    {household.phone ||
                      "Not provided"}
                  </strong>
                </div>

                <div>
                  <span>
                    Local Area
                  </span>

                  <strong>
                    {household.locality_name ||
                      "Not set"}
                  </strong>
                </div>

                <div>
                  <span>
                    Ward
                  </span>

                  <strong>
                    {household.ward_name ||
                      "Not set"}
                  </strong>
                </div>

                <div className="household-profile-wide">
                  <span>
                    Address
                  </span>

                  <strong>
                    {household.address_text ||
                      "Not provided"}
                  </strong>
                </div>
              </div>
            </div>
          </div>
        )}
      </section>
    </main>
  );
}


export default HouseholdDashboard;