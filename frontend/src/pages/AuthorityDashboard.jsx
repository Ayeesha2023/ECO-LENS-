import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  useNavigate,
} from "react-router-dom";

import logo from "../assets/ecolens-logo.png";

import {
  apiRequest,
} from "../services/api";

import "../styles/authority-dashboard.css";

import AuthorityEmployeeTools
  from "../components/AuthorityEmployeeTools";

import AuthorityCleanupVerification
  from "../components/AuthorityCleanupVerification";


const menuItems = [
  {
    id: "overview",
    icon: "⌂",
    label: "Overview",
  },
  {
    id: "reports",
    icon: "▤",
    label: "Waste Reports",
  },
  {
    id: "map",
    icon: "⌖",
    label: "Map",
  },
  {
    id: "employees",
    icon: "♙",
    label: "Employees",
  },
  {
    id: "assignments",
    icon: "✓",
    label: "Assignments",
  },
  {
    id: "verification",
    icon: "✓",
    label: "Cleanup Verification",
  },
  {
    id: "analytics",
    icon: "▥",
    label: "Analytics & AI",
  },
  {
    id: "coverage",
    icon: "◎",
    label: "Coverage Wards",
  },
];


function formatDate(
  value
) {

  if (!value) {
    return "—";
  }

  const date =
    new Date(value);

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


function statusLabel(
  status
) {

  const labels = {

    submitted:
      "New Report",

    under_review:
      "Under Review",

    assigned:
      "Assigned",

    accepted:
      "Accepted",

    in_progress:
      "In Progress",

    completed:
      "Completed",

    rejected:
      "Rejected",

    cancelled:
      "Cancelled",

    active:
      "Active",

    inactive:
      "Inactive",

    on_leave:
      "On Leave",

    low:
      "Low",

    medium:
      "Medium",

    high:
      "High",

    urgent:
      "Urgent",

    critical:
      "Critical",
  };


  return (
    labels[status] ||
    String(
      status || ""
    )
      .replaceAll(
        "_",
        " "
      )
      .replace(
        /\b\w/g,
        (letter) =>
          letter.toUpperCase()
      )
  );
}


function GoogleMap({
  latitude,
  longitude,
}) {

  if (
    latitude === null ||
    latitude === undefined ||
    longitude === null ||
    longitude === undefined
  ) {

    return (
      <div className="authority-empty-map">

        <span>
          ⌖
        </span>

        <p>
          This report does not have
          an exact map location yet.
        </p>

      </div>
    );
  }


  const mapUrl =
    `https://www.google.com/maps?q=${latitude},${longitude}&output=embed`;


  return (
    <iframe
      className="authority-map-frame"
      src={mapUrl}
      title="Reported waste location"
      loading="lazy"
      referrerPolicy="no-referrer-when-downgrade"
    />
  );
}


function StatBarChart({
  title,
  subtitle,
  items,
  suffix = "",
  emptyMessage = "No data is available for this comparison yet.",
  scaleMax = null,
}) {
  const safeItems =
    Array.isArray(items)
      ? items
      : [];

  const hasData =
    safeItems.some(
      (item) =>
        Number(item.value || 0) > 0
    );

  const maxValue =
    Number(scaleMax) > 0
      ? Number(scaleMax)
      : Math.max(
          1,
          ...safeItems.map(
            (item) => Number(item.value || 0)
          )
        );

  return (
    <section className="authority-chart-card authority-horizontal-chart-card">
      <div className="authority-chart-heading">
        <div>
          <span>STATISTICAL VIEW</span>
          <h3>{title}</h3>
        </div>
        {subtitle && <small>{subtitle}</small>}
      </div>

      {!hasData ? (
        <div className="authority-chart-empty">
          {emptyMessage}
        </div>
      ) : (
        <div className="authority-horizontal-chart">
          {safeItems.map((item) => {
            const numericValue = Number(item.value || 0);
            const width = Math.max(
              numericValue > 0 ? 3 : 0,
              Math.min(100, (numericValue / maxValue) * 100)
            );

            return (
              <div
                className="authority-horizontal-row"
                key={item.label}
              >
                <div className="authority-horizontal-row-top">
                  <span>{item.label}</span>
                  <strong>
                    {Number.isInteger(numericValue)
                      ? numericValue
                      : numericValue.toFixed(1)}
                    {suffix}
                  </strong>
                </div>

                <div className="authority-horizontal-track">
                  <div
                    className="authority-horizontal-fill"
                    style={{ width: `${width}%` }}
                    title={`${item.label}: ${numericValue}${suffix}`}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}


function WasteCompositionChart({
  items,
}) {
  const safeItems = (Array.isArray(items) ? items : [])
    .filter((item) => Number(item.value || 0) > 0);

  const total = safeItems.reduce(
    (sum, item) => sum + Number(item.value || 0),
    0
  );

  const colors = [
    "#0b6b45",
    "#5b9d2d",
    "#9fbd3e",
    "#d0a12d",
    "#2f7f82",
    "#745aa8",
    "#b46b45",
    "#5c7587",
  ];

  let runningPercent = 0;
  const gradientParts = safeItems.map((item, index) => {
    const percent = total > 0
      ? (Number(item.value || 0) / total) * 100
      : 0;
    const start = runningPercent;
    runningPercent += percent;
    return `${colors[index % colors.length]} ${start}% ${runningPercent}%`;
  });

  return (
    <section className="authority-chart-card authority-pie-chart-card">
      <div className="authority-chart-heading">
        <div>
          <span>STATISTICAL VIEW</span>
          <h3>Waste Composition</h3>
        </div>
        <small>Share of verified waste by major category</small>
      </div>

      {total <= 0 ? (
        <div className="authority-chart-empty">
          No verified category-level cleanup data is available for this period.
        </div>
      ) : (
        <div className="authority-pie-layout">
          <div
            className="authority-donut-chart"
            style={{
              background: `conic-gradient(${gradientParts.join(", ")})`,
            }}
            aria-label="Waste composition pie chart"
          >
            <div className="authority-donut-center">
              <strong>{total.toFixed(1)} kg</strong>
              <span>verified waste</span>
            </div>
          </div>

          <div className="authority-pie-legend">
            {safeItems.map((item, index) => {
              const value = Number(item.value || 0);
              const percent = total > 0
                ? (value / total) * 100
                : 0;

              return (
                <div
                  className="authority-pie-legend-item"
                  key={item.label}
                >
                  <span
                    className="authority-pie-swatch"
                    style={{
                      backgroundColor:
                        colors[index % colors.length],
                    }}
                  />

                  <div>
                    <strong>{item.label}</strong>
                    <small>
                      {value.toFixed(1)} kg · {percent.toFixed(1)}%
                    </small>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </section>
  );
}


function AuthorityDashboard() {

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


  const [
    selectedReport,
    setSelectedReport,
  ] = useState(null);


  const [
    reportLoading,
    setReportLoading,
  ] = useState(false);


  const [
    reportFilter,
    setReportFilter,
  ] = useState("all");


  const [
    assignmentOpen,
    setAssignmentOpen,
  ] = useState(false);


  const [
    assignmentForm,
    setAssignmentForm,
  ] = useState({
    employee_id: "",
    priority: "medium",
    assignment_notes: "",
  });


  const [
    assignmentMessage,
    setAssignmentMessage,
  ] = useState("");


  const [
    assigning,
    setAssigning,
  ] = useState(false);


  const [
    detailedAnalytics,
    setDetailedAnalytics,
  ] = useState(null);


  const [
    detailedAnalyticsError,
    setDetailedAnalyticsError,
  ] = useState("");


  const [
    ragResult,
    setRagResult,
  ] = useState(null);


  const [
    ragLoading,
    setRagLoading,
  ] = useState(false);


  const [
    ragError,
    setRagError,
  ] = useState("");


  const [
    aiLanguage,
    setAiLanguage,
  ] = useState("en");


  const [
    geminiResult,
    setGeminiResult,
  ] = useState(null);


  const [
    geminiLoading,
    setGeminiLoading,
  ] = useState(false);


  const [
    geminiError,
    setGeminiError,
  ] = useState("");


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
            "/api/authority/dashboard/bootstrap"
          );


        setData(
          response
        );


      } catch (requestError) {

        setError(
          requestError.message
        );


        if (
          requestError.status === 401 ||
          requestError.status === 403
        ) {

          setTimeout(
            () => {
              navigate(
                "/login"
              );
            },
            1200
          );
        }


      } finally {

        setLoading(false);
      }
    };


  const loadDetailedAnalytics =
    async (authorityId = null) => {
      const resolvedAuthorityId =
        authorityId ||
        data?.authority?.authority_id;

      if (!resolvedAuthorityId) {
        return;
      }

      const today = new Date();
      const startDate =
        `${today.getFullYear()}-01-01`;
      const endDate =
        today.toISOString().slice(0, 10);

      try {
        setDetailedAnalyticsError("");

        const response =
          await apiRequest(
            `/api/authority/${resolvedAuthorityId}/analytics?start_date=${startDate}&end_date=${endDate}`
          );

        setDetailedAnalytics(
          response.analytics || null
        );

      } catch (requestError) {
        setDetailedAnalytics(null);
        setDetailedAnalyticsError(
          requestError.message
        );
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
      const authorityId =
        data?.authority?.authority_id;

      if (authorityId) {
        loadDetailedAnalytics(
          authorityId
        );
      }
    },
    [data?.authority?.authority_id]
  );


  // ========================================================
  // FILTERED REPORTS
  // ========================================================

  const filteredReports =
    useMemo(
      () => {

        if (!data) {
          return [];
        }


        if (
          reportFilter ===
          "all"
        ) {

          return (
            data.reports || []
          );
        }


        return (
          data.reports || []
        ).filter(
          (report) =>
            report.report_status ===
            reportFilter
        );

      },
      [
        data,
        reportFilter,
      ]
    );


  const reportChartData = useMemo(
    () => {
      const rows = data?.reports || [];
      const counts = {
        submitted: 0,
        under_review: 0,
        assigned: 0,
        accepted: 0,
        in_progress: 0,
        completed: 0,
        rejected: 0,
      };

      rows.forEach((report) => {
        const key = report.report_status;
        if (Object.hasOwn(counts, key)) {
          counts[key] += 1;
        }
      });

      return [
        { label: "New", value: counts.submitted },
        { label: "Under Review", value: counts.under_review },
        { label: "Assigned", value: counts.assigned + counts.accepted },
        { label: "In Progress", value: counts.in_progress },
        { label: "Completed", value: counts.completed },
        { label: "Rejected", value: counts.rejected },
      ];
    },
    [data]
  );


  const assignmentChartData = useMemo(
    () => {
      const rows = data?.assignments || [];
      const counts = {
        assigned: 0,
        accepted: 0,
        in_progress: 0,
        completed: 0,
        cancelled: 0,
      };

      rows.forEach((assignment) => {
        const key = assignment.assignment_status;
        if (Object.hasOwn(counts, key)) {
          counts[key] += 1;
        }
      });

      return [
        { label: "Assigned", value: counts.assigned },
        { label: "Accepted", value: counts.accepted },
        { label: "In Progress", value: counts.in_progress },
        { label: "Completed", value: counts.completed },
        { label: "Cancelled", value: counts.cancelled },
      ];
    },
    [data]
  );


  const wasteCategoryChartData = useMemo(
    () => {
      const rows =
        detailedAnalytics?.waste
          ?.category_breakdown || [];

      return rows.map(
        (row) => ({
          label:
            row.category_name ||
            row.category_code ||
            "Unmapped Waste",
          value: Number(
            row.weight_kg || 0
          ),
        })
      );
    },
    [detailedAnalytics]
  );


  const wasteOutcomeChartData = useMemo(
    () => {
      const waste =
        detailedAnalytics?.waste || {};

      return [
        {
          label: "Recycled",
          value: Number(
            waste.recycled_kg || 0
          ),
        },
        {
          label: "Composted",
          value: Number(
            waste.composted_kg || 0
          ),
        },
        {
          label: "Properly Disposed",
          value: Number(
            waste.properly_disposed_kg || 0
          ),
        },
        {
          label: "Hazardous",
          value: Number(
            waste.hazardous_kg || 0
          ),
        },
      ];
    },
    [detailedAnalytics]
  );


  const performanceChartData = useMemo(
    () => {
      const indicators =
        detailedAnalytics?.indicators || {};

      return [
        {
          label: "Report Completion",
          value: Number(
            indicators.report_completion_rate_percent || 0
          ),
        },
        {
          label: "Unresolved Reports",
          value: Number(
            indicators.unresolved_report_rate_percent || 0
          ),
        },
        {
          label: "Recycling Share",
          value: Number(
            indicators.recycling_share_percent || 0
          ),
        },
        {
          label: "Compostable Share",
          value: Number(
            indicators.compostable_share_percent || 0
          ),
        },
        {
          label: "Hazardous Share",
          value: Number(
            indicators.hazardous_share_percent || 0
          ),
        },
        {
          label: "Overdue Assignments",
          value: Number(
            indicators.overdue_assignment_rate_percent || 0
          ),
        },
      ];
    },
    [detailedAnalytics]
  );



  // ========================================================
  // REPORT DETAIL
  // ========================================================

  const openReport =
    async (
      reportId
    ) => {

      try {

        setReportLoading(
          true
        );


        const response =
          await apiRequest(
            `/api/authority/dashboard/reports/${reportId}`
          );


        setSelectedReport(
          response.report
        );


      } catch (requestError) {

        alert(
          requestError.message
        );


      } finally {

        setReportLoading(
          false
        );
      }
    };


  // ========================================================
  // ASSIGN EMPLOYEE
  // ========================================================

  const openAssignment =
    (
      report
    ) => {

      setSelectedReport(
        report
      );

      setAssignmentMessage(
        ""
      );

      setAssignmentForm({
        employee_id: "",
        priority: "medium",
        assignment_notes: "",
      });

      setAssignmentOpen(
        true
      );
    };


  const submitAssignment =
    async (
      event
    ) => {

      event.preventDefault();


      if (
        !selectedReport
      ) {
        return;
      }


      try {

        setAssigning(
          true
        );

        setAssignmentMessage(
          ""
        );


        const response =
          await apiRequest(
            `/api/authority/dashboard/reports/${selectedReport.report_id}/assign`,
            {
              method: "POST",

              body:
                JSON.stringify(
                  {
                    employee_id:
                      Number(
                        assignmentForm.employee_id
                      ),

                    priority:
                      assignmentForm.priority,

                    assignment_notes:
                      assignmentForm.assignment_notes,
                  }
                ),
            }
          );


        setAssignmentMessage(
          response.message
        );


        await loadDashboard();


        setTimeout(
          () => {

            setAssignmentOpen(
              false
            );

          },
          900
        );


      } catch (requestError) {

        setAssignmentMessage(
          requestError.message
        );


      } finally {

        setAssigning(
          false
        );
      }
    };


  // ========================================================
  // AUTHORITY RAG
  // ========================================================

  const generateRagAdvice =
    async () => {

    if (!data) {
      return;
    }


    const authorityId =
      data.authority
        .authority_id;


    const today =
      new Date();


    const startDate =
      `${today.getFullYear()}-01-01`;


    const endDate =
      today
        .toISOString()
        .slice(
          0,
          10
        );


    try {

      setRagLoading(
        true
      );

      setRagError(
        ""
      );

      setRagResult(
        null
      );


      const response =
        await apiRequest(
          `/api/authority/${authorityId}/advice`,
          {
            method: "POST",

            body:
              JSON.stringify(
                {

                  // IMPORTANT:
                  // These names match the
                  // existing Authority RAG API.

                  start_date:
                    startDate,

                  end_date:
                    endDate,

                  language:
                    "en",
                }
              ),
          }
        );


      console.log(
        "Authority RAG response:",
        response
      );


      setRagResult(
        response.result ||
        response
      );


    } catch (
      requestError
    ) {

      console.error(
        "Authority RAG error:",
        requestError
      );


      setRagError(
        requestError.message
      );


    } finally {

      setRagLoading(
        false
      );
    }
  };


  const getAuthorityAnalyticsPeriod = () => {
    const today = new Date();

    return {
      startDate: `${today.getFullYear()}-01-01`,
      endDate: today.toISOString().slice(0, 10),
    };
  };


  const generateGeminiAdvice =
    async (languageOverride = aiLanguage) => {

      if (!data) {
        return;
      }

      const authorityId =
        data.authority.authority_id;

      const {
        startDate,
        endDate,
      } = getAuthorityAnalyticsPeriod();

      try {
        setAiLanguage(languageOverride);
        setGeminiLoading(true);
        setGeminiError("");
        setChatError("");
        setChatMessages([]);

        const response =
          await apiRequest(
            `/api/authority/${authorityId}/advice/gemini`,
            {
              method: "POST",
              body: JSON.stringify({
                start_date: startDate,
                end_date: endDate,
                language: languageOverride,
              }),
            }
          );

        setGeminiResult(
          response.result || response
        );

      } catch (requestError) {
        setGeminiError(
          requestError.message
        );

      } finally {
        setGeminiLoading(false);
      }
    };


  const switchAiLanguage =
    async (nextLanguage) => {
      setAiLanguage(nextLanguage);

      if (geminiResult) {
        await generateGeminiAdvice(
          nextLanguage
        );
      }
    };


  const sendAuthorityChat =
    async (event) => {

      event.preventDefault();

      const message =
        chatInput.trim();

      if (!message || !data) {
        return;
      }

      const authorityId =
        data.authority.authority_id;

      const {
        startDate,
        endDate,
      } = getAuthorityAnalyticsPeriod();

      const nextHistory = [
        ...chatMessages,
        {
          role: "user",
          content: message,
        },
      ];

      setChatMessages(nextHistory);
      setChatInput("");
      setChatLoading(true);
      setChatError("");

      try {
        const response =
          await apiRequest(
            `/api/authority/${authorityId}/advice/chat`,
            {
              method: "POST",
              body: JSON.stringify({
                start_date: startDate,
                end_date: endDate,
                language: aiLanguage,
                message,
                conversation_history:
                  chatMessages,
                initial_result:
                  geminiResult,
              }),
            }
          );

        const answer =
          response.result?.answer ||
          response.answer ||
          "";

        setChatMessages((previous) => [
          ...previous,
          {
            role: "assistant",
            content: answer,
          },
        ]);

      } catch (requestError) {
        setChatError(
          requestError.message
        );

      } finally {
        setChatLoading(false);
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


  // ========================================================
  // LOADING / ERROR
  // ========================================================

  if (loading) {

    return (
      <main className="authority-loading-page">

        <img
          src={logo}
          alt="EcoLens"
        />

        <p>
          Loading Community Authority
          dashboard...
        </p>

      </main>
    );
  }


  if (
    error ||
    !data
  ) {

    return (
      <main className="authority-loading-page">

        <img
          src={logo}
          alt="EcoLens"
        />

        <p>
          {error ||
            "Dashboard could not be loaded."}
        </p>

      </main>
    );
  }


  const {
    authority,
    summary,
    reports,
    employees,
    assignments,
    coverage,
    analytics,
  } = data;


  // ========================================================
  // REPORT LIST COMPONENT
  // ========================================================

  const reportList = (

    <div className="authority-report-list">

      {filteredReports.length ===
        0 && (

        <div className="authority-empty-state">

          No reports match this
          filter.

        </div>
      )}


      {filteredReports.map(
        (report) => (

          <article
            className="authority-report-card"
            key={
              report.report_id
            }
          >

            <div className="report-photo-placeholder">

              <span>
                📷
              </span>

              <small>
                Report #
                {report.report_id}
              </small>

            </div>


            <div className="report-card-content">

              <div className="report-card-heading">

                <div>

                  <span className="report-ward">
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
                    `report-status status-${report.report_status}`
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


              <div className="report-meta">

                <span>
                  ⌖{" "}
                  {report.address_text ||
                    "Location supplied by map"}
                </span>

                <span>
                  ◷{" "}
                  {
                    formatDate(
                      report.submitted_at
                    )
                  }
                </span>

              </div>


              <div className="report-actions">

                <button
                  type="button"

                  className="secondary-dashboard-button"

                  onClick={() =>
                    openReport(
                      report.report_id
                    )
                  }
                >
                  View Report
                </button>


                {report.latitude &&
                  report.longitude && (

                  <a
                    className="map-link-button"

                    href={
                      `https://www.google.com/maps?q=${report.latitude},${report.longitude}`
                    }

                    target="_blank"

                    rel="noreferrer"
                  >
                    Open Map ↗
                  </a>

                )}


                {Number(
                  report.active_assignment_count
                ) === 0 &&

                  ![
                    "completed",
                    "rejected",
                    "cancelled",
                  ].includes(
                    report.report_status
                  ) && (

                  <button
                    type="button"

                    className="primary-dashboard-button"

                    onClick={() =>
                      openAssignment(
                        report
                      )
                    }
                  >
                    Assign Employee
                  </button>

                )}

              </div>

            </div>

          </article>

        )
      )}

    </div>
  );


  // ========================================================
  // UI
  // ========================================================

  return (

    <main className="authority-dashboard">


      {/* ====================================================
          SIDEBAR
          ==================================================== */}

      <aside className="authority-sidebar">

        <div>

          <div className="authority-sidebar-brand">

            <img
              src={logo}
              alt="EcoLens"
            />

            <div>

              <strong>
                EcoLens
              </strong>

              <span>
                Authority
              </span>

            </div>

          </div>


          <nav className="authority-nav">

            {menuItems.map(
              (item) => (

                <button
                  type="button"

                  key={
                    item.id
                  }

                  className={
                    activeSection ===
                    item.id

                      ? "authority-nav-item active"

                      : "authority-nav-item"
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


        <div className="authority-sidebar-bottom">

          <div className="authority-profile-mini">

            <div className="profile-initial">

              {
                authority.full_name
                  ?.charAt(0)
                  ?.toUpperCase()
              }

            </div>


            <div>

              <strong>
                {
                  authority.full_name
                }
              </strong>

              <span>
                {
                  authority.organization_name ||
                  "Community Authority"
                }
              </span>

            </div>

          </div>


          <button
            type="button"

            className="authority-logout"

            onClick={
              handleLogout
            }
          >
            Log Out
          </button>

        </div>

      </aside>


      {/* ====================================================
          MAIN AREA
          ==================================================== */}

      <section className="authority-main">


        {/* TOP BAR */}

        <header className="authority-topbar">

          <div>

            <span className="authority-page-label">
              COMMUNITY OPERATIONS
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


          <div className="coverage-top-pill">

            <span>
              ◎
            </span>

            {coverage.length}
            {" "}
            Ward
            {coverage.length ===
              1
              ? ""
              : "s"}

          </div>

        </header>


        {/* ==================================================
            OVERVIEW
            ================================================== */}

        {activeSection ===
          "overview" && (

          <div className="dashboard-section">

            <div className="authority-welcome">

              <div>

                <span>
                  ECOLENS COMMUNITY CONTROL
                </span>

                <h2>
                  Welcome back,
                  {" "}
                  {
                    authority.full_name
                  }.
                </h2>

                <p>
                  Monitor public waste
                  reports, coordinate your
                  field team and understand
                  conditions across your
                  covered wards.
                </p>

              </div>


              <div className="authority-welcome-mark">
                ◎
              </div>

            </div>


            <div className="authority-stat-grid">

              <div className="authority-stat-card">

                <span>
                  New Reports
                </span>

                <strong>
                  {
                    summary.new_reports
                  }
                </strong>

                <small>
                  Awaiting authority action
                </small>

              </div>


              <div className="authority-stat-card">

                <span>
                  Open Reports
                </span>

                <strong>
                  {
                    summary.open_reports
                  }
                </strong>

                <small>
                  Not completed yet
                </small>

              </div>


              <div className="authority-stat-card">

                <span>
                  Active Jobs
                </span>

                <strong>
                  {
                    summary.active_assignments
                  }
                </strong>

                <small>
                  Assigned to employees
                </small>

              </div>


              <div className="authority-stat-card">

                <span>
                  Active Employees
                </span>

                <strong>
                  {
                    summary.active_employees
                  }
                </strong>

                <small>
                  Available field workforce
                </small>

              </div>

            </div>


            <div className="overview-two-column">

              <section className="dashboard-panel">

                <div className="panel-heading">

                  <div>

                    <span>
                      RECENT ACTIVITY
                    </span>

                    <h2>
                      Latest Waste Reports
                    </h2>

                  </div>


                  <button
                    type="button"

                    className="text-dashboard-button"

                    onClick={() =>
                      setActiveSection(
                        "reports"
                      )
                    }
                  >
                    View all →
                  </button>

                </div>


                <div className="mini-report-list">

                  {
                    reports
                      .slice(
                        0,
                        5
                      )
                      .map(
                        (report) => (

                          <button
                            type="button"

                            className="mini-report"

                            key={
                              report.report_id
                            }

                            onClick={() =>
                              openReport(
                                report.report_id
                              )
                            }
                          >

                            <div className="mini-report-icon">
                              ⌖
                            </div>


                            <div>

                              <strong>
                                {
                                  report.title
                                }
                              </strong>

                              <span>
                                {
                                  report.region_name
                                }
                                {" • "}
                                {
                                  formatDate(
                                    report.submitted_at
                                  )
                                }
                              </span>

                            </div>


                            <span
                              className={
                                `report-status status-${report.report_status}`
                              }
                            >
                              {
                                statusLabel(
                                  report.report_status
                                )
                              }
                            </span>

                          </button>

                        )
                      )
                  }

                </div>

              </section>


              <section className="dashboard-panel ai-overview-panel">

                <div className="ai-symbol">
                  ✦
                </div>

                <span className="ai-panel-label">
                  AUTHORITY RAG
                </span>

                <h2>
                  Community Intelligence
                </h2>

                <p>
                  EcoLens analyses community
                  reports, assignments and
                  verified cleanup records,
                  then retrieves relevant
                  Bangladesh-specific
                  knowledge before producing
                  authority recommendations.
                </p>


                <button
                  type="button"

                  className="primary-dashboard-button wide"

                  onClick={() => {

                    setActiveSection(
                      "analytics"
                    );

                    generateRagAdvice();
                  }}
                >
                  Generate Recommendations
                  {" "}
                  ✦
                </button>

              </section>

            </div>

          </div>
        )}


        {/* ==================================================
            REPORTS
            ================================================== */}

        {activeSection ===
          "reports" && (

          <div className="dashboard-section">

            <div className="section-introduction">

              <div>

                <h2>
                  Public Waste Reports
                </h2>

                <p>
                  Reports submitted by
                  residents inside your
                  covered wards. These are
                  cleanup requests, not
                  household YOLO detections.
                </p>

              </div>

            </div>


            <div className="report-filter-bar">

              {[
                "all",
                "submitted",
                "assigned",
                "in_progress",
                "completed",
              ].map(
                (filter) => (

                  <button
                    type="button"

                    key={
                      filter
                    }

                    className={
                      reportFilter ===
                      filter

                        ? "report-filter active"

                        : "report-filter"
                    }

                    onClick={() =>
                      setReportFilter(
                        filter
                      )
                    }
                  >

                    {
                      filter ===
                      "all"

                        ? "All"

                        : statusLabel(
                            filter
                          )
                    }

                  </button>

                )
              )}

            </div>


            {reportList}

          </div>
        )}


        {/* ==================================================
            MAP
            ================================================== */}

        {activeSection ===
          "map" && (

          <div className="dashboard-section">

            <div className="section-introduction">

              <div>

                <h2>
                  Report Locations
                </h2>

                <p>
                  Ward ownership determines
                  which authority receives a
                  report. Google Maps
                  coordinates show employees
                  the exact cleanup location.
                </p>

              </div>

            </div>


            <div className="map-dashboard-layout">

              <div className="map-location-list">

                {
                  reports
                    .filter(
                      (report) =>
                        report.latitude &&
                        report.longitude
                    )
                    .map(
                      (report) => (

                        <button
                          key={
                            report.report_id
                          }

                          type="button"

                          className="map-location-item"

                          onClick={() =>
                            setSelectedReport(
                              report
                            )
                          }
                        >

                          <strong>
                            {
                              report.title
                            }
                          </strong>

                          <span>
                            {
                              report.region_name
                            }
                          </span>

                          <small>
                            {
                              report.address_text ||
                              "Map location"
                            }
                          </small>

                        </button>

                      )
                    )
                }

              </div>


              <div className="dashboard-map-container">

                <GoogleMap
                  latitude={
                    selectedReport
                      ?.latitude ||
                    reports.find(
                      (report) =>
                        report.latitude
                    )?.latitude
                  }

                  longitude={
                    selectedReport
                      ?.longitude ||
                    reports.find(
                      (report) =>
                        report.longitude
                    )?.longitude
                  }
                />

              </div>

            </div>

          </div>
        )}


        {/* ==================================================
            EMPLOYEES
            ================================================== */}

        {activeSection ===
          "employees" && (

          <div className="dashboard-section">

            <div className="section-introduction">

              <div>

                <h2>
                  Municipal Employees
                </h2>

                <p>
                  Employees registered under
                  this Community Authority.
                </p>

              </div>

            </div>


            <AuthorityEmployeeTools />


            <div className="employee-grid">

              {employees.map(
                (employee) => (

                  <article
                    className="employee-card"
                    key={
                      employee.employee_id
                    }
                  >

                    <div className="employee-card-top">

                      <div className="employee-avatar">

                        {
                          employee.full_name
                            ?.charAt(0)
                            ?.toUpperCase()
                        }

                      </div>


                      <span
                        className={
                          `employee-state ${employee.employment_status}`
                        }
                      >
                        {
                          statusLabel(
                            employee.employment_status
                          )
                        }
                      </span>

                    </div>


                    <h3>
                      {
                        employee.full_name
                      }
                    </h3>

                    <span className="employee-code">
                      {
                        employee.employee_code
                      }
                    </span>

                    <p>
                      {
                        employee.job_title ||
                        "Municipal Employee"
                      }
                    </p>


                    <div className="employee-workload">

                      <div>

                        <strong>
                          {
                            employee.active_assignments
                          }
                        </strong>

                        <span>
                          Active
                        </span>

                      </div>


                      <div>

                        <strong>
                          {
                            employee.completed_assignments
                          }
                        </strong>

                        <span>
                          Completed
                        </span>

                      </div>

                    </div>

                  </article>

                )
              )}

            </div>

          </div>
        )}


        {/* ==================================================
            ASSIGNMENTS
            ================================================== */}

        {activeSection ===
          "assignments" && (

          <div className="dashboard-section">

            <div className="section-introduction">

              <div>

                <h2>
                  Cleanup Assignments
                </h2>

                <p>
                  Track which employee is
                  responsible for each public
                  waste report.
                </p>

              </div>

            </div>


            <div className="assignment-table-wrap">

              <table className="assignment-table">

                <thead>

                  <tr>

                    <th>
                      Report
                    </th>

                    <th>
                      Employee
                    </th>

                    <th>
                      Ward
                    </th>

                    <th>
                      Priority
                    </th>

                    <th>
                      Status
                    </th>

                    <th>
                      Assigned
                    </th>

                  </tr>

                </thead>


                <tbody>

                  {assignments.map(
                    (assignment) => (

                      <tr
                        key={
                          assignment.assignment_id
                        }
                      >

                        <td>

                          <strong>
                            {
                              assignment.report_title
                            }
                          </strong>

                          <small>
                            #
                            {
                              assignment.report_id
                            }
                          </small>

                        </td>


                        <td>
                          {
                            assignment.employee_name
                          }
                        </td>


                        <td>
                          {
                            assignment.region_name
                          }
                        </td>


                        <td>

                          <span
                            className={
                              `priority-pill priority-${assignment.priority}`
                            }
                          >
                            {
                              statusLabel(
                                assignment.priority
                              )
                            }
                          </span>

                        </td>


                        <td>

                          <span
                            className={
                              `report-status status-${assignment.assignment_status}`
                            }
                          >
                            {
                              statusLabel(
                                assignment.assignment_status
                              )
                            }
                          </span>

                        </td>


                        <td>
                          {
                            formatDate(
                              assignment.assigned_at
                            )
                          }
                        </td>

                      </tr>

                    )
                  )}

                </tbody>

              </table>

            </div>

          </div>
        )}


        {/* ==================================================
            CLEANUP VERIFICATION
            ================================================== */}

        {activeSection ===
          "verification" && (

          <div className="dashboard-section">

            <div className="section-introduction">
              <div>
                <h2>
                  Cleanup Verification
                </h2>
                <p>
                  Review employee cleanup records before
                  they become part of verified Authority
                  waste analytics. Waste is grouped into
                  major mapped categories for comparison.
                </p>
              </div>
            </div>

            <AuthorityCleanupVerification
              onChanged={async () => {
                await loadDashboard();
                await loadDetailedAnalytics();
              }}
            />

          </div>
        )}


        {/* ==================================================
            ANALYTICS + RAG
            ================================================== */}

        {activeSection ===
          "analytics" && (

          <div className="dashboard-section">

            <div className="analytics-heading">

              <div>

                <h2>
                  Analytics & AI
                </h2>

                <p>
                  Analytics use operational
                  report, assignment and
                  verified cleanup data.
                  Authority RAG uses these
                  analytics to retrieve
                  relevant verified knowledge.
                </p>

              </div>


              <div className="authority-ai-actions authority-ai-actions-top">
                <div className="authority-language-toggle">
                  <button
                    type="button"
                    className={aiLanguage === "en" ? "active" : ""}
                    onClick={() => switchAiLanguage("en")}
                    disabled={geminiLoading}
                  >
                    English
                  </button>

                  <button
                    type="button"
                    className={aiLanguage === "bn" ? "active" : ""}
                    onClick={() => switchAiLanguage("bn")}
                    disabled={geminiLoading}
                  >
                    বাংলা
                  </button>
                </div>

                <button
                  type="button"
                  className="primary-dashboard-button"
                  onClick={() => generateGeminiAdvice(aiLanguage)}
                  disabled={geminiLoading}
                >
                  {geminiLoading
                    ? "Generating..."
                    : "Generate AI Recommendations ✦"}
                </button>
              </div>

            </div>


            {analytics && (

              <div className="analytics-grid">

                <div className="analytics-card">

                  <span>
                    Total Reports
                  </span>

                  <strong>
                    {
                      analytics.total_reports ??
                      summary.total_reports
                    }
                  </strong>

                </div>


                <div className="analytics-card">

                  <span>
                    Unresolved Reports
                  </span>

                  <strong>
                    {
                      analytics.unresolved_reports ??
                      summary.open_reports
                    }
                  </strong>

                </div>


                <div className="analytics-card">

                  <span>
                    Waste Collected
                  </span>

                  <strong>
                    {
                      Number(
                        detailedAnalytics?.waste?.total_collected_kg ??
                        analytics.total_waste_collected_kg ??
                        0
                      ).toFixed(1)
                    }
                    {" kg"}
                  </strong>

                </div>


                <div className="analytics-card">

                  <span>
                    Recycled
                  </span>

                  <strong>
                    {
                      Number(
                        detailedAnalytics?.waste?.recycled_kg ??
                        analytics.recycled_waste_kg ??
                        0
                      ).toFixed(1)
                    }
                    {" kg"}
                  </strong>

                </div>


                <div className="analytics-card">

                  <span>
                    Composted
                  </span>

                  <strong>
                    {
                      Number(
                        detailedAnalytics?.waste?.composted_kg ??
                        analytics.composted_waste_kg ??
                        0
                      ).toFixed(1)
                    }
                    {" kg"}
                  </strong>

                </div>


                <div className="analytics-card">

                  <span>
                    Hazardous Waste
                  </span>

                  <strong>
                    {
                      Number(
                        detailedAnalytics?.waste?.hazardous_kg ??
                        analytics.hazardous_waste_kg ??
                        0
                      ).toFixed(1)
                    }
                    {" kg"}
                  </strong>

                </div>

              </div>
            )}


            {detailedAnalyticsError && (
              <div className="rag-error">
                Detailed analytics could not be loaded: {detailedAnalyticsError}
              </div>
            )}

            <div className="authority-chart-grid">
              <StatBarChart
                title="Report Status Distribution"
                subtitle="Current reports visible to this authority"
                items={reportChartData}
              />

              <StatBarChart
                title="Assignment Status Distribution"
                subtitle="Current field-work assignments"
                items={assignmentChartData}
              />

              <StatBarChart
                title="Waste by Major Category"
                subtitle="Verified cleanup weight grouped by mapped waste category"
                items={wasteCategoryChartData}
                suffix=" kg"
                emptyMessage="No verified category-level cleanup data is available for this period. Verify pending cleanup reports to include them here."
              />

              <WasteCompositionChart
                items={wasteCategoryChartData}
              />

              <StatBarChart
                title="Verified Waste Handling Outcomes"
                subtitle="How verified collected waste was handled"
                items={wasteOutcomeChartData}
                suffix=" kg"
                emptyMessage="No verified cleanup handling data is available for this period yet."
              />

              <StatBarChart
                title="Operational Performance Rates"
                subtitle="Percentage indicators calculated from Authority analytics"
                items={performanceChartData}
                suffix="%"
                scaleMax={100}
              />
            </div>


            <section className="authority-ai-panel">
              <div className="authority-ai-toolbar authority-ai-toolbar-results">
                <div>
                  <span className="authority-ai-eyebrow">
                    RAG + GEMINI
                  </span>
                  <h2>
                    Grounded AI Recommendations
                  </h2>
                  <p>
                    Uses verified Authority analytics first, then adds
                    RAG context when available. Missing RAG sources do
                    not block practical analytics-based planning advice.
                  </p>
                </div>
              </div>

              {geminiError && (
                <div className="rag-error">
                  {geminiError}
                </div>
              )}

              {geminiResult && (
                <div className="authority-gemini-result">
                  <div className="rag-result-heading">
                    <div>
                      <span>✦ GEMINI + AUTHORITY RAG</span>
                      <h2>
                        {aiLanguage === "bn"
                          ? "কর্তৃপক্ষের জন্য পরামর্শ"
                          : "Authority Decision Support"}
                      </h2>
                    </div>

                    <span className="rag-mode-pill">
                      {geminiResult.mode ||
                        "gemini_grounded"}
                    </span>
                  </div>

                  {geminiResult.summary && (
                    <p className="authority-ai-summary">
                      {geminiResult.summary}
                    </p>
                  )}

                  {(geminiResult.recommendations || [])
                    .length === 0 ? (
                    <div className="authority-ai-empty">
                      {aiLanguage === "bn"
                        ? "এই সময়সীমায় যথেষ্ট ব্যবহারযোগ্য যাচাইকৃত অ্যানালিটিক্স নেই। আরও তথ্য যোগ হলে EcoLens নির্ভরযোগ্য পরামর্শ তৈরি করতে পারবে।"
                        : "No recommendations were returned. If all operational analytics are zero, verify more cleanup data and try again; otherwise refresh and regenerate the AI recommendations."}
                    </div>
                  ) : (
                    (geminiResult.recommendations || [])
                      .map((recommendation, index) => (
                        <article
                          className="rag-recommendation"
                          key={`gemini-${recommendation.title}-${index}`}
                        >
                          <div className="rag-recommendation-top">
                            <h3>{recommendation.title}</h3>
                            <span
                              className={
                                `priority-pill priority-${recommendation.priority}`
                              }
                            >
                              {statusLabel(
                                recommendation.priority
                              )}
                            </span>
                          </div>

                          <p>{recommendation.why}</p>

                          <ul>
                            {(recommendation.actions || [])
                              .map((action, actionIndex) => (
                                <li key={actionIndex}>
                                  {action}
                                </li>
                              ))}
                          </ul>
                        </article>
                      ))
                  )}

                  {geminiResult.disclaimer && (
                    <p className="authority-ai-disclaimer">
                      {geminiResult.disclaimer}
                    </p>
                  )}

                  <section className="authority-chatbox">
                    <div className="authority-chat-heading">
                      <div>
                        <span>FOLLOW-UP CHAT</span>
                        <h3>
                          {aiLanguage === "bn"
                            ? "EcoLens-কে আরও জিজ্ঞাসা করুন"
                            : "Ask EcoLens a follow-up"}
                        </h3>
                      </div>
                      <small>
                        {aiLanguage === "bn"
                          ? "একই অ্যানালিটিক্স ও যাচাইকৃত RAG প্রসঙ্গ ব্যবহার করা হবে"
                          : "Uses the same analytics and verified RAG context"}
                      </small>
                    </div>

                    <div className="authority-chat-messages">
                      {chatMessages.length === 0 && (
                        <div className="authority-chat-placeholder">
                          {aiLanguage === "bn"
                            ? "পরামর্শ, বর্জ্য প্রবণতা বা অগ্রাধিকার সম্পর্কে প্রশ্ন করুন।"
                            : "Ask about the recommendations, waste trends or operational priorities."}
                        </div>
                      )}

                      {chatMessages.map((message, index) => (
                        <div
                          key={`${message.role}-${index}`}
                          className={
                            `authority-chat-message ${message.role}`
                          }
                        >
                          {message.content}
                        </div>
                      ))}

                      {chatLoading && (
                        <div className="authority-chat-message assistant">
                          {aiLanguage === "bn"
                            ? "উত্তর তৈরি হচ্ছে..."
                            : "Preparing grounded answer..."}
                        </div>
                      )}
                    </div>

                    {chatError && (
                      <div className="rag-error">
                        {chatError}
                      </div>
                    )}

                    <form
                      className="authority-chat-form"
                      onSubmit={sendAuthorityChat}
                    >
                      <textarea
                        rows="3"
                        value={chatInput}
                        onChange={(event) =>
                          setChatInput(
                            event.target.value
                          )
                        }
                        placeholder={
                          aiLanguage === "bn"
                            ? "আপনার প্রশ্ন লিখুন..."
                            : "Ask a grounded follow-up question..."
                        }
                        disabled={chatLoading}
                      />

                      <button
                        type="submit"
                        className="primary-dashboard-button"
                        disabled={
                          chatLoading ||
                          !chatInput.trim()
                        }
                      >
                        {aiLanguage === "bn"
                          ? "জিজ্ঞাসা করুন ✦"
                          : "Ask EcoLens ✦"}
                      </button>
                    </form>
                  </section>
                </div>
              )}
            </section>


          </div>
        )}


        {/* ==================================================
            COVERAGE
            ================================================== */}

        {activeSection ===
          "coverage" && (

          <div className="dashboard-section">

            <div className="section-introduction">

              <div>

                <h2>
                  Covered Wards
                </h2>

                <p>
                  Public reports inside these
                  wards belong to this
                  Community Authority.
                </p>

              </div>

            </div>


            <div className="coverage-grid">

              {coverage.map(
                (ward) => (

                  <article
                    className="coverage-card"
                    key={
                      ward.region_id
                    }
                  >

                    <div className="coverage-icon">
                      ◎
                    </div>


                    <div>

                      <h3>
                        {
                          ward.region_name
                        }
                      </h3>

                      <span>
                        {
                          ward.region_code
                        }
                      </span>


                      {Boolean(
                        ward.is_primary
                      ) && (

                        <small>
                          Primary Ward
                        </small>

                      )}

                    </div>

                  </article>

                )
              )}

            </div>

          </div>
        )}


      </section>


      {/* ====================================================
          REPORT DETAIL MODAL
          ==================================================== */}

      {selectedReport &&
        !assignmentOpen &&
        activeSection !==
          "map" && (

        <div
          className="dashboard-modal-backdrop"

          onClick={() =>
            setSelectedReport(
              null
            )
          }
        >

          <div
            className="dashboard-modal report-detail-modal"

            onClick={
              (event) =>
                event.stopPropagation()
            }
          >

            <button
              type="button"

              className="modal-close"

              onClick={() =>
                setSelectedReport(
                  null
                )
              }
            >
              ×
            </button>


            {reportLoading ? (

              <p>
                Loading report...
              </p>

            ) : (

              <>

                <span className="modal-eyebrow">
                  PUBLIC WASTE REPORT
                </span>


                <h2>
                  {
                    selectedReport.title
                  }
                </h2>


                <div className="report-detail-tags">

                  <span>
                    {
                      selectedReport.region_name
                    }
                  </span>

                  <span
                    className={
                      `report-status status-${selectedReport.report_status}`
                    }
                  >
                    {
                      statusLabel(
                        selectedReport.report_status
                      )
                    }
                  </span>

                </div>


                <p className="report-detail-description">
                  {
                    selectedReport.description
                  }
                </p>


                <div className="report-detail-information">

                  <div>

                    <span>
                      Reporter
                    </span>

                    <strong>
                      {
                        selectedReport.reporter_name
                      }
                    </strong>

                  </div>


                  <div>

                    <span>
                      Submitted
                    </span>

                    <strong>
                      {
                        formatDate(
                          selectedReport.submitted_at
                        )
                      }
                    </strong>

                  </div>


                  <div>

                    <span>
                      Address
                    </span>

                    <strong>
                      {
                        selectedReport.address_text ||
                        "Map location"
                      }
                    </strong>

                  </div>


                  <div>

                    <span>
                      Ward
                    </span>

                    <strong>
                      {
                        selectedReport.region_name
                      }
                    </strong>

                  </div>

                </div>


                <GoogleMap
                  latitude={
                    selectedReport.latitude
                  }

                  longitude={
                    selectedReport.longitude
                  }
                />


                <div className="report-modal-actions">

                  {selectedReport.latitude &&
                    selectedReport.longitude && (

                    <a
                      className="secondary-dashboard-button link-button"

                      href={
                        `https://www.google.com/maps?q=${selectedReport.latitude},${selectedReport.longitude}`
                      }

                      target="_blank"

                      rel="noreferrer"
                    >
                      Open in Google Maps ↗
                    </a>

                  )}


                  {Number(
                    selectedReport.active_assignment_count
                  ) === 0 &&

                    ![
                      "completed",
                      "rejected",
                      "cancelled",
                    ].includes(
                      selectedReport.report_status
                    ) && (

                    <button
                      type="button"

                      className="primary-dashboard-button"

                      onClick={() =>
                        openAssignment(
                          selectedReport
                        )
                      }
                    >
                      Assign Employee
                    </button>

                  )}

                </div>

              </>

            )}

          </div>

        </div>
      )}


      {/* ====================================================
          ASSIGNMENT MODAL
          ==================================================== */}

      {assignmentOpen &&
        selectedReport && (

        <div
          className="dashboard-modal-backdrop"

          onClick={() =>
            setAssignmentOpen(
              false
            )
          }
        >

          <form
            className="dashboard-modal assignment-modal"

            onSubmit={
              submitAssignment
            }

            onClick={
              (event) =>
                event.stopPropagation()
            }
          >

            <button
              type="button"

              className="modal-close"

              onClick={() =>
                setAssignmentOpen(
                  false
                )
              }
            >
              ×
            </button>


            <span className="modal-eyebrow">
              FIELD ASSIGNMENT
            </span>


            <h2>
              Assign Cleanup Employee
            </h2>


            <p>
              {
                selectedReport.title
              }
              {" • "}
              {
                selectedReport.region_name
              }
            </p>


            <label className="dashboard-form-field">

              <span>
                Employee
              </span>


              <select
                value={
                  assignmentForm.employee_id
                }

                onChange={
                  (event) =>
                    setAssignmentForm(
                      (previous) => ({
                        ...previous,

                        employee_id:
                          event.target.value,
                      })
                    )
                }

                required
              >

                <option value="">
                  Select employee
                </option>


                {employees
                  .filter(
                    (employee) =>
                      employee.employment_status ===
                      "active"
                  )
                  .map(
                    (employee) => (

                      <option
                        key={
                          employee.employee_id
                        }

                        value={
                          employee.employee_id
                        }
                      >

                        {
                          employee.full_name
                        }
                        {" — "}
                        {
                          employee.active_assignments
                        }
                        {" active job(s)"}

                      </option>

                    )
                  )}

              </select>

            </label>


            <label className="dashboard-form-field">

              <span>
                Assignment Priority
              </span>


              <select
                value={
                  assignmentForm.priority
                }

                onChange={
                  (event) =>
                    setAssignmentForm(
                      (previous) => ({
                        ...previous,

                        priority:
                          event.target.value,
                      })
                    )
                }
              >

                <option value="low">
                  Low
                </option>

                <option value="medium">
                  Medium
                </option>

                <option value="high">
                  High
                </option>

                <option value="urgent">
                  Urgent
                </option>

              </select>

            </label>


            <label className="dashboard-form-field">

              <span>
                Instructions
              </span>


              <textarea
                rows="4"

                placeholder="Optional instructions for the employee..."

                value={
                  assignmentForm.assignment_notes
                }

                onChange={
                  (event) =>
                    setAssignmentForm(
                      (previous) => ({
                        ...previous,

                        assignment_notes:
                          event.target.value,
                      })
                    )
                }
              />

            </label>


            {assignmentMessage && (

              <div className="assignment-message">
                {
                  assignmentMessage
                }
              </div>

            )}


            <button
              type="submit"

              className="primary-dashboard-button wide"

              disabled={
                assigning
              }
            >

              {assigning
                ? "Assigning..."
                : "Assign Employee"}

            </button>

          </form>

        </div>

      )}

    </main>
  );
}


export default AuthorityDashboard;