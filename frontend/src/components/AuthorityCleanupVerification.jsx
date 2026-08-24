import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  apiRequest,
} from "../services/api";

import "../styles/authority-employee-tools.css";


function formatDate(value) {
  if (!value) {
    return "—";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
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


function groupByMajorCategory(
  wasteBreakdown = []
) {
  const grouped = new Map();

  wasteBreakdown.forEach((item) => {
    const categoryName =
      item.category_name ||
      "Unmapped Waste";

    if (!grouped.has(categoryName)) {
      grouped.set(categoryName, {
        category_name: categoryName,
        total_weight_kg: 0,
        classes: [],
      });
    }

    const group = grouped.get(categoryName);
    const weight = Number(item.weight_kg || 0);

    group.total_weight_kg += weight;
    group.classes.push({
      model_class_id: item.model_class_id,
      class_name:
        item.class_name ||
        "Unknown class",
      weight_kg: weight,
      handling_method:
        item.handling_method ||
        "not recorded",
    });
  });

  return Array.from(grouped.values())
    .sort(
      (a, b) =>
        b.total_weight_kg -
        a.total_weight_kg
    );
}


function AuthorityCleanupVerification({
  onChanged,
}) {
  const [
    pendingCleanups,
    setPendingCleanups,
  ] = useState([]);

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    actionCleanupId,
    setActionCleanupId,
  ] = useState(null);

  const [
    message,
    setMessage,
  ] = useState("");

  const [
    error,
    setError,
  ] = useState("");


  const loadPendingCleanups =
    async () => {
      try {
        setLoading(true);
        setError("");

        const response =
          await apiRequest(
            "/api/authority/cleanup-verification/pending"
          );

        setPendingCleanups(
          response.cleanups || []
        );

      } catch (requestError) {
        setError(
          requestError.message
        );

      } finally {
        setLoading(false);
      }
    };


  useEffect(
    () => {
      loadPendingCleanups();
    },
    []
  );


  const pendingTotalKg =
    useMemo(
      () =>
        pendingCleanups.reduce(
          (sum, cleanup) =>
            sum + Number(
              cleanup.total_waste_kg || 0
            ),
          0
        ),
      [pendingCleanups]
    );


  const reviewCleanup =
    async (
      cleanupId,
      decision
    ) => {
      try {
        setActionCleanupId(
          cleanupId
        );
        setMessage("");
        setError("");

        const response =
          await apiRequest(
            `/api/authority/cleanup-verification/${cleanupId}/${decision}`,
            {
              method: "POST",
            }
          );

        setMessage(
          response.message
        );

        await loadPendingCleanups();

        if (
          typeof onChanged ===
          "function"
        ) {
          await onChanged();
        }

      } catch (requestError) {
        setError(
          requestError.message
        );

      } finally {
        setActionCleanupId(null);
      }
    };


  if (loading) {
    return (
      <div className="authority-tool-card">
        Loading pending cleanup reports...
      </div>
    );
  }


  return (
    <section className="authority-employee-tools">
      <div className="authority-verification-summary">
        <article className="authority-tool-card">
          <span className="authority-tool-eyebrow">
            PENDING CLEANUPS
          </span>
          <h3>
            {pendingCleanups.length}
          </h3>
          <p>
            Employee cleanup submissions waiting
            for this Authority to verify.
          </p>
        </article>

        <article className="authority-tool-card">
          <span className="authority-tool-eyebrow">
            PENDING WASTE WEIGHT
          </span>
          <h3>
            {pendingTotalKg.toFixed(2)} kg
          </h3>
          <p>
            This weight is excluded from verified
            Authority analytics until approved.
          </p>
        </article>
      </div>

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

      {pendingCleanups.length === 0 ? (
        <article className="authority-tool-card authority-verification-empty">
          <span className="authority-tool-eyebrow">
            ALL CAUGHT UP
          </span>
          <h3>
            No cleanup reports are waiting for verification.
          </h3>
          <p>
            New employee cleanup submissions for
            this Authority will appear here.
          </p>
        </article>
      ) : (
        <div className="authority-cleanup-list">
          {pendingCleanups.map(
            (cleanup) => {
              const categoryGroups =
                groupByMajorCategory(
                  cleanup.waste_breakdown || []
                );

              const busy =
                actionCleanupId ===
                cleanup.cleanup_id;

              return (
                <article
                  className="authority-cleanup-item authority-cleanup-review-card"
                  key={cleanup.cleanup_id}
                >
                  <div className="authority-cleanup-item-top">
                    <div>
                      <span className="authority-tool-eyebrow">
                        CLEANUP #{cleanup.cleanup_id}
                      </span>

                      <strong>
                        {cleanup.report_title}
                      </strong>

                      <span>
                        Employee: {cleanup.employee_name}
                      </span>

                      {cleanup.address_text && (
                        <span>
                          Location: {cleanup.address_text}
                        </span>
                      )}
                    </div>

                    <div className="authority-cleanup-total">
                      <strong>
                        {Number(
                          cleanup.total_waste_kg || 0
                        ).toFixed(2)} kg
                      </strong>
                      <span>
                        Total reported
                      </span>
                    </div>
                  </div>

                  <div className="authority-cleanup-meta-grid">
                    <span>
                      Recycled: {Number(
                        cleanup.recycled_waste_kg || 0
                      ).toFixed(2)} kg
                    </span>
                    <span>
                      Composted: {Number(
                        cleanup.composted_waste_kg || 0
                      ).toFixed(2)} kg
                    </span>
                    <span>
                      Properly disposed: {Number(
                        cleanup.properly_disposed_kg || 0
                      ).toFixed(2)} kg
                    </span>
                    <span>
                      Hazardous: {Number(
                        cleanup.hazardous_waste_kg || 0
                      ).toFixed(2)} kg
                    </span>
                  </div>

                  <div className="authority-major-category-list">
                    <div className="authority-category-heading">
                      <strong>
                        Major Waste Categories
                      </strong>
                      <span>
                        Used for Authority analytics after verification
                      </span>
                    </div>

                    {categoryGroups.length === 0 ? (
                      <div className="authority-category-warning">
                        No mapped waste breakdown was found for this cleanup.
                        Review before verifying.
                      </div>
                    ) : (
                      categoryGroups.map(
                        (group) => (
                          <div
                            className="authority-major-category-card"
                            key={group.category_name}
                          >
                            <div className="authority-major-category-top">
                              <strong>
                                {group.category_name}
                              </strong>
                              <span>
                                {group.total_weight_kg.toFixed(2)} kg
                              </span>
                            </div>

                            <div className="authority-cleanup-breakdown">
                              {group.classes.map(
                                (item, index) => (
                                  <span
                                    key={`${item.model_class_id}-${index}`}
                                  >
                                    {item.class_name}: {item.weight_kg.toFixed(2)} kg
                                  </span>
                                )
                              )}
                            </div>
                          </div>
                        )
                      )
                    )}
                  </div>

                  <span className="authority-cleanup-submitted">
                    Submitted: {formatDate(
                      cleanup.cleaned_at
                    )}
                  </span>

                  {cleanup.cleanup_notes && (
                    <p className="authority-cleanup-notes">
                      Notes: {cleanup.cleanup_notes}
                    </p>
                  )}

                  <div className="authority-cleanup-actions">
                    <button
                      type="button"
                      className="primary-dashboard-button"
                      disabled={busy}
                      onClick={() =>
                        reviewCleanup(
                          cleanup.cleanup_id,
                          "verify"
                        )
                      }
                    >
                      {busy
                        ? "Updating..."
                        : "Verify Cleanup"}
                    </button>

                    <button
                      type="button"
                      className="secondary-dashboard-button"
                      disabled={busy}
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
                </article>
              );
            }
          )}
        </div>
      )}
    </section>
  );
}


export default AuthorityCleanupVerification;
