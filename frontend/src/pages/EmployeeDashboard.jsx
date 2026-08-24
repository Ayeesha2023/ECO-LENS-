import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  useNavigate,
} from "react-router-dom";

import logo
  from "../assets/ecolens-logo.png";

import {
  apiRequest,
} from "../services/api";

import "../styles/employee-dashboard.css";


const menuItems = [
  {
    id: "overview",
    icon: "⌂",
    label: "Overview",
  },
  {
    id: "assignments",
    icon: "▤",
    label: "My Assignments",
  },
  {
    id: "map",
    icon: "⌖",
    label: "Map",
  },
  {
    id: "safety",
    icon: "✦",
    label: "Safety Guidance",
  },
  {
    id: "completed",
    icon: "✓",
    label: "Completed Jobs",
  },
  {
    id: "profile",
    icon: "○",
    label: "Profile",
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


function label(
  value
) {
  const labels = {
    assigned:
      "New Assignment",

    accepted:
      "Accepted",

    in_progress:
      "In Progress",

    completed:
      "Completed",

    cancelled:
      "Cancelled",

    pending:
      "Waiting for Authority Verification",

    verified:
      "Verified by Authority",

    rejected:
      "Verification Rejected",

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
    labels[value] ||
    String(
      value || ""
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
      <div className="employee-empty-map">
        <span>
          ⌖
        </span>

        <p>
          Exact map coordinates are not
          available for this assignment.
        </p>
      </div>
    );
  }

  const mapUrl =
    `https://www.google.com/maps?q=${latitude},${longitude}&output=embed`;

  return (
    <iframe
      className="employee-map-frame"
      src={mapUrl}
      title="Cleanup location"
      loading="lazy"
      referrerPolicy="no-referrer-when-downgrade"
    />
  );
}


function EmployeeDashboard() {
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
    selectedAssignment,
    setSelectedAssignment,
  ] = useState(null);

  const [
    assignmentLoading,
    setAssignmentLoading,
  ] = useState(false);

  const [
    actionLoading,
    setActionLoading,
  ] = useState(false);

  const [
    scanFile,
    setScanFile,
  ] = useState(null);

  const [
    scanLoading,
    setScanLoading,
  ] = useState(false);

  const [
    scanResult,
    setScanResult,
  ] = useState(null);

  const [
    ragLoading,
    setRagLoading,
  ] = useState(false);

  const [
    ragResult,
    setRagResult,
  ] = useState(null);

  const [
    ragError,
    setRagError,
  ] = useState("");

  const [
    ragAdviceId,
    setRagAdviceId,
  ] = useState(null);

  const [
    detailedLoading,
    setDetailedLoading,
  ] = useState(false);

  const [
    detailedResult,
    setDetailedResult,
  ] = useState(null);

  const [
    detailedError,
    setDetailedError,
  ] = useState("");

  const [
    detailedLanguage,
    setDetailedLanguage,
  ] = useState("en");

  const [
    completionOpen,
    setCompletionOpen,
  ] = useState(false);

  const [
    afterImage,
    setAfterImage,
  ] = useState(null);

  const [
    cleanupNotes,
    setCleanupNotes,
  ] = useState("");

  const [
    wasteRows,
    setWasteRows,
  ] = useState([
    {
      model_class_id: "",
      weight_kg: "",
      handling_method:
        "other",
      notes: "",
    },
  ]);

  const [
    completionLoading,
    setCompletionLoading,
  ] = useState(false);

  const [
    completionMessage,
    setCompletionMessage,
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
            "/api/employee/dashboard/bootstrap"
          );

        setData(
          response
        );

      } catch (
        requestError
      ) {
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
            1000
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
  // DERIVED LISTS
  // ========================================================

  const activeAssignments =
    useMemo(
      () => {
        if (!data) {
          return [];
        }

        return (
          data.assignments || []
        ).filter(
          (assignment) =>
            [
              "assigned",
              "accepted",
              "in_progress",
            ].includes(
              assignment.assignment_status
            )
        );
      },
      [data]
    );


  const completedAssignments =
    useMemo(
      () => {
        if (!data) {
          return [];
        }

        return (
          data.assignments || []
        ).filter(
          (assignment) =>
            assignment.assignment_status ===
            "completed"
        );
      },
      [data]
    );


  // ========================================================
  // DETAIL
  // ========================================================

  const openAssignment =
    async (
      assignmentId
    ) => {
      try {
        setAssignmentLoading(
          true
        );

        const response =
          await apiRequest(
            `/api/employee/dashboard/assignments/${assignmentId}`
          );

        setSelectedAssignment(
          response.assignment
        );

        setScanResult(null);
        setRagResult(null);
        setRagError("");
        setRagAdviceId(null);
        setDetailedResult(null);
        setDetailedError("");
        setDetailedLanguage("en");

      } catch (
        requestError
      ) {
        alert(
          requestError.message
        );

      } finally {
        setAssignmentLoading(
          false
        );
      }
    };


  // ========================================================
  // ACCEPT / START
  // ========================================================

  const updateAssignment =
    async (
      action
    ) => {
      if (
        !selectedAssignment
      ) {
        return;
      }

      try {
        setActionLoading(
          true
        );

        await apiRequest(
          `/api/employee/dashboard/assignments/${selectedAssignment.assignment_id}/${action}`,
          {
            method:
              "POST",
          }
        );

        await loadDashboard();

        await openAssignment(
          selectedAssignment.assignment_id
        );

      } catch (
        requestError
      ) {
        alert(
          requestError.message
        );

      } finally {
        setActionLoading(
          false
        );
      }
    };


  // ========================================================
  // YOLO + EMPLOYEE RAG
  // ========================================================

  const scanWaste =
    async () => {
      if (
        !selectedAssignment
      ) {
        return;
      }

      if (!scanFile) {
        setRagError(
          "Choose a waste image first."
        );

        return;
      }

      try {
        setScanLoading(
          true
        );

        setRagLoading(false);
        setRagError("");
        setScanResult(null);
        setRagResult(null);
        setRagAdviceId(null);
        setDetailedResult(null);
        setDetailedError("");

        const formData =
          new FormData();

        formData.append(
          "image",
          scanFile
        );

        const scanResponse =
          await apiRequest(
            `/api/employee/dashboard/assignments/${selectedAssignment.assignment_id}/scan`,
            {
              method:
                "POST",

              body:
                formData,
            }
          );

        setScanResult(
          scanResponse.detection
        );

        setRagLoading(true);

        const ragResponse =
          await apiRequest(
            `/api/employee/${data.employee.employee_id}/advice`,
            {
              method:
                "POST",

              body:
                JSON.stringify(
                  {
                    assignment_id:
                      selectedAssignment.assignment_id,

                    language:
                      "en",
                  }
                ),
            }
          );

        setRagResult(
          ragResponse.result ||
          ragResponse.advice ||
          ragResponse
        );

        setRagAdviceId(
          ragResponse.advice_id ||
          null
        );

      } catch (
        requestError
      ) {
        setRagError(
          requestError.message
        );

      } finally {
        setScanLoading(false);
        setRagLoading(false);
      }
    };


  // ========================================================
  // OPTIONAL GEMINI-DETAILED GUIDANCE
  // ========================================================

  const getDetailedGuidance =
    async () => {
      if (
        !data ||
        !ragAdviceId
      ) {
        setDetailedError(
          "Run the waste scan and Employee RAG guidance first."
        );
        return;
      }

      try {
        setDetailedLoading(true);
        setDetailedError("");
        setDetailedResult(null);

        const response =
          await apiRequest(
            `/api/employee/${data.employee.employee_id}/advice/${ragAdviceId}/detailed`,
            {
              method:
                "POST",

              body:
                JSON.stringify(
                  {
                    language:
                      detailedLanguage,
                  }
                ),
            }
          );

        setDetailedResult(
          response.result ||
          null
        );

      } catch (
        requestError
      ) {
        setDetailedError(
          requestError.message
        );

      } finally {
        setDetailedLoading(false);
      }
    };


  // ========================================================
  // COMPLETION FORM
  // ========================================================

  const addWasteRow =
    () => {
      setWasteRows(
        (previous) => [
          ...previous,
          {
            model_class_id: "",
            weight_kg: "",
            handling_method:
              "other",
            notes: "",
          },
        ]
      );
    };


  const updateWasteRow =
    (
      index,
      field,
      value
    ) => {
      setWasteRows(
        (previous) =>
          previous.map(
            (
              row,
              rowIndex
            ) =>
              rowIndex === index
                ? {
                    ...row,
                    [field]:
                      value,
                  }
                : row
          )
      );
    };


  const removeWasteRow =
    (
      index
    ) => {
      setWasteRows(
        (previous) =>
          previous.filter(
            (
              _,
              rowIndex
            ) =>
              rowIndex !== index
          )
      );
    };


  const openCompletion =
    () => {
      setCompletionMessage("");
      setAfterImage(null);
      setCleanupNotes("");

      setWasteRows([
        {
          model_class_id: "",
          weight_kg: "",
          handling_method:
            "other",
          notes: "",
        },
      ]);

      setCompletionOpen(
        true
      );
    };


  const completeCleanup =
    async (
      event
    ) => {
      event.preventDefault();

      if (
        !selectedAssignment
      ) {
        return;
      }

      if (!afterImage) {
        setCompletionMessage(
          "Upload an after-cleanup photo."
        );

        return;
      }

      const normalizedRows =
        wasteRows
          .filter(
            (row) =>
              row.model_class_id &&
              Number(
                row.weight_kg
              ) > 0
          )
          .map(
            (row) => ({
              model_class_id:
                Number(
                  row.model_class_id
                ),

              weight_kg:
                Number(
                  row.weight_kg
                ),

              handling_method:
                row.handling_method,

              notes:
                row.notes,
            })
          );

      if (
        normalizedRows.length ===
        0
      ) {
        setCompletionMessage(
          "Enter at least one waste type and weight."
        );

        return;
      }

      try {
        setCompletionLoading(
          true
        );

        setCompletionMessage(
          ""
        );

        const formData =
          new FormData();

        formData.append(
          "after_image",
          afterImage
        );

        formData.append(
          "cleanup_notes",
          cleanupNotes
        );

        formData.append(
          "waste_breakdown",
          JSON.stringify(
            normalizedRows
          )
        );

        const response =
          await apiRequest(
            `/api/employee/dashboard/assignments/${selectedAssignment.assignment_id}/complete`,
            {
              method:
                "POST",

              body:
                formData,
            }
          );

        setCompletionMessage(
          response.message
        );

        await loadDashboard();

        setSelectedAssignment(
          null
        );

        setTimeout(
          () => {
            setCompletionOpen(
              false
            );

            setActiveSection(
              "completed"
            );
          },
          900
        );

      } catch (
        requestError
      ) {
        setCompletionMessage(
          requestError.message
        );

      } finally {
        setCompletionLoading(
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
            method:
              "POST",
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
      <main className="employee-loading">
        <img
          src={logo}
          alt="EcoLens"
        />

        <p>
          Loading Employee Dashboard...
        </p>
      </main>
    );
  }


  if (
    error ||
    !data
  ) {
    return (
      <main className="employee-loading">
        <img
          src={logo}
          alt="EcoLens"
        />

        <p>
          {error ||
            "Employee dashboard could not be loaded."}
        </p>
      </main>
    );
  }


  const {
    employee,
    summary,
    model_classes: modelClasses,
  } = data;


  const assignmentCards =
    (items) => (
      <div className="employee-job-list">
        {items.length === 0 && (
          <div className="employee-empty-state">
            No assignments here yet.
          </div>
        )}

        {items.map(
          (assignment) => (
            <article
              className="employee-job-card"
              key={
                assignment.assignment_id
              }
            >
              <div className="employee-job-marker">
                <span>
                  ⌖
                </span>

                <small>
                  #
                  {
                    assignment.assignment_id
                  }
                </small>
              </div>

              <div className="employee-job-content">
                <div className="employee-job-heading">
                  <div>
                    <span className="employee-ward-label">
                      {
                        assignment.region_name
                      }
                    </span>

                    <h3>
                      {
                        assignment.report_title
                      }
                    </h3>
                  </div>

                  <div className="employee-job-badges">
                    <span
                      className={
                        `employee-priority priority-${assignment.priority}`
                      }
                    >
                      {
                        label(
                          assignment.priority
                        )
                      }
                    </span>

                    <span
                      className={
                        `employee-status status-${assignment.assignment_status}`
                      }
                    >
                      {
                        label(
                          assignment.assignment_status
                        )
                      }
                    </span>
                  </div>
                </div>

                <p>
                  {
                    assignment.report_description
                  }
                </p>

                <div className="employee-job-meta">
                  <span>
                    ⌖{" "}
                    {
                      assignment.address_text ||
                      "Map location"
                    }
                  </span>

                  <span>
                    ◷{" "}
                    {
                      formatDate(
                        assignment.assigned_at
                      )
                    }
                  </span>
                </div>

                <div className="employee-job-actions">
                  <button
                    type="button"
                    className="employee-secondary-button"
                    onClick={() =>
                      openAssignment(
                        assignment.assignment_id
                      )
                    }
                  >
                    View Job
                  </button>

                  {assignment.latitude &&
                    assignment.longitude && (
                    <a
                      className="employee-secondary-button"
                      href={
                        `https://www.google.com/maps?q=${assignment.latitude},${assignment.longitude}`
                      }
                      target="_blank"
                      rel="noreferrer"
                    >
                      Open Map ↗
                    </a>
                  )}
                </div>
              </div>
            </article>
          )
        )}
      </div>
    );


  return (
    <main className="employee-dashboard">

      {/* SIDEBAR */}
      <aside className="employee-sidebar">
        <div>
          <div className="employee-brand">
            <img
              src={logo}
              alt="EcoLens"
            />

            <div>
              <strong>
                EcoLens
              </strong>

              <span>
                Municipal Employee
              </span>
            </div>
          </div>

          <nav className="employee-nav">
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
                      ? "employee-nav-item active"
                      : "employee-nav-item"
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

                  {
                    item.label
                  }
                </button>
              )
            )}
          </nav>
        </div>

        <div className="employee-sidebar-bottom">
          <div className="employee-profile-mini">
            <div className="employee-profile-letter">
              {
                employee.full_name
                  ?.charAt(0)
                  ?.toUpperCase()
              }
            </div>

            <div>
              <strong>
                {
                  employee.full_name
                }
              </strong>

              <span>
                {
                  employee.employee_code
                }
              </span>
            </div>
          </div>

          <button
            type="button"
            className="employee-logout"
            onClick={
              handleLogout
            }
          >
            Log Out
          </button>
        </div>
      </aside>


      {/* MAIN */}
      <section className="employee-main">
        <header className="employee-topbar">
          <div>
            <span>
              FIELD OPERATIONS
            </span>

            <h1>
              {
                activeSection ===
                "overview"
                  ? "Overview"
                  : menuItems.find(
                      (item) =>
                        item.id ===
                        activeSection
                    )?.label
              }
            </h1>
          </div>

          <div className="employee-org-pill">
            {
              employee.organization_name
            }
          </div>
        </header>


        {/* OVERVIEW */}
        {activeSection ===
          "overview" && (
          <div className="employee-section">
            <section className="employee-welcome">
              <div>
                <span>
                  TODAY'S FIELD WORK
                </span>

                <h2>
                  Welcome,
                  {" "}
                  {
                    employee.full_name
                  }.
                </h2>

                <p>
                  Accept assigned cleanup jobs,
                  use the location to reach the
                  site, follow safety guidance
                  and report what was collected.
                </p>
              </div>

              <div className="employee-welcome-icon">
                ✓
              </div>
            </section>

            <div className="employee-stat-grid">
              <div className="employee-stat">
                <span>
                  New Assignments
                </span>

                <strong>
                  {
                    summary.new_assignments
                  }
                </strong>
              </div>

              <div className="employee-stat">
                <span>
                  Active Jobs
                </span>

                <strong>
                  {
                    summary.active_assignments
                  }
                </strong>
              </div>

              <div className="employee-stat">
                <span>
                  In Progress
                </span>

                <strong>
                  {
                    summary.in_progress
                  }
                </strong>
              </div>

              <div className="employee-stat">
                <span>
                  Completed
                </span>

                <strong>
                  {
                    summary.completed_assignments
                  }
                </strong>
              </div>
            </div>

            <div className="employee-section-heading">
              <div>
                <span>
                  ACTIVE WORK
                </span>

                <h2>
                  Current Assignments
                </h2>
              </div>

              <button
                type="button"
                className="employee-text-button"
                onClick={() =>
                  setActiveSection(
                    "assignments"
                  )
                }
              >
                View all →
              </button>
            </div>

            {
              assignmentCards(
                activeAssignments.slice(
                  0,
                  4
                )
              )
            }
          </div>
        )}


        {/* ASSIGNMENTS */}
        {activeSection ===
          "assignments" && (
          <div className="employee-section">
            <div className="employee-section-heading">
              <div>
                <span>
                  ASSIGNED BY AUTHORITY
                </span>

                <h2>
                  My Assignments
                </h2>

                <p>
                  A job moves from New Assignment
                  → Accepted → In Progress →
                  Completed.
                </p>
              </div>
            </div>

            {
              assignmentCards(
                activeAssignments
              )
            }
          </div>
        )}


        {/* MAP */}
        {activeSection ===
          "map" && (
          <div className="employee-section">
            <div className="employee-section-heading">
              <div>
                <span>
                  CLEANUP LOCATIONS
                </span>

                <h2>
                  Assignment Map
                </h2>

                <p>
                  Select an assignment to see its
                  reported coordinates.
                </p>
              </div>
            </div>

            <div className="employee-map-layout">
              <div className="employee-map-list">
                {activeAssignments.map(
                  (assignment) => (
                    <button
                      type="button"
                      key={
                        assignment.assignment_id
                      }
                      className="employee-map-item"
                      onClick={() =>
                        setSelectedAssignment(
                          assignment
                        )
                      }
                    >
                      <strong>
                        {
                          assignment.report_title
                        }
                      </strong>

                      <span>
                        {
                          assignment.region_name
                        }
                      </span>

                      <small>
                        {
                          label(
                            assignment.assignment_status
                          )
                        }
                      </small>
                    </button>
                  )
                )}
              </div>

              <div className="employee-map-box">
                <GoogleMap
                  latitude={
                    selectedAssignment
                      ?.latitude ||
                    activeAssignments.find(
                      (item) =>
                        item.latitude
                    )?.latitude
                  }
                  longitude={
                    selectedAssignment
                      ?.longitude ||
                    activeAssignments.find(
                      (item) =>
                        item.longitude
                    )?.longitude
                  }
                />
              </div>
            </div>
          </div>
        )}


        {/* SAFETY */}
        {activeSection ===
          "safety" && (
          <div className="employee-section">
            <section className="employee-safety-intro">
              <div>
                <span>
                  YOLO → RAG
                </span>

                <h2>
                  Worker Safety Guidance
                </h2>

                <p>
                  Safety guidance belongs to a
                  specific assignment. Open an
                  active job, scan waste at the
                  site and EcoLens uses YOLO
                  detection with the existing
                  Employee RAG pipeline.
                </p>
              </div>

              <div>
                ✦
              </div>
            </section>

            <div className="employee-info-panel">
              <strong>
                How this part works
              </strong>

              <p>
                1. Accept the cleanup job.
                {" "}
                2. Reach the location.
                {" "}
                3. Take a waste photo.
                {" "}
                4. YOLO identifies classes.
                {" "}
                5. Employee RAG retrieves worker
                safety, handling and disposal
                knowledge.
              </p>

              <button
                type="button"
                className="employee-primary-button"
                onClick={() =>
                  setActiveSection(
                    "assignments"
                  )
                }
              >
                Open My Assignments
              </button>
            </div>
          </div>
        )}


        {/* COMPLETED */}
        {activeSection ===
          "completed" && (
          <div className="employee-section">
            <div className="employee-section-heading">
              <div>
                <span>
                  CLEANUP HISTORY
                </span>

                <h2>
                  Completed Jobs
                </h2>

                <p>
                  Waste quantities remain marked
                  pending until the Community
                  Authority verifies the cleanup
                  record.
                </p>
              </div>
            </div>

            {
              assignmentCards(
                completedAssignments
              )
            }

            {completedAssignments.length >
              0 && (
              <div className="employee-verification-note">
                <strong>
                  Analytics rule:
                </strong>
                {" "}
                cleanup quantities are sent to the
                authority first. Verified cleanup
                records are then used by authority
                waste analytics.
              </div>
            )}
          </div>
        )}


        {/* PROFILE */}
        {activeSection ===
          "profile" && (
          <div className="employee-section">
            <div className="employee-profile-card">
              <div className="employee-large-avatar">
                {
                  employee.full_name
                    ?.charAt(0)
                    ?.toUpperCase()
                }
              </div>

              <h2>
                {
                  employee.full_name
                }
              </h2>

              <p>
                {
                  employee.job_title ||
                  "Municipal Employee"
                }
              </p>

              <div className="employee-profile-grid">
                <div>
                  <span>
                    Employee Code
                  </span>

                  <strong>
                    {
                      employee.employee_code
                    }
                  </strong>
                </div>

                <div>
                  <span>
                    Authority
                  </span>

                  <strong>
                    {
                      employee.organization_name
                    }
                  </strong>
                </div>

                <div>
                  <span>
                    Email
                  </span>

                  <strong>
                    {
                      employee.email
                    }
                  </strong>
                </div>

                <div>
                  <span>
                    Primary Region
                  </span>

                  <strong>
                    {
                      employee.primary_region_name
                    }
                  </strong>
                </div>
              </div>
            </div>
          </div>
        )}
      </section>


      {/* JOB DETAIL MODAL */}
      {selectedAssignment &&
        activeSection !==
          "map" && (
        <div
          className="employee-modal-backdrop"
          onClick={() =>
            setSelectedAssignment(
              null
            )
          }
        >
          <section
            className="employee-modal employee-job-modal"
            onClick={
              (event) =>
                event.stopPropagation()
            }
          >
            <button
              type="button"
              className="employee-modal-close"
              onClick={() =>
                setSelectedAssignment(
                  null
                )
              }
            >
              ×
            </button>

            {assignmentLoading ? (
              <p>
                Loading assignment...
              </p>
            ) : (
              <>
                <span className="employee-modal-eyebrow">
                  CLEANUP ASSIGNMENT
                </span>

                <h2>
                  {
                    selectedAssignment.report_title
                  }
                </h2>

                <div className="employee-detail-badges">
                  <span
                    className={
                      `employee-priority priority-${selectedAssignment.priority}`
                    }
                  >
                    {
                      label(
                        selectedAssignment.priority
                      )
                    }
                  </span>

                  <span
                    className={
                      `employee-status status-${selectedAssignment.assignment_status}`
                    }
                  >
                    {
                      label(
                        selectedAssignment.assignment_status
                      )
                    }
                  </span>
                </div>

                <p className="employee-detail-description">
                  {
                    selectedAssignment.report_description
                  }
                </p>

                <div className="employee-detail-grid">
                  <div>
                    <span>
                      Ward
                    </span>

                    <strong>
                      {
                        selectedAssignment.region_name
                      }
                    </strong>
                  </div>

                  <div>
                    <span>
                      Address
                    </span>

                    <strong>
                      {
                        selectedAssignment.address_text ||
                        "Map location"
                      }
                    </strong>
                  </div>

                  <div>
                    <span>
                      Authority
                    </span>

                    <strong>
                      {
                        selectedAssignment.organization_name
                      }
                    </strong>
                  </div>

                  <div>
                    <span>
                      Assigned
                    </span>

                    <strong>
                      {
                        formatDate(
                          selectedAssignment.assigned_at
                        )
                      }
                    </strong>
                  </div>
                </div>

                {selectedAssignment.assignment_notes && (
                  <div className="employee-authority-note">
                    <span>
                      AUTHORITY INSTRUCTIONS
                    </span>

                    <p>
                      {
                        selectedAssignment.assignment_notes
                      }
                    </p>
                  </div>
                )}

                <GoogleMap
                  latitude={
                    selectedAssignment.latitude
                  }
                  longitude={
                    selectedAssignment.longitude
                  }
                />

                {selectedAssignment.latitude &&
                  selectedAssignment.longitude && (
                  <a
                    className="employee-secondary-button employee-map-open"
                    href={
                      `https://www.google.com/maps?q=${selectedAssignment.latitude},${selectedAssignment.longitude}`
                    }
                    target="_blank"
                    rel="noreferrer"
                  >
                    Open in Google Maps ↗
                  </a>
                )}


                {/* STATUS ACTIONS */}
                <div className="employee-workflow-actions">
                  {selectedAssignment.assignment_status ===
                    "assigned" && (
                    <button
                      type="button"
                      className="employee-primary-button"
                      disabled={
                        actionLoading
                      }
                      onClick={() =>
                        updateAssignment(
                          "accept"
                        )
                      }
                    >
                      {
                        actionLoading
                          ? "Updating..."
                          : "Accept Job"
                      }
                    </button>
                  )}

                  {selectedAssignment.assignment_status ===
                    "accepted" && (
                    <button
                      type="button"
                      className="employee-primary-button"
                      disabled={
                        actionLoading
                      }
                      onClick={() =>
                        updateAssignment(
                          "start"
                        )
                      }
                    >
                      {
                        actionLoading
                          ? "Updating..."
                          : "Start Cleanup"
                      }
                    </button>
                  )}
                </div>


                {/* SCAN */}
                {[
                  "accepted",
                  "in_progress",
                ].includes(
                  selectedAssignment.assignment_status
                ) && (
                  <section className="employee-scan-panel">
                    <div>
                      <span>
                        OPTIONAL SITE SCAN
                      </span>

                      <h3>
                        Detect Waste & Get Safety Guidance
                      </h3>

                      <p>
                        This does not classify the
                        household complaint photo.
                        It scans waste at the actual
                        cleanup site for worker
                        guidance.
                      </p>
                    </div>

                    <input
                      type="file"
                      accept="image/png,image/jpeg,image/webp"
                      onChange={
                        (event) =>
                          setScanFile(
                            event.target.files?.[0] ||
                            null
                          )
                      }
                    />

                    <button
                      type="button"
                      className="employee-secondary-button"
                      disabled={
                        scanLoading ||
                        ragLoading
                      }
                      onClick={
                        scanWaste
                      }
                    >
                      {
                        scanLoading
                          ? "Running YOLO..."
                          : ragLoading
                            ? "Building RAG Guidance..."
                            : "Scan Waste & Get Guidance ✦"
                      }
                    </button>

                    {ragError && (
                      <div className="employee-error-message">
                        {
                          ragError
                        }
                      </div>
                    )}

                    {scanResult && (
                      <div className="employee-detection-result">
                        <strong>
                          YOLO Detection
                        </strong>

                        <p>
                          {
                            scanResult.detected_objects?.length ||
                            0
                          }
                          {" "}
                          object(s) detected with
                          {" "}
                          {
                            scanResult.architecture
                          }.
                        </p>

                        <div className="employee-detected-tags">
                          {
                            (
                              scanResult.detected_objects ||
                              []
                            ).map(
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
                                  {" "}
                                  (
                                  {
                                    Math.round(
                                      Number(
                                        object.confidence
                                      ) * 100
                                    )
                                  }
                                  %)
                                </span>
                              )
                            )
                          }
                        </div>
                      </div>
                    )}

                    {ragResult && (
                      <div className="employee-rag-result">
                        <div className="employee-rag-heading">
                          <span>
                            ✦ EMPLOYEE RAG
                          </span>

                          <strong>
                            {
                              ragResult.summary ||
                              "Worker guidance prepared."
                            }
                          </strong>
                        </div>

                        {
                          (
                            ragResult.work_instructions ||
                            ragResult.instructions ||
                            ragResult.guidance ||
                            ragResult.result
                              ?.work_instructions ||
                            []
                          ).map(
                            (
                              instruction,
                              index
                            ) => (
                              <article
                                key={
                                  `${instruction.class_name || index}`
                                }
                              >
                                <h4>
                                  {
                                    instruction.class_name ||
                                    instruction.waste_class ||
                                    instruction.category_name ||
                                    `Instruction ${index + 1}`
                                  }
                                </h4>

                                {
                                  [
                                    "immediate_actions",
                                    "safety_precautions",
                                    "segregation_steps",
                                    "collection_steps",
                                    "handling_steps",
                                    "transport_steps",
                                    "disposal_steps",
                                    "prohibited_actions",
                                    "emergency_steps",
                                  ].map(
                                    (key) =>
                                      Array.isArray(
                                        instruction[key]
                                      ) &&
                                      instruction[key].length >
                                        0 && (
                                        <div
                                          className="employee-rag-block"
                                          key={
                                            key
                                          }
                                        >
                                          <strong>
                                            {
                                              label(
                                                key
                                              )
                                            }
                                          </strong>

                                          <ul>
                                            {
                                              instruction[key].map(
                                                (
                                                  item,
                                                  itemIndex
                                                ) => (
                                                  <li
                                                    key={
                                                      itemIndex
                                                    }
                                                  >
                                                    {
                                                      item
                                                    }
                                                  </li>
                                                )
                                              )
                                            }
                                          </ul>
                                        </div>
                                      )
                                  )
                                }
                              </article>
                            )
                          )
                        }

                        <div className="employee-detailed-guidance-actions">
                          <div>
                            <strong>
                              Need more detail?
                            </strong>

                            <span>
                              Gemini will expand the existing
                              YOLO + Employee RAG result.
                            </span>
                          </div>

                          <select
                            value={
                              detailedLanguage
                            }
                            onChange={
                              (event) => {
                                setDetailedLanguage(
                                  event.target.value
                                );
                                setDetailedResult(null);
                                setDetailedError("");
                              }
                            }
                            disabled={
                              detailedLoading
                            }
                            aria-label="Detailed guidance language"
                          >
                            <option value="en">
                              English
                            </option>

                            <option value="bn">
                              বাংলা
                            </option>
                          </select>

                          <button
                            type="button"
                            className="employee-primary-button employee-detailed-button"
                            disabled={
                              detailedLoading ||
                              !ragAdviceId
                            }
                            onClick={
                              getDetailedGuidance
                            }
                          >
                            {
                              detailedLoading
                                ? "Getting Detailed Guidance..."
                                : "Get More Detailed Guidance ✦"
                            }
                          </button>
                        </div>

                        {detailedError && (
                          <div className="employee-error-message">
                            {
                              detailedError
                            }
                          </div>
                        )}

                        {detailedResult && (
                          <section className="employee-gemini-result">
                            <div className="employee-gemini-heading">
                              <span>
                                ✦ GEMINI + EMPLOYEE RAG
                              </span>

                              <strong>
                                {
                                  detailedResult.summary ||
                                  "Detailed worker guidance prepared."
                                }
                              </strong>
                            </div>

                            {(
                              detailedResult.guidance ||
                              []
                            ).map(
                              (
                                guidance,
                                index
                              ) => (
                                <article
                                  key={
                                    `${guidance.model_class_id || guidance.class_name || index}`
                                  }
                                >
                                  <h4>
                                    {
                                      guidance.display_name ||
                                      guidance.class_name ||
                                      `Guidance ${index + 1}`
                                    }
                                  </h4>

                                  {guidance.overview && (
                                    <p className="employee-gemini-overview">
                                      {
                                        guidance.overview
                                      }
                                    </p>
                                  )}

                                  {[
                                    "ppe_requirements",
                                    "site_preparation_steps",
                                    "collection_steps",
                                    "segregation_steps",
                                    "handling_precautions",
                                    "temporary_storage_steps",
                                    "transport_steps",
                                    "disposal_steps",
                                    "prohibited_actions",
                                    "emergency_actions",
                                    "supervisor_or_verification_notes",
                                  ].map(
                                    (key) =>
                                      Array.isArray(
                                        guidance[key]
                                      ) &&
                                      guidance[key].length >
                                        0 && (
                                        <div
                                          className="employee-rag-block"
                                          key={
                                            key
                                          }
                                        >
                                          <strong>
                                            {
                                              label(
                                                key
                                              )
                                            }
                                          </strong>

                                          <ul>
                                            {
                                              guidance[key].map(
                                                (
                                                  item,
                                                  itemIndex
                                                ) => (
                                                  <li
                                                    key={
                                                      itemIndex
                                                    }
                                                  >
                                                    {
                                                      item
                                                    }
                                                  </li>
                                                )
                                              )
                                            }
                                          </ul>
                                        </div>
                                      )
                                  )}
                                </article>
                              )
                            )}

                            {detailedResult.disclaimer && (
                              <p className="employee-gemini-disclaimer">
                                {
                                  detailedResult.disclaimer
                                }
                              </p>
                            )}
                          </section>
                        )}
                      </div>
                    )}
                  </section>
                )}


                {selectedAssignment.assignment_status ===
                  "in_progress" && (
                  <button
                    type="button"
                    className="employee-complete-button"
                    onClick={
                      openCompletion
                    }
                  >
                    Complete Cleanup & Report Waste
                  </button>
                )}


                {selectedAssignment.assignment_status ===
                  "completed" && (
                  <div className="employee-completed-summary">
                    <strong>
                      Cleanup Completed
                    </strong>

                    <p>
                      Authority verification:
                      {" "}
                      {
                        label(
                          selectedAssignment.cleanup_verification_status
                        )
                      }
                    </p>

                    {selectedAssignment.total_waste_kg !==
                      null &&
                      selectedAssignment.total_waste_kg !==
                        undefined && (
                        <p>
                          Total recorded:
                          {" "}
                          {
                            Number(
                              selectedAssignment.total_waste_kg
                            ).toFixed(2)
                          }
                          {" kg"}
                        </p>
                      )}
                  </div>
                )}
              </>
            )}
          </section>
        </div>
      )}


      {/* COMPLETION MODAL */}
      {completionOpen &&
        selectedAssignment && (
        <div
          className="employee-modal-backdrop employee-completion-layer"
          onClick={() =>
            setCompletionOpen(
              false
            )
          }
        >
          <form
            className="employee-modal employee-completion-modal"
            onSubmit={
              completeCleanup
            }
            onClick={
              (event) =>
                event.stopPropagation()
            }
          >
            <button
              type="button"
              className="employee-modal-close"
              onClick={() =>
                setCompletionOpen(
                  false
                )
              }
            >
              ×
            </button>

            <span className="employee-modal-eyebrow">
              CLEANUP REPORT
            </span>

            <h2>
              Report What You Collected
            </h2>

            <p>
              Enter waste amounts using the
              same 10 EcoLens model classes.
              The authority receives this
              record for verification before
              weight-based analytics use it.
            </p>

            <label className="employee-form-field">
              <span>
                After-cleanup photo *
              </span>

              <input
                type="file"
                accept="image/png,image/jpeg,image/webp"
                required
                onChange={
                  (event) =>
                    setAfterImage(
                      event.target.files?.[0] ||
                      null
                    )
                }
              />
            </label>

            <div className="employee-waste-table-header">
              <div>
                <strong>
                  Waste Breakdown
                </strong>

                <span>
                  Class + amount + handling
                </span>
              </div>

              <button
                type="button"
                className="employee-secondary-button"
                onClick={
                  addWasteRow
                }
              >
                + Add Type
              </button>
            </div>

            <div className="employee-waste-rows">
              {wasteRows.map(
                (
                  row,
                  index
                ) => (
                  <div
                    className="employee-waste-row"
                    key={
                      index
                    }
                  >
                    <select
                      value={
                        row.model_class_id
                      }
                      required
                      onChange={
                        (event) =>
                          updateWasteRow(
                            index,
                            "model_class_id",
                            event.target.value
                          )
                      }
                    >
                      <option value="">
                        Waste class
                      </option>

                      {modelClasses.map(
                        (modelClass) => (
                          <option
                            key={
                              modelClass.model_class_id
                            }
                            value={
                              modelClass.model_class_id
                            }
                          >
                            {
                              modelClass.display_name
                            }
                            {" — "}
                            {
                              modelClass.category_name
                            }
                          </option>
                        )
                      )}
                    </select>

                    <input
                      type="number"
                      min="0.01"
                      step="0.01"
                      required
                      placeholder="kg"
                      value={
                        row.weight_kg
                      }
                      onChange={
                        (event) =>
                          updateWasteRow(
                            index,
                            "weight_kg",
                            event.target.value
                          )
                      }
                    />

                    <select
                      value={
                        row.handling_method
                      }
                      onChange={
                        (event) =>
                          updateWasteRow(
                            index,
                            "handling_method",
                            event.target.value
                          )
                      }
                    >
                      <option value="recycled">
                        Recycled
                      </option>

                      <option value="composted">
                        Composted
                      </option>

                      <option value="special_collection">
                        Special Collection
                      </option>

                      <option value="controlled_disposal">
                        Controlled Disposal
                      </option>

                      <option value="other">
                        Other
                      </option>
                    </select>

                    <input
                      type="text"
                      placeholder="Notes"
                      value={
                        row.notes
                      }
                      onChange={
                        (event) =>
                          updateWasteRow(
                            index,
                            "notes",
                            event.target.value
                          )
                      }
                    />

                    {wasteRows.length >
                      1 && (
                      <button
                        type="button"
                        className="employee-remove-row"
                        onClick={() =>
                          removeWasteRow(
                            index
                          )
                        }
                      >
                        ×
                      </button>
                    )}
                  </div>
                )
              )}
            </div>

            <label className="employee-form-field">
              <span>
                Cleanup notes
              </span>

              <textarea
                rows="4"
                placeholder="Anything the authority should know..."
                value={
                  cleanupNotes
                }
                onChange={
                  (event) =>
                    setCleanupNotes(
                      event.target.value
                    )
                }
              />
            </label>

            {completionMessage && (
              <div className="employee-completion-message">
                {
                  completionMessage
                }
              </div>
            )}

            <button
              type="submit"
              className="employee-primary-button employee-full-button"
              disabled={
                completionLoading
              }
            >
              {
                completionLoading
                  ? "Submitting Cleanup..."
                  : "Submit Cleanup & Mark Completed"
              }
            </button>
          </form>
        </div>
      )}
    </main>
  );
}


export default EmployeeDashboard;