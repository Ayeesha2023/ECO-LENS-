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

import HouseholdDashboard
  from "./pages/HouseholdDashboard";

import EmployeeDashboard
  from "./pages/EmployeeDashboard";

import AuthorityDashboard
  from "./pages/AuthorityDashboard";

import AdminDashboard
  from "./pages/AdminDashboard";


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


        {/* HOUSEHOLD DASHBOARD */}
        <Route
          path="/household"
          element={
            <HouseholdDashboard />
          }
        />


        {/* MUNICIPAL EMPLOYEE DASHBOARD */}
        <Route
          path="/employee"
          element={
            <EmployeeDashboard />
          }
        />


        {/* COMMUNITY AUTHORITY DASHBOARD */}
        <Route
          path="/authority"
          element={
            <AuthorityDashboard />
          }
        />


        {/* ADMIN DASHBOARD */}
        <Route
          path="/admin"
          element={
            <AdminDashboard />
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