import React, { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { getRequestErrorMessage } from "../services/api";

const AuthCallback = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { completeOidcLogin } = useAuth();
  const [error, setError] = useState("");
  const loginRef = useRef(completeOidcLogin);

  loginRef.current = completeOidcLogin;

  useEffect(() => {
    let ignore = false;

    const finalize = async () => {
      try {
        await loginRef.current();
        if (!ignore) {
          navigate("/", { replace: true });
        }
      } catch (requestError) {
        if (!ignore) {
          setError(getRequestErrorMessage(requestError, "Single sign-on failed."));
        }
      }
    };

    finalize();

    return () => {
      ignore = true;
    };
  }, [navigate, searchParams]);

  return (
    <section className="login-panel refined-auth minimal-auth-shell">
      <p className="eyebrow">Secure provider access</p>
      <h2>Finalizing sign-in</h2>
      {error ? (
        <p className="error-text">{error}</p>
      ) : (
        <p className="subtle-copy">
          Completing the {searchParams.get("provider") || "provider"} exchange and loading your workspace.
        </p>
      )}
    </section>
  );
};

export default AuthCallback;
