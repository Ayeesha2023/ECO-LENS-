import {
  useEffect,
  useState,
} from "react";

import {
  useNavigate,
} from "react-router-dom";

import logo from "../assets/ecolens-logo.png";

import {
  apiRequest,
} from "../services/api";

import "../styles/login.css";


const ROLE_PATHS = {

  household:
    "/household",

  employee:
    "/employee",

  community_authority:
    "/authority",
};


function AccountHomePage({
  expectedRole,
}) {

  const navigate =
    useNavigate();


  const [
    user,
    setUser,
  ] = useState(null);


  const [
    loading,
    setLoading,
  ] = useState(true);


  const [
    error,
    setError,
  ] = useState("");


  useEffect(() => {

    async function loadUser() {

      try {

        const response =
          await apiRequest(
            "/api/auth/me"
          );


        const loggedInUser =
          response.user;


        if (
          loggedInUser.role
          !== expectedRole
        ) {

          navigate(
            ROLE_PATHS[
              loggedInUser.role
            ] || "/"
          );

          return;
        }


        setUser(
          loggedInUser
        );


      } catch (requestError) {

        setError(
          requestError.message
        );


        setTimeout(
          () => {
            navigate(
              "/login"
            );
          },
          1200
        );


      } finally {

        setLoading(
          false
        );
      }
    }


    loadUser();

  }, [
    expectedRole,
    navigate,
  ]);


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


  if (loading) {

    return (
      <main className="account-home">

        <div className="account-home-card">

          <p>
            Loading your EcoLens account...
          </p>

        </div>

      </main>
    );
  }


  if (error) {

    return (
      <main className="account-home">

        <div className="account-home-card">

          <p>
            {error}
          </p>

        </div>

      </main>
    );
  }


  return (

    <main className="account-home">

      <div className="account-home-card">

        <img
          src={logo}
          alt="EcoLens"
        />


        <span className="account-role-pill">
          {user.role_display}
        </span>


        <h1>
          Welcome, {user.full_name}
        </h1>


        <p>
          You are successfully logged
          into EcoLens as a
          {" "}
          <strong>
            {user.role_display}
          </strong>.
        </p>


        <p>
          {user.email}
        </p>


        {user.region_name && (

          <p>
            Region:
            {" "}
            {user.region_name}
          </p>

        )}


        <button
          className="account-logout"

          onClick={
            handleLogout
          }
        >

          Log Out

        </button>

      </div>

    </main>
  );
}


export default AccountHomePage;