import {
  useState,
} from "react";

import {
  Link,
  useNavigate,
} from "react-router-dom";

import logo from "../assets/ecolens-logo.png";

import {
  apiRequest,
} from "../services/api";

import "../styles/login.css";


const loginRoles = [

  {
    id: "household",
    icon: "⌂",
    title: "Household",
    subtitle: "Personal waste guidance",
  },

  {
    id: "employee",
    icon: "✓",
    title: "Municipal Employee",
    subtitle: "Field work and assignments",
  },

  {
    id: "authority",
    icon: "▦",
    title: "Community Authority",
    subtitle: "Community management",
  },
];


function LoginPage() {

  const navigate =
    useNavigate();


  const [
    selectedRole,
    setSelectedRole,
  ] = useState(
    "household"
  );


  const [
    email,
    setEmail,
  ] = useState("");


  const [
    password,
    setPassword,
  ] = useState("");


  const [
    showPassword,
    setShowPassword,
  ] = useState(false);


  const [
    submitting,
    setSubmitting,
  ] = useState(false);


  const [
    feedback,
    setFeedback,
  ] = useState(null);


  // ========================================================
  // LOGIN
  // ========================================================

  const handleSubmit = async (
    event
  ) => {

    event.preventDefault();


    setFeedback(null);


    try {

      setSubmitting(true);


      const response =
        await apiRequest(
          "/api/auth/login",
          {
            method: "POST",

            body:
              JSON.stringify(
                {
                  role:
                    selectedRole,

                  email,

                  password,
                }
              ),
          }
        );


      setFeedback(
        {
          type: "success",

          message:
            `Welcome back, ${response.user.full_name}.`,
        }
      );


      navigate(
        response.redirect_path
      );


    } catch (error) {

      setFeedback(
        {
          type: "error",

          message:
            error.message,
        }
      );


    } finally {

      setSubmitting(
        false
      );
    }
  };


  return (

    <main className="login-page">


      {/* BACKGROUND */}

      <div className="login-glow login-glow-one" />

      <div className="login-glow login-glow-two" />


      {/* HEADER */}

      <header className="login-header">

        <Link
          to="/"
          className="login-brand"
        >

          <img
            src={logo}
            alt="EcoLens"
          />

          <span>
            EcoLens
          </span>

        </Link>


        <div className="login-signup-link">

          <span>
            New to EcoLens?
          </span>

          <Link to="/signup">
            Create Account
          </Link>

        </div>

      </header>


      {/* LOGIN */}

      <section className="login-container">


        {/* INTRO */}

        <div className="login-intro">

          <span className="login-eyebrow">
            WELCOME BACK
          </span>


          <h1>
            Continue your work

            <span>
              {" "}with EcoLens.
            </span>
          </h1>


          <p>
            Select your EcoLens account
            type and sign in using the
            email and password you used
            during registration.
          </p>

        </div>


        {/* CARD */}

        <div className="login-card">


          <div className="login-card-heading">

            <div>

              <span>
                SECURE LOGIN
              </span>

              <h2>
                Sign in to your account
              </h2>

            </div>

          </div>


          {/* ROLE */}

          <div className="login-role-section">

            <span className="login-field-label">
              Account Type
            </span>


            <div className="login-role-grid">

              {loginRoles.map(
                (role) => (

                  <button
                    key={
                      role.id
                    }

                    type="button"

                    className={
                      `login-role-card ${
                        selectedRole ===
                        role.id

                          ? "login-role-card-selected"

                          : ""
                      }`
                    }

                    onClick={() => {

                      setSelectedRole(
                        role.id
                      );

                      setFeedback(
                        null
                      );
                    }}
                  >

                    <div className="login-role-icon">
                      {role.icon}
                    </div>


                    <div>

                      <strong>
                        {role.title}
                      </strong>

                      <span>
                        {role.subtitle}
                      </span>

                    </div>


                    <div className="login-role-check">

                      {selectedRole ===
                        role.id
                        ? "✓"
                        : ""}

                    </div>

                  </button>

                )
              )}

            </div>

          </div>


          {/* FORM */}

          <form
            className="login-form"

            onSubmit={
              handleSubmit
            }
          >


            <label className="login-field">

              <span>
                Email Address
              </span>

              <input
                type="email"

                placeholder="you@example.com"

                value={
                  email
                }

                onChange={
                  (event) => {

                    setEmail(
                      event.target.value
                    );

                    setFeedback(
                      null
                    );
                  }
                }

                autoComplete="email"

                required
              />

            </label>


            <label className="login-field">

              <div className="password-label-row">

                <span>
                  Password
                </span>

              </div>


              <div className="login-password-field">

                <input
                  type={
                    showPassword
                      ? "text"
                      : "password"
                  }

                  placeholder="Enter your password"

                  value={
                    password
                  }

                  onChange={
                    (event) => {

                      setPassword(
                        event.target.value
                      );

                      setFeedback(
                        null
                      );
                    }
                  }

                  autoComplete="current-password"

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


            {selectedRole ===
              "authority" && (

              <div className="login-info-box">

                Community Authority
                accounts must be approved
                before they can sign in.

              </div>

            )}


            {feedback && (

              <div
                className={
                  `login-feedback ${
                    feedback.type ===
                    "success"

                      ? "login-feedback-success"

                      : "login-feedback-error"
                  }`
                }
              >

                {feedback.message}

              </div>

            )}


            <button
              type="submit"

              className="login-button"

              disabled={
                submitting
              }
            >

              {submitting
                ? "Signing In..."
                : "Log In"}

              {!submitting && (
                <span>
                  →
                </span>
              )}

            </button>


            <p className="login-bottom-text">

              Don't have an account?

              {" "}

              <Link to="/signup">
                Sign Up
              </Link>

            </p>

          </form>

        </div>

      </section>


      <footer className="login-footer">

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


export default LoginPage;