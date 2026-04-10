import React, { createContext, useContext, useEffect, useMemo, useState } from "react";

import {
  clearAuthSession,
  getCurrentUser,
  getRequestErrorMessage,
  login as loginRequest,
  logoutRequest,
  refreshAuthSession,
  signup as signupRequest,
  updateCurrentUser,
} from "../services/api";

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  // When the axios interceptor exhausts both access + refresh tokens it fires
  // this event so we can clear auth state without needing a direct reference
  // into AuthContext from the API module.
  useEffect(() => {
    const handleExpired = () => setUser(null);
    window.addEventListener("auth:session-expired", handleExpired);
    return () => window.removeEventListener("auth:session-expired", handleExpired);
  }, []);

  useEffect(() => {
    let ignore = false;

    const refreshSession = async () => {
      try {
        const profile = await getCurrentUser();
        if (!ignore) {
          setUser(profile);
        }
      } catch {
        try {
          await refreshAuthSession();
          const profile = await getCurrentUser();
          if (!ignore) {
            setUser(profile);
          }
        } catch (refreshError) {
          clearAuthSession();
          if (!ignore) {
            setUser(null);
          }
        }
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }
    };

    refreshSession();

    return () => {
      ignore = true;
    };
  }, []);

  const value = useMemo(
    () => ({
      user,
      loading,
      busy,
      error,
      isAuthenticated: Boolean(user),
      async login(username, password) {
        setBusy(true);
        setError("");
        try {
          const response = await loginRequest(username, password);
          setUser(response.user);
          return response.user;
        } catch (requestError) {
          setUser(null);
          setError(getRequestErrorMessage(requestError, "Sign-in failed."));
          throw requestError;
        } finally {
          setBusy(false);
        }
      },
      async signup(payload) {
        setBusy(true);
        setError("");
        try {
          const response = await signupRequest(payload);
          setUser(response.user);
          return response.user;
        } catch (requestError) {
          setUser(null);
          setError(getRequestErrorMessage(requestError, "Account creation failed."));
          throw requestError;
        } finally {
          setBusy(false);
        }
      },
      async completeOidcLogin() {
        setBusy(true);
        setError("");
        try {
          const profile = await getCurrentUser();
          setUser(profile);
          return profile;
        } catch {
          try {
            await refreshAuthSession();
            const profile = await getCurrentUser();
            setUser(profile);
            return profile;
          } catch (requestError) {
            setUser(null);
            setError(getRequestErrorMessage(requestError, "Sign-in failed."));
            throw requestError;
          }
        } finally {
          setBusy(false);
        }
      },
      async refreshProfile() {
        setBusy(true);
        setError("");
        try {
          const profile = await getCurrentUser();
          setUser(profile);
          return profile;
        } catch (requestError) {
          setUser(null);
          setError(getRequestErrorMessage(requestError, "Profile refresh failed."));
          throw requestError;
        } finally {
          setBusy(false);
        }
      },
      async updateProfile(payload) {
        setBusy(true);
        setError("");
        try {
          const profile = await updateCurrentUser(payload);
          setUser(profile);
          return profile;
        } catch (requestError) {
          setError(getRequestErrorMessage(requestError, "Profile update failed."));
          throw requestError;
        } finally {
          setBusy(false);
        }
      },
      async logout() {
        try {
          await logoutRequest();
        } finally {
          clearAuthSession();
          setUser(null);
          setError("");
        }
      },
      clearError() {
        setError("");
      },
    }),
    [busy, error, loading, user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("useAuth must be used inside AuthProvider.");
  }
  return value;
};
