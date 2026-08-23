import {
  useEffect,
  useState,
} from "react";

import {
  apiRequest,
} from "../services/api";

import "../styles/authority-employee-tools.css";


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
      dateStyle:
        "medium",

      timeStyle:
        "short",
    }
  );
}


function AuthorityEmployeeTools() {
  const [
    invites,
    setInvites,
  ] = useState([]);

  const [
    pendingCleanups,
    setPendingCleanups,
  ] = useState([]);

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    inviteLoading,
    setInviteLoading,
  ] = useState(false);

  const [
    inviteResult,
    setInviteResult,
  ] = useState(null);

  const [
    message,
    setMessage,
  ] = useState("");

  const [
    error,
    setError,
  ] = useState("");

  const [
    form,
    setForm,
  ] = useState({
    employee_code:
      "",

    job_title:
      "Municipal Employee",

    expires_days:
      7,
  });


  const loadTools =
    async () => {
      try {
        setLoading(true);
        setError("");

        const [
          inviteResponse,
          cleanupResponse,
        ] =
          await Promise.all([
            apiRequest(
              "/api/authority/employee-invites"
            ),

            apiRequest(
              "/api/authority/cleanup-verification/pending"
            ),
          ]);

        setInvites(
          inviteResponse.invites ||
          []
        );

        setPendingCleanups(
          cleanupResponse.cleanups ||
          []
        );

      } catch (
        requestError
      ) {
        setError(
          requestError.message
        );

      } finally {
        setLoading(false);
      }
    };


  useEffect(
    () => {
      loadTools();
    },
    []
  );


  const createInvite =
    async (
      event
    ) => {
      event.preventDefault();

      try {
        setInviteLoading(
          true
        );

        setMessage("");
        setError("");
        setInviteResult(null);

        const response =
          await apiRequest(
            "/api/authority/employee-invites",
            {
              method:
                "POST",

              body:
                JSON.stringify(
                  {
                    employee_code:
                      form.employee_code,

                    job_title:
                      form.job_title,

                    expires_days:
                      Number(
                        form.expires_days
                      ),
                  }
                ),
            }
          );

        setInviteResult(
          response.invite
        );

        setMessage(
          response.message
        );

        setForm(
          {
            employee_code:
              "",

            job_title:
              "Municipal Employee",

            expires_days:
              7,
          }
        );

        await loadTools();

      } catch (
        requestError
      ) {
        setError(
          requestError.message
        );

      } finally {
        setInviteLoading(
          false
        );
      }
    };


  const copyInvite =
    async () => {
      if (
        !inviteResult
          ?.invite_code
      ) {
        return;
      }

      try {
        await navigator.clipboard.writeText(
          inviteResult
            .invite_code
        );

        setMessage(
          "Invitation code copied."
        );

      } catch {
        setMessage(
          "Copy failed. Select the code manually."
        );
      }
    };


  const revokeInvite =
    async (
      inviteId
    ) => {
      try {
        setMessage("");
        setError("");

        const response =
          await apiRequest(
            `/api/authority/employee-invites/${inviteId}/revoke`,
            {
              method:
                "POST",
            }
          );

        setMessage(
          response.message
        );

        await loadTools();

      } catch (
        requestError
      ) {
        setError(
          requestError.message
        );
      }
    };


  const reviewCleanup =
    async (
      cleanupId,
      decision
    ) => {
      try {
        setMessage("");
        setError("");

        const response =
          await apiRequest(
            `/api/authority/cleanup-verification/${cleanupId}/${decision}`,
            {
              method:
                "POST",
            }
          );

        setMessage(
          response.message
        );

        await loadTools();

      } catch (
        requestError
      ) {
        setError(
          requestError.message
        );
      }
    };


  if (loading) {
    return (
      <div className="authority-employee-tools">
        Loading employee tools...
      </div>
    );
  }


  return (
    <section className="authority-employee-tools">
      <div className="authority-tool-grid">

        {/* CREATE EMPLOYEE CODE */}
        <article className="authority-tool-card">
          <span className="authority-tool-eyebrow">
            EMPLOYEE ACCESS
          </span>

          <h3>
            Create Employee Invitation
          </h3>

          <p>
            The Community Authority generates
            this code and gives it to a municipal
            employee. The employee uses the code
            during signup. Only the secure digest
            is stored in the database.
          </p>

          <form
            className="authority-invite-form"
            onSubmit={
              createInvite
            }
          >
            <input
              type="text"
              placeholder="Employee code, e.g. EMP-W17-004"
              value={
                form.employee_code
              }
              onChange={
                (event) =>
                  setForm(
                    (
                      previous
                    ) => ({
                      ...previous,

                      employee_code:
                        event.target.value,
                    })
                  )
              }
            />

            <input
              type="text"
              placeholder="Job title"
              required
              value={
                form.job_title
              }
              onChange={
                (event) =>
                  setForm(
                    (
                      previous
                    ) => ({
                      ...previous,

                      job_title:
                        event.target.value,
                    })
                  )
              }
            />

            <input
              type="number"
              min="1"
              max="30"
              required
              value={
                form.expires_days
              }
              onChange={
                (event) =>
                  setForm(
                    (
                      previous
                    ) => ({
                      ...previous,

                      expires_days:
                        event.target.value,
                    })
                  )
              }
              title="Expiry days"
            />

            <button
              type="submit"
              className="primary-dashboard-button"
              disabled={
                inviteLoading
              }
            >
              {
                inviteLoading
                  ? "Creating..."
                  : "Generate Code"
              }
            </button>
          </form>

          {inviteResult && (
            <div className="authority-invite-result">
              <strong>
                Give this one-time code
                to the employee:
              </strong>

              <div className="authority-invite-code">
                <code>
                  {
                    inviteResult.invite_code
                  }
                </code>

                <button
                  type="button"
                  className="secondary-dashboard-button"
                  onClick={
                    copyInvite
                  }
                >
                  Copy
                </button>
              </div>

              <small>
                Employee code:
                {" "}
                {
                  inviteResult.employee_code
                }
                {" • "}
                Expires:
                {" "}
                {
                  formatDate(
                    inviteResult.expires_at
                  )
                }
              </small>
            </div>
          )}
        </article>


        {/* RECENT INVITES */}
        <article className="authority-tool-card">
          <span className="authority-tool-eyebrow">
            RECENT INVITATIONS
          </span>

          <h3>
            Invitation Status
          </h3>

          <p>
            Active codes can be used once.
            Used, expired or revoked codes
            cannot create another employee.
          </p>

          <div className="authority-invite-list">
            {invites.length ===
              0 && (
              <div>
                No employee invitations yet.
              </div>
            )}

            {invites
              .slice(
                0,
                6
              )
              .map(
                (invite) => (
                  <div
                    className="authority-invite-item"
                    key={
                      invite.invite_id
                    }
                  >
                    <div className="authority-invite-item-top">
                      <div>
                        <strong>
                          {
                            invite.employee_code
                          }
                        </strong>

                        <span>
                          {
                            invite.job_title ||
                            "Municipal Employee"
                          }
                        </span>
                      </div>

                      <span className="authority-tool-status">
                        {
                          invite.invite_status
                        }
                      </span>
                    </div>

                    <span>
                      Expires:
                      {" "}
                      {
                        formatDate(
                          invite.expires_at
                        )
                      }
                    </span>

                    {invite.invite_status ===
                      "active" && (
                      <button
                        type="button"
                        className="secondary-dashboard-button"
                        onClick={() =>
                          revokeInvite(
                            invite.invite_id
                          )
                        }
                      >
                        Revoke
                      </button>
                    )}
                  </div>
                )
              )}
          </div>
        </article>
      </div>


      {/* CLEANUP VERIFICATION */}
      <article className="authority-tool-card">
        <span className="authority-tool-eyebrow">
          CLEANUP ANALYTICS CONTROL
        </span>

        <h3>
          Verify Employee Cleanup Reports
        </h3>

        <p>
          Employees report the amount and type
          of waste they collected using EcoLens
          model classes. These records stay
          pending until this authority verifies
          them. Your existing authority analytics
          can then safely use verified cleanup
          data.
        </p>

        <div className="authority-cleanup-list">
          {pendingCleanups.length ===
            0 && (
            <div>
              No cleanup reports are waiting
              for verification.
            </div>
          )}

          {pendingCleanups.map(
            (cleanup) => (
              <div
                className="authority-cleanup-item"
                key={
                  cleanup.cleanup_id
                }
              >
                <div className="authority-cleanup-item-top">
                  <div>
                    <strong>
                      {
                        cleanup.report_title
                      }
                    </strong>

                    <span>
                      Employee:
                      {" "}
                      {
                        cleanup.employee_name
                      }
                    </span>
                  </div>

                  <strong>
                    {
                      Number(
                        cleanup.total_waste_kg
                      ).toFixed(2)
                    }
                    {" kg"}
                  </strong>
                </div>

                <div className="authority-cleanup-breakdown">
                  {
                    (
                      cleanup.waste_breakdown ||
                      []
                    ).map(
                      (
                        item,
                        index
                      ) => (
                        <span
                          key={
                            `${item.model_class_id}-${index}`
                          }
                        >
                          {
                            item.class_name
                          }
                          :
                          {" "}
                          {
                            Number(
                              item.weight_kg
                            ).toFixed(2)
                          }
                          {" kg"}
                        </span>
                      )
                    )
                  }
                </div>

                <span>
                  Submitted:
                  {" "}
                  {
                    formatDate(
                      cleanup.cleaned_at
                    )
                  }
                </span>

                <div className="authority-cleanup-actions">
                  <button
                    type="button"
                    className="primary-dashboard-button"
                    onClick={() =>
                      reviewCleanup(
                        cleanup.cleanup_id,
                        "verify"
                      )
                    }
                  >
                    Verify
                  </button>

                  <button
                    type="button"
                    className="secondary-dashboard-button"
                    onClick={() =>
                      reviewCleanup(
                        cleanup.cleanup_id,
                        "reject"
                      )
                    }
                  >
                    Reject
                  </button>
                </div>
              </div>
            )
          )}
        </div>
      </article>


      {message && (
        <div className="authority-tool-message">
          {message}
        </div>
      )}

      {error && (
        <div className="authority-tool-error">
          {error}
        </div>
      )}
    </section>
  );
}


export default AuthorityEmployeeTools;