import "../styles/welcome.css";
import logo from "../assets/ecolens-logo.png";

function WelcomePage() {
  const handleScrollToAbout = () => {
    const aboutSection = document.getElementById("about");

    if (aboutSection) {
      aboutSection.scrollIntoView({
        behavior: "smooth",
      });
    }
  };

  return (
    <main className="welcome-page">
      {/* Decorative background */}
      <div className="background-glow glow-one" />
      <div className="background-glow glow-two" />
      <div className="background-grid" />

      {/* ================= NAVBAR ================= */}

      <header className="welcome-navbar">
        <div className="nav-brand">
          <span className="brand-dot" />
          <span>EcoLens</span>
        </div>

        <nav className="nav-links">
          <button
            className="nav-link"
            onClick={handleScrollToAbout}
          >
            About
          </button>

          <a
            href="/login"
            className="nav-link"
          >
            Login
          </a>

          <a
            href="/signup"
            className="nav-signup"
          >
            Sign Up
          </a>
        </nav>
      </header>

      {/* ================= HERO ================= */}

      <section className="welcome-hero">
        <div className="hero-content">
          <div className="logo-wrapper">
            <div className="logo-glow" />

            <img
              src={logo}
              alt="EcoLens"
              className="hero-logo"
            />
          </div>

          <div className="hero-text">
            <span className="hero-label">
              INTELLIGENT WASTE MANAGEMENT
            </span>

            <h1 className="hero-title">
  Smarter Waste Detection
  <br />
  <span>for a Cleaner Bangladesh.</span>
</h1>

            <p className="hero-description">
              EcoLens turns everyday waste into practical
              guidance for cleaner homes, safer communities,
              and a greener Bangladesh.
              <br />
              Through intelligent detection and responsible
              environmental guidance, every small action can
              become part of a cleaner future.
            </p>

            <div className="hero-actions">
              <a
                href="/signup"
                className="primary-button"
              >
                Get Started

                <span className="button-arrow">
                  →
                </span>
              </a>

              <button
                className="secondary-button"
                onClick={handleScrollToAbout}
              >
                Discover EcoLens
              </button>
            </div>

            <div className="trust-row">
              <div className="trust-item">
                <span className="trust-icon">
                  ✓
                </span>

                <span>
                  Simple
                </span>
              </div>

              <div className="trust-item">
                <span className="trust-icon">
                  ✓
                </span>

                <span>
                  Intelligent
                </span>
              </div>

              <div className="trust-item">
                <span className="trust-icon">
                  ✓
                </span>

                <span>
                  Bangladesh-focused
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ================= ABOUT PREVIEW ================= */}

      <section
        className="about-preview"
        id="about"
      >
        <div className="about-card">
          <span className="section-label">
            WHAT IS ECOLENS?
          </span>

          <h2>
            A clearer way to understand and manage waste.
          </h2>

          <p>
            EcoLens combines intelligent waste detection
            with useful environmental guidance. It helps
            households understand their waste, supports
            municipal employees during collection work,
            and gives community authorities better
            information for cleaner and more responsible
            waste management.
          </p>

          <div className="about-features">
            <div className="about-feature">
              <div className="feature-number">
                01
              </div>

              <div>
                <h3>
                  Identify
                </h3>

                <p>
                  Recognise different types of waste
                  through intelligent image detection.
                </p>
              </div>
            </div>

            <div className="about-feature">
              <div className="feature-number">
                02
              </div>

              <div>
                <h3>
                  Understand
                </h3>

                <p>
                  Receive practical guidance designed
                  for the right user and situation.
                </p>
              </div>
            </div>

            <div className="about-feature">
              <div className="feature-number">
                03
              </div>

              <div>
                <h3>
                  Improve
                </h3>

                <p>
                  Turn better information into cleaner
                  homes, streets, and communities.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ================= FOOTER ================= */}

      <footer className="welcome-footer">
        <div>
          <strong>
            EcoLens
          </strong>

          <span>
            Cleaner choices. Better communities.
          </span>
        </div>

        <p>
          © 2026 EcoLens
        </p>
      </footer>
    </main>
  );
}

export default WelcomePage;