import {
  useEffect,
  useState,
} from "react";

import {
  Link,
} from "react-router-dom";

import logo from "../assets/ecolens-logo.png";

import {
  apiRequest,
} from "../services/api";

import "../styles/signup.css";
import "../styles/signup-location.css";


const roleOptions = [
  {
    id: "household",

    title: "Household",

    subtitle:
      "For individuals and families",

    description:
      "Identify household waste and receive simple, practical disposal guidance.",

    icon: "home",
  },

  {
    id: "employee",

    title: "Municipal Employee",

    subtitle:
      "For field and cleaning workers",

    description:
      "Access cleanup tasks, safety guidance, and worker-specific waste handling instructions.",

    icon: "worker",
  },

  {
    id: "authority",

    title: "Community Authority",

    subtitle:
      "For municipal management",

    description:
      "Manage community reports, employees, analytics, and environmental recommendations.",

    icon: "authority",
  },
];


function RoleIcon({
  type,
}) {

  if (type === "home") {

    return (
      <svg
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path
          d="M3.5 10.5 12 3l8.5 7.5v9A1.5 1.5 0 0 1 19 21h-5v-6h-4v6H5a1.5 1.5 0 0 1-1.5-1.5v-9Z"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.7"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    );
  }


  if (type === "worker") {

    return (
      <svg
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path
          d="M7.5 10V8a4.5 4.5 0 0 1 9 0v2"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.7"
        />

        <path
          d="M5 10h14M8 10v2m8-2v2"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.7"
        />

        <circle
          cx="12"
          cy="14"
          r="3"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.7"
        />

        <path
          d="M6 21c.8-3 2.8-4.5 6-4.5s5.2 1.5 6 4.5"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.7"
        />
      </svg>
    );
  }


  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path
        d="M3 10h18M5 10v9m4-9v9m6-9v9m4-9v9M3 19h18M12 3l9 5H3l9-5Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}


function SignupPage() {

  const [
    selectedRole,
    setSelectedRole,
  ] = useState(
    "household"
  );


  const [
    showPassword,
    setShowPassword,
  ] = useState(false);


  const [
    householdAreas,
    setHouseholdAreas,
  ] = useState([]);


  const [
    authorityWards,
    setAuthorityWards,
  ] = useState([]);


  const [
    locationsLoading,
    setLocationsLoading,
  ] = useState(true);


  const [
    submitting,
    setSubmitting,
  ] = useState(false);


  const [
    feedback,
    setFeedback,
  ] = useState(null);


  const [
    formData,
    setFormData,
  ] = useState({

    fullName: "",

    email: "",

    phone: "",

    addressText: "",

    areaRegionId: "",

    wardRegionIds: [],

    inviteCode: "",

    organizationName: "",

    password: "",

    confirmPassword: "",
  });


  // ========================================================
  // LOAD LOCATIONS
  // ========================================================

  useEffect(() => {

    async function loadLocations() {

      try {

        const data = await apiRequest(
          "/api/auth/signup-locations"
        );

        setHouseholdAreas(
          data.household_areas || []
        );

        setAuthorityWards(
          data.authority_wards || []
        );

      } catch (error) {

        setFeedback({
          type: "error",

          message:
            error.message,
        });

      } finally {

        setLocationsLoading(
          false
        );
      }
    }


    loadLocations();

  }, []);


  // ========================================================
  // NORMAL FIELD CHANGE
  // ========================================================

  const handleChange = (
    event
  ) => {

    const {
      name,
      value,
    } = event.target;


    setFormData(
      (previous) => ({

        ...previous,

        [name]: value,
      })
    );


    setFeedback(null);
  };


  // ========================================================
  // ROLE CHANGE
  // ========================================================

  const chooseRole = (
    role
  ) => {

    setSelectedRole(role);

    setFeedback(null);


    setFormData(
      (previous) => ({

        ...previous,

        areaRegionId: "",

        wardRegionIds: [],

        inviteCode: "",

        organizationName: "",
      })
    );
  };


  // ========================================================
  // AUTHORITY WARD CHECKBOX
  // ========================================================

  const toggleWard = (
    wardRegionId
  ) => {

    const wardId = Number(
      wardRegionId
    );


    setFormData(
      (previous) => {

        const alreadySelected =
          previous.wardRegionIds.includes(
            wardId
          );


        const nextWardIds =
          alreadySelected

            ? previous.wardRegionIds.filter(
                (id) =>
                  id !== wardId
              )

            : [
                ...previous.wardRegionIds,
                wardId,
              ];


        return {
          ...previous,

          wardRegionIds:
            nextWardIds,
        };
      }
    );


    setFeedback(null);
  };


  // ========================================================
  // SUBMIT
  // ========================================================

  const handleSubmit = async (
    event
  ) => {

    event.preventDefault();

    setFeedback(null);


    if (
      formData.password !==
      formData.confirmPassword
    ) {

      setFeedback({
        type: "error",

        message:
          "Passwords do not match.",
      });

      return;
    }


    if (
      formData.password.length < 8
    ) {

      setFeedback({
        type: "error",

        message:
          "Password must contain at least 8 characters.",
      });

      return;
    }


    if (
      selectedRole ===
        "household"

      && !formData.areaRegionId
    ) {

      setFeedback({
        type: "error",

        message:
          "Please select your local area.",
      });

      return;
    }


    if (
      selectedRole ===
        "authority"

      && formData
        .wardRegionIds
        .length === 0
    ) {

      setFeedback({
        type: "error",

        message:
          "Please select at least one ward covered by your authority.",
      });

      return;
    }


    const requestBody = {

      role:
        selectedRole,

      fullName:
        formData.fullName,

      email:
        formData.email,

      phone:
        formData.phone,

      addressText:
        formData.addressText,

      password:
        formData.password,


      areaRegionId:
        selectedRole ===
          "household"

          ? Number(
              formData.areaRegionId
            )

          : null,


      wardRegionIds:
        selectedRole ===
          "authority"

          ? formData.wardRegionIds

          : [],


      inviteCode:
        selectedRole ===
          "household"

          ? null

          : formData.inviteCode,


      organizationName:
        selectedRole ===
          "authority"

          ? formData.organizationName

          : null,
    };


    try {

      setSubmitting(true);


      const response =
        await apiRequest(
          "/api/auth/signup",
          {
            method: "POST",

            body:
              JSON.stringify(
                requestBody
              ),
          }
        );


      setFeedback({
        type: "success",

        message:
          response.message,
      });


      setFormData({

        fullName: "",

        email: "",

        phone: "",

        addressText: "",

        areaRegionId: "",

        wardRegionIds: [],

        inviteCode: "",

        organizationName: "",

        password: "",

        confirmPassword: "",
      });


    } catch (error) {

      setFeedback({
        type: "error",

        message:
          error.message,
      });


    } finally {

      setSubmitting(false);
    }
  };


  // ========================================================
  // CARD TILT
  // ========================================================

  const handleCardMove = (
    event
  ) => {

    const card =
      event.currentTarget;

    const rect =
      card.getBoundingClientRect();

    const x =
      event.clientX -
      rect.left;

    const y =
      event.clientY -
      rect.top;


    const rotateY =
      (
        x /
        rect.width -
        0.5
      ) * 5;


    const rotateX =
      (
        y /
        rect.height -
        0.5
      ) * -5;


    card.style.setProperty(
      "--rotate-x",
      `${rotateX}deg`
    );


    card.style.setProperty(
      "--rotate-y",
      `${rotateY}deg`
    );
  };


  const resetCardTilt = (
    event
  ) => {

    event.currentTarget
      .style
      .setProperty(
        "--rotate-x",
        "0deg"
      );


    event.currentTarget
      .style
      .setProperty(
        "--rotate-y",
        "0deg"
      );
  };


  return (
    <main className="signup-page">

      <div className="signup-glow signup-glow-one" />

      <div className="signup-glow signup-glow-two" />


      {/* HEADER */}

      <header className="signup-header">

        <Link
          to="/"
          className="signup-brand"
        >

          <img
            src={logo}
            alt="EcoLens"
          />

          <span>
            EcoLens
          </span>

        </Link>


        <div className="signup-login-link">

          <span>
            Already have an account?
          </span>

          <Link to="/login">
            Log In
          </Link>

        </div>

      </header>


      <section className="signup-container">

        {/* HEADING */}

        <div className="signup-heading">

          <span className="signup-eyebrow">
            JOIN ECOLENS
          </span>

          <h1>
            How will you use

            <span>
              {" "}EcoLens?
            </span>
          </h1>

          <p>
            Choose the role that best
            describes you. EcoLens will
            personalise your experience
            around the work you need to do.
          </p>

        </div>


        {/* ROLE CARDS */}

        <div className="role-grid">

          {roleOptions.map(
            (role) => (

              <button
                key={role.id}

                type="button"

                className={
                  `role-card ${
                    selectedRole ===
                    role.id

                      ? "role-card-selected"

                      : ""
                  }`
                }

                onClick={() =>
                  chooseRole(
                    role.id
                  )
                }

                onMouseMove={
                  handleCardMove
                }

                onMouseLeave={
                  resetCardTilt
                }
              >

                <div className="role-card-top">

                  <div className="role-icon">

                    <RoleIcon
                      type={
                        role.icon
                      }
                    />

                  </div>


                  <div
                    className={
                      `role-check ${
                        selectedRole ===
                        role.id

                          ? "role-check-visible"

                          : ""
                      }`
                    }
                  >
                    ✓
                  </div>

                </div>


                <h2>
                  {role.title}
                </h2>


                <span className="role-subtitle">
                  {role.subtitle}
                </span>


                <p>
                  {role.description}
                </p>

              </button>
            )
          )}

        </div>


        {/* FORM */}

        <div className="signup-form-card">

          <div className="form-heading">

            <div>

              <span>

                {selectedRole ===
                  "household"

                  ? "HOUSEHOLD ACCOUNT"

                  : selectedRole ===
                    "employee"

                    ? "EMPLOYEE ACCOUNT"

                    : "AUTHORITY ACCOUNT"}

              </span>


              <h2>
                Create your account
              </h2>

            </div>


            <div className="selected-role-badge">

              {selectedRole ===
                "household"

                ? "Household"

                : selectedRole ===
                  "employee"

                  ? "Municipal Employee"

                  : "Community Authority"}

            </div>

          </div>


          {/* EMPLOYEE NOTICE */}

          {selectedRole ===
            "employee" && (

            <div className="role-notice">

              <strong>
                Employee verification
              </strong>

              <p>
                Enter the registration code
                issued by your Community
                Authority. Your work region is
                inherited from that authority,
                so you do not choose it manually.
              </p>

            </div>
          )}


          {/* AUTHORITY NOTICE */}

          {selectedRole ===
            "authority" && (

            <div className="role-notice">

              <strong>
                Authority coverage
              </strong>

              <p>
                Select every ward your authority
                is responsible for. EcoLens will
                later use reports from all these
                wards when producing community
                analytics and recommendations.
              </p>

            </div>
          )}


          <form
            className="signup-form"

            onSubmit={
              handleSubmit
            }
          >

            <div className="form-grid">


              {/* NAME */}

              <label className="form-field">

                <span>
                  Full Name
                </span>

                <input
                  type="text"

                  name="fullName"

                  placeholder="Enter your full name"

                  value={
                    formData.fullName
                  }

                  onChange={
                    handleChange
                  }

                  maxLength="120"

                  required
                />

              </label>


              {/* EMAIL */}

              <label className="form-field">

                <span>
                  Email Address
                </span>

                <input
                  type="email"

                  name="email"

                  placeholder="you@example.com"

                  value={
                    formData.email
                  }

                  onChange={
                    handleChange
                  }

                  maxLength="190"

                  required
                />

              </label>


              {/* PHONE */}

              <label className="form-field">

                <span>
                  Phone Number
                </span>

                <input
                  type="tel"

                  name="phone"

                  placeholder="+880 1XXXXXXXXX"

                  value={
                    formData.phone
                  }

                  onChange={
                    handleChange
                  }

                  maxLength="30"
                />

              </label>


              {/* ADDRESS */}

              <label className="form-field">

                <span>
                  Address
                </span>

                <input
                  type="text"

                  name="addressText"

                  placeholder="Street, road or house information"

                  value={
                    formData.addressText
                  }

                  onChange={
                    handleChange
                  }

                  maxLength="500"
                />

              </label>


              {/* HOUSEHOLD AREA */}

              {selectedRole ===
                "household" && (

                <label className="form-field form-field-wide">

                  <span>
                    Your Local Area
                  </span>

                  <select
                    className="location-select"

                    name="areaRegionId"

                    value={
                      formData.areaRegionId
                    }

                    onChange={
                      handleChange
                    }

                    disabled={
                      locationsLoading
                    }

                    required
                  >

                    <option value="">

                      {locationsLoading

                        ? "Loading areas..."

                        : "Select your area"}

                    </option>


                    {householdAreas.map(
                      (area) => (

                        <option
                          key={
                            area.area_region_id
                          }

                          value={
                            area.area_region_id
                          }
                        >

                          {area.area_name}

                          {" — "}

                          {area.ward_name}

                        </option>

                      )
                    )}

                  </select>


                  <small className="location-help">

                    Your ward is determined
                    automatically from the
                    selected area.

                  </small>

                </label>
              )}


              {/* EMPLOYEE INVITE */}

              {selectedRole ===
                "employee" && (

                <label className="form-field form-field-wide">

                  <span>
                    Employee Invitation Code
                  </span>

                  <input
                    type="text"

                    name="inviteCode"

                    placeholder="Enter the code provided by your authority"

                    value={
                      formData.inviteCode
                    }

                    onChange={
                      handleChange
                    }

                    required
                  />

                </label>
              )}


              {/* AUTHORITY ORGANISATION */}

              {selectedRole ===
                "authority" && (

                <>

                  <label className="form-field">

                    <span>
                      Organization Name
                    </span>

                    <input
                      type="text"

                      name="organizationName"

                      placeholder="Municipality or community authority"

                      value={
                        formData.organizationName
                      }

                      onChange={
                        handleChange
                      }

                      maxLength="190"

                      required
                    />

                  </label>


                  <label className="form-field">

                    <span>
                      Authority Registration Code
                    </span>

                    <input
                      type="text"

                      name="inviteCode"

                      placeholder="Enter your authorised code"

                      value={
                        formData.inviteCode
                      }

                      onChange={
                        handleChange
                      }

                      required
                    />

                  </label>


                  {/* WARD COVERAGE */}

                  <div className="form-field form-field-wide">

                    <span>
                      Wards Under Your Authority
                    </span>


                    <div className="ward-selection-grid">

                      {locationsLoading && (

                        <div className="ward-loading">
                          Loading available wards...
                        </div>

                      )}


                      {!locationsLoading &&

                        authorityWards.map(
                          (ward) => {

                            const wardId =
                              Number(
                                ward.ward_region_id
                              );


                            const selected =
                              formData
                                .wardRegionIds
                                .includes(
                                  wardId
                                );


                            return (

                              <label
                                key={
                                  wardId
                                }

                                className={
                                  `ward-option ${
                                    selected

                                      ? "ward-option-selected"

                                      : ""
                                  }`
                                }
                              >

                                <input
                                  type="checkbox"

                                  checked={
                                    selected
                                  }

                                  onChange={() =>
                                    toggleWard(
                                      wardId
                                    )
                                  }
                                />


                                <div>

                                  <strong>
                                    {ward.ward_name}
                                  </strong>


                                  <span>
                                    {ward.zone_name}
                                  </span>


                                  {ward.area_summary && (

                                    <p>
                                      {
                                        ward.area_summary
                                      }
                                    </p>

                                  )}

                                </div>


                                <span className="ward-check">
                                  {selected
                                    ? "✓"
                                    : ""}
                                </span>

                              </label>
                            );
                          }
                        )}

                    </div>


                    <small className="location-help">

                      Selected:
                      {" "}

                      {
                        formData
                          .wardRegionIds
                          .length
                      }

                      {" "}
                      ward(s)

                    </small>

                  </div>

                </>
              )}


              {/* PASSWORD */}

              <label className="form-field">

                <span>
                  Password
                </span>


                <div className="password-field">

                  <input
                    type={
                      showPassword

                        ? "text"

                        : "password"
                    }

                    name="password"

                    placeholder="At least 8 characters"

                    value={
                      formData.password
                    }

                    onChange={
                      handleChange
                    }

                    minLength="8"

                    required
                  />


                  <button
                    type="button"

                    onClick={() =>
                      setShowPassword(
                        (previous) =>
                          !previous
                      )
                    }
                  >

                    {showPassword
                      ? "Hide"
                      : "Show"}

                  </button>

                </div>

              </label>


              {/* CONFIRM PASSWORD */}

              <label className="form-field">

                <span>
                  Confirm Password
                </span>

                <input
                  type={
                    showPassword

                      ? "text"

                      : "password"
                  }

                  name="confirmPassword"

                  placeholder="Enter password again"

                  value={
                    formData.confirmPassword
                  }

                  onChange={
                    handleChange
                  }

                  minLength="8"

                  required
                />

              </label>

            </div>


            {/* TERMS */}

            <label className="terms-row">

              <input
                type="checkbox"
                required
              />

              <span>
                I agree to the EcoLens
                Terms of Use and
                Privacy Policy.
              </span>

            </label>


            {/* FEEDBACK */}

            {feedback && (

              <div
                className={
                  `signup-feedback ${
                    feedback.type ===
                    "success"

                      ? "signup-feedback-success"

                      : "signup-feedback-error"
                  }`
                }
              >

                {feedback.message}

              </div>
            )}


            {/* SUBMIT */}

            <button
              type="submit"

              className="create-account-button"

              disabled={
                submitting
              }
            >

              {submitting

                ? "Creating Account..."

                : "Create Account"}


              {!submitting && (
                <span>
                  →
                </span>
              )}

            </button>


            <p className="mobile-login-link">

              Already have an account?
              {" "}

              <Link to="/login">
                Log In
              </Link>

            </p>

          </form>

        </div>

      </section>


      <footer className="signup-footer">

        <span>
          © 2026 EcoLens
        </span>

        <span>
          Smarter Waste Detection
          for a Cleaner Bangladesh.
        </span>

      </footer>

    </main>
  );
}


export default SignupPage;