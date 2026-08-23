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

import "../styles/admin-dashboard.css";


function AdminDashboard() {

  const navigate =
    useNavigate();


  const [
    admin,
    setAdmin,
  ] = useState(null);


  const [
    invites,
    setInvites,
  ] = useState([]);


  const [
    organizationName,
    setOrganizationName,
  ] = useState("");


  const [
    validDays,
    setValidDays,
  ] = useState(30);


  const [
    generatedInvite,
    setGeneratedInvite,
  ] = useState(null);


  const [
    feedback,
    setFeedback,
  ] = useState(null);


  const [
    loading,
    setLoading,
  ] = useState(true);


  const [
    creating,
    setCreating,
  ] = useState(false);


  // ========================================================
  // LOAD DASHBOARD
  // ========================================================

  const loadDashboard = async () => {

    try {

      const response =
        await apiRequest(
          "/api/admin/bootstrap"
        );


      setAdmin(
        response.admin
      );


      setInvites(
        response.authority_invites || []
      );


    } catch (error) {

      setFeedback(
        {
          type: "error",
          message: error.message,
        }
      );


      if (
        error.status === 401 ||
        error.status === 403
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

      setLoading(
        false
      );
    }
  };


  useEffect(() => {

    loadDashboard();

  }, []);


  // ========================================================
  // SUMMARY
  // ========================================================

  const summary =
    useMemo(
      () => {

        const active =
          invites.filter(
            (invite) =>
              invite.invite_status ===
              "active"
          ).length;


        const used =
          invites.filter(
            (invite) =>
              invite.invite_status ===
              "used"
          ).length;


        return {
          total: invites.length,
          active,
          used,
        };
      },
      [invites]
    );


  // ========================================================
  // GENERATE AUTHORITY CODE
  // ========================================================

  const handleGenerate = async (
    event
  ) => {

    event.preventDefault();

    setFeedback(null);
    setGeneratedInvite(null);


    try {

      setCreating(
        true
      );


      const response =
        await apiRequest(
          "/api/admin/authority-invites",
          {
            method: "POST",

            body:
              JSON.stringify(
                {
                  organization_name:
                    organizationName,

                  valid_days:
                    Number(
                      validDays
                    ),
                }
              ),
          }
        );


      setGeneratedInvite(
        response.invite
      );


      setOrganizationName(
        ""
      );


      setFeedback(
        {
          type: "success",
          message:
            "Authority registration code generated successfully.",
        }
      );


      const refreshed =
        await apiRequest(
          "/api/admin/authority-invites"
        );


      setInvites(
        refreshed.invites || []
      );


    } catch (error) {

      setFeedback(
        {
          type: "error",
          message: error.message,
        }
      );


    } finally {

      setCreating(
        false
      );
    }
  };


  // ========================================================
  // COPY CODE
  // ========================================================

  const copyInviteCode = async () => {

    if (
      !generatedInvite?.invite_code
    ) {
      return;
    }


    try {

      await navigator.clipboard.writeText(
        generatedInvite.invite_code
      );


      setFeedback(
        {
          type: "success",
          message:
            "Registration code copied.",
        }
      );


    } catch {

      setFeedback(
        {
          type: "error",
          message:
            "Could not copy automatically. Select the code and copy it manually.",
        }
      );
    }
  };


  // ========================================================
  // LOGOUT
  // ========================================================

  const handleLogout = async () => {

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
  // LOADING
  // ========================================================

  if (loading) {

    return (
      <main className="admin-page admin-centered-state">

        <div className="admin-state-card">
          Loading EcoLens Admin...
        </div>

      </main>
    );
  }


  // ========================================================
  // PAGE
  // ========================================================

  return (

    <main className="admin-page">


      <header className="admin-header">

        <div className="admin-brand">

          <img
            src={logo}
            alt="EcoLens"
          />

          <div>
            <strong>
              EcoLens
            </strong>

            <span>
              Administrator Console
            </span>
          </div>

        </div>


        <div className="admin-header-actions">

          <div className="admin-identity">
            <span>
              ADMINISTRATOR
            </span>

            <strong>
              {admin?.full_name ||
                "EcoLens Administrator"}
            </strong>
          </div>


          <button
            type="button"
            className="admin-logout"
            onClick={
              handleLogout
            }
          >
            Log Out
          </button>

        </div>

      </header>


      <section className="admin-shell">


        <section className="admin-hero">

          <div>

            <span className="admin-eyebrow">
              AUTHORITY REGISTRATION CONTROL
            </span>

            <h1>
              Manage trusted
              {" "}
              <span>
                Community Authority access.
              </span>
            </h1>

            <p>
              Generate one-time organization-bound
              registration codes for Community
              Authorities. The organization name
              entered here must match the name used
              during authority signup.
            </p>

          </div>


          <div className="admin-summary-grid">

            <article>
              <span>
                Total Codes
              </span>

              <strong>
                {summary.total}
              </strong>
            </article>


            <article>
              <span>
                Active
              </span>

              <strong>
                {summary.active}
              </strong>
            </article>


            <article>
              <span>
                Used
              </span>

              <strong>
                {summary.used}
              </strong>
            </article>

          </div>

        </section>


        {feedback && (

          <div
            className={
              `admin-feedback ${
                feedback.type ===
                "success"
                  ? "admin-feedback-success"
                  : "admin-feedback-error"
              }`
            }
          >
            {feedback.message}
          </div>

        )}


        <section className="admin-main-grid">


          <article className="admin-panel">

            <div className="admin-panel-heading">

              <span>
                NEW AUTHORITY
              </span>

              <h2>
                Generate registration code
              </h2>

              <p>
                Enter the exact organization name
                you expect the Community Authority
                to use during signup.
              </p>

            </div>


            <form
              className="admin-form"
              onSubmit={
                handleGenerate
              }
            >

              <label>

                <span>
                  Organization Name
                </span>

                <input
                  type="text"
                  maxLength="190"
                  placeholder="Example: Dhaka North City Corporation"
                  value={
                    organizationName
                  }
                  onChange={
                    (event) => {
                      setOrganizationName(
                        event.target.value
                      );

                      setFeedback(
                        null
                      );
                    }
                  }
                  required
                />

              </label>


              <label>

                <span>
                  Code Validity
                </span>

                <select
                  value={
                    validDays
                  }
                  onChange={
                    (event) =>
                      setValidDays(
                        event.target.value
                      )
                  }
                >
                  <option value="7">
                    7 days
                  </option>

                  <option value="14">
                    14 days
                  </option>

                  <option value="30">
                    30 days
                  </option>

                  <option value="60">
                    60 days
                  </option>

                  <option value="90">
                    90 days
                  </option>
                </select>

              </label>


              <button
                type="submit"
                className="admin-primary-button"
                disabled={
                  creating
                }
              >
                {creating
                  ? "Generating..."
                  : "Generate Authority Code"}
              </button>

            </form>


            {generatedInvite && (

              <div className="admin-generated-card">

                <span className="admin-generated-label">
                  NEW REGISTRATION CODE
                </span>

                <strong>
                  {
                    generatedInvite
                      .organization_name
                  }
                </strong>

                <div className="admin-code-row">

                  <code>
                    {
                      generatedInvite
                        .invite_code
                    }
                  </code>

                  <button
                    type="button"
                    onClick={
                      copyInviteCode
                    }
                  >
                    Copy
                  </button>

                </div>


                <p>
                  Expires:
                  {" "}
                  {
                    new Date(
                      generatedInvite
                        .expires_at
                    )
                    .toLocaleString()
                  }
                </p>


                <small>
                  Copy this code now. EcoLens stores
                  only the secure digest, so the raw
                  code is not shown again in the
                  invitation history.
                </small>

              </div>

            )}

          </article>


          <article className="admin-panel admin-history-panel">

            <div className="admin-panel-heading">

              <span>
                REGISTRATION HISTORY
              </span>

              <h2>
                Authority invitations
              </h2>

              <p>
                Review which organization-bound
                invitations are active, used,
                expired, or revoked.
              </p>

            </div>


            {invites.length === 0
              ? (

                <div className="admin-empty-state">
                  No authority registration codes
                  have been generated yet.
                </div>

              )
              : (

                <div className="admin-invite-list">

                  {invites.map(
                    (invite) => (

                      <article
                        className="admin-invite-item"
                        key={
                          invite.invite_id
                        }
                      >

                        <div>

                          <strong>
                            {
                              invite
                                .organization_name ||
                              "Organization not recorded"
                            }
                          </strong>

                          <span>
                            Invite #
                            {
                              invite.invite_id
                            }
                          </span>

                        </div>


                        <div className="admin-invite-meta">

                          <span
                            className={
                              `admin-status admin-status-${
                                invite
                                  .invite_status
                              }`
                            }
                          >
                            {
                              invite
                                .invite_status
                            }
                          </span>

                          <small>
                            Expires
                            {" "}
                            {
                              invite.expires_at
                                ? new Date(
                                    invite.expires_at
                                  )
                                  .toLocaleDateString()
                                : "No expiry"
                            }
                          </small>

                        </div>

                      </article>

                    )
                  )}

                </div>

              )}

          </article>

        </section>


        <section className="admin-note">

          <strong>
            How approval works
          </strong>

          <p>
            A Community Authority becomes active
            only when its signup code is valid and
            the submitted organization name matches
            the organization stored with that
            administrator-issued code.
          </p>

        </section>


      </section>

    </main>
  );
}


export default AdminDashboard;