import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
} from "react-router-dom";

import WelcomePage
  from "./pages/WelcomePage";

import SignupPage
  from "./pages/SignupPage";

import LoginPage
  from "./pages/LoginPage";

import AccountHomePage
  from "./pages/AccountHomePage";


function App() {

  return (

    <BrowserRouter>

      <Routes>


        {/* WELCOME */}

        <Route
          path="/"

          element={
            <WelcomePage />
          }
        />


        {/* SIGNUP */}

        <Route
          path="/signup"

          element={
            <SignupPage />
          }
        />


        {/* LOGIN */}

        <Route
          path="/login"

          element={
            <LoginPage />
          }
        />


        {/* TEMP HOUSEHOLD HOME */}

        <Route
          path="/household"

          element={
            <AccountHomePage
              expectedRole="household"
            />
          }
        />


        {/* TEMP EMPLOYEE HOME */}

        <Route
          path="/employee"

          element={
            <AccountHomePage
              expectedRole="employee"
            />
          }
        />


        {/* TEMP AUTHORITY HOME */}

        <Route
          path="/authority"

          element={
            <AccountHomePage
              expectedRole="community_authority"
            />
          }
        />


        {/* UNKNOWN ROUTE */}

        <Route
          path="*"

          element={
            <Navigate
              to="/"
              replace
            />
          }
        />


      </Routes>

    </BrowserRouter>
  );
}


export default App;