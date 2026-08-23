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


  useEffect(
    () => {

      loadDashboard();

    },
    []
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


              <button
                type="button"

                className="primary-dashboard-button"

                onClick={
                  generateRagAdvice
                }

                disabled={
                  ragLoading
                }
              >

                {ragLoading
                  ? "Analysing..."
                  : "Generate RAG Recommendations ✦"}

              </button>

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
                        analytics.total_waste_collected_kg ||
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
                        analytics.recycled_waste_kg ||
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
                        analytics.composted_waste_kg ||
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
                        analytics.hazardous_waste_kg ||
                        0
                      ).toFixed(1)
                    }
                    {" kg"}
                  </strong>

                </div>

              </div>
            )}


            {ragError && (

              <div className="rag-error">
                {ragError}
              </div>

            )}


            {ragResult && (

              <section className="rag-result-panel">

                <div className="rag-result-heading">

                  <div>

                    <span>
                      ✦ ECOLENS RAG
                    </span>

                    <h2>
                      Community Recommendations
                    </h2>

                  </div>


                  {ragResult.mode && (

                    <span className="rag-mode-pill">
                      {
                        ragResult.mode
                      }
                    </span>

                  )}

                </div>


                {
                  (
                    ragResult.recommendations ||
                    ragResult.result
                      ?.recommendations ||
                    []
                  ).map(
                    (
                      recommendation,
                      index
                    ) => (

                      <article
                        className="rag-recommendation"
                        key={
                          `${recommendation.title}-${index}`
                        }
                      >

                        <div className="rag-recommendation-top">

                          <h3>
                            {
                              recommendation.title
                            }
                          </h3>


                          <span
                            className={
                              `priority-pill priority-${recommendation.priority}`
                            }
                          >
                            {
                              statusLabel(
                                recommendation.priority
                              )
                            }
                          </span>

                        </div>


                        <p>
                          {
                            recommendation.why
                          }
                        </p>


                        <ul>

                          {
                            (
                              recommendation.actions ||
                              []
                            ).map(
                              (
                                action,
                                actionIndex
                              ) => (

                                <li
                                  key={
                                    actionIndex
                                  }
                                >
                                  {
                                    action
                                  }
                                </li>

                              )
                            )
                          }

                        </ul>

                      </article>

                    )
                  )
                }

              </section>
            )}

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