import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { getAuthProviders } from "../services/api";

const signInDefaults = {
  username: "",
  password: "",
};

const signUpDefaults = {
  full_name: "",
  email: "",
  password: "",
  role: "clinician",
};

const fallbackProviders = [
  { id: "password", label: "Email and password", available: true, brand: "local" },
  { id: "google", label: "Google", available: false, brand: "google" },
  { id: "facebook", label: "Facebook", available: false, brand: "facebook" },
];

const providerBadge = (provider) => {
  const brand = provider.brand || provider.id;
  if (brand === "google") {
    return "G";
  }
  if (brand === "facebook") {
    return "f";
  }
  return provider.label?.slice(0, 1)?.toUpperCase() || "+";
};

const LoginPanel = ({ defaultMode = "signup", variant = "standalone" }) => {
  const navigate = useNavigate();
  const { login, signup, busy, error, clearError } = useAuth();
  const [mode, setMode] = useState(defaultMode);
  const [signInForm, setSignInForm] = useState(signInDefaults);
  const [signUpForm, setSignUpForm] = useState(signUpDefaults);
  const [providers, setProviders] = useState([]);
  const [providersLoading, setProvidersLoading] = useState(true);

  const shellClassName =
    variant === "embedded"
      ? "login-panel refined-auth embedded-auth-shell"
      : "login-panel refined-auth minimal-auth-shell";

  useEffect(() => {
    let ignore = false;

    const loadProviders = async () => {
      try {
        const response = await getAuthProviders();
        if (!ignore) {
          setProviders(response.providers || fallbackProviders);
        }
      } catch {
        if (!ignore) {
          setProviders(fallbackProviders);
        }
      } finally {
        if (!ignore) {
          setProvidersLoading(false);
        }
      }
    };

    loadProviders();

    return () => {
      ignore = true;
    };
  }, []);

  const socialProviders = useMemo(
    () => providers.filter((provider) => provider.id !== "password"),
    [providers]
  );

  const submitSignIn = async (event) => {
    event.preventDefault();
    clearError();
    try {
      await login(signInForm.username, signInForm.password);
      navigate("/", { replace: true });
    } catch {
      return;
    }
  };

  const submitSignUp = async (event) => {
    event.preventDefault();
    clearError();
    try {
      const payload = Object.fromEntries(Object.entries(signUpForm).filter(([, value]) => value !== ""));
      await signup(payload);
      navigate("/", { replace: true });
    } catch {
      return;
    }
  };

  const updateSignIn = (event) => {
    const { name, value } = event.target;
    setSignInForm((current) => ({ ...current, [name]: value }));
  };

  const updateSignUp = (event) => {
    const { name, value } = event.target;
    setSignUpForm((current) => ({ ...current, [name]: value }));
  };

  const launchProvider = (provider) => {
    if (!provider?.available || !provider?.login_url) {
      return;
    }
    clearError();
    window.location.assign(provider.login_url);
  };

  const providerCta = (provider) =>
    mode === "signup" ? `Sign up with ${provider.label}` : `Continue with ${provider.label}`;

  const heading = mode === "signup" ? "Create your account" : "Welcome back";
  const subcopy =
    mode === "signup"
      ? "Set up your operator account. Role and profile details can be finished later."
      : "Sign in with your username, email, or connected provider.";

  return (
    <section className={shellClassName}>
      <div className="auth-brand">
        <div className="auth-brand-mark">HS</div>
        <div className="auth-brand-copy">
          <p className="eyebrow">{variant === "embedded" ? "Secure access" : "Secure workspace"}</p>
          <h2>{heading}</h2>
          <p className="subtle-copy">{subcopy}</p>
        </div>
      </div>

      <div className="auth-tab-row auth-tab-row-simple">
        <button
          className={`tab-button ${mode === "signup" ? "active" : ""}`}
          type="button"
          onClick={() => setMode("signup")}
        >
          Sign up
        </button>
        <button
          className={`tab-button ${mode === "signin" ? "active" : ""}`}
          type="button"
          onClick={() => setMode("signin")}
        >
          Sign in
        </button>
      </div>

      <div className="auth-main-card auth-card-simple">
        <div className="auth-provider-stack">
          {providersLoading ? (
            <p className="subtle-copy">Loading provider options...</p>
          ) : (
            socialProviders.map((provider) => (
              <button
                key={provider.id}
                className={`social-auth-button social-auth-${provider.brand || "generic"} ${
                  provider.available ? "" : "is-inactive"
                }`}
                type="button"
                disabled={!provider.available || !provider.login_url}
                onClick={() => launchProvider(provider)}
              >
                <span className="social-auth-mark">{providerBadge(provider)}</span>
                <span className="social-auth-copy">
                  <strong>{providerCta(provider)}</strong>
                  <small>
                    {provider.available
                      ? provider.description || "Secure provider sign-in"
                      : `${provider.label} is unavailable until it is connected.`}
                  </small>
                </span>
              </button>
            ))
          )}
        </div>

        <div className="auth-divider">
          <span>{mode === "signup" ? "or create with email" : "or continue with email"}</span>
        </div>

        {mode === "signup" ? (
          <form className="login-form auth-form-stack auth-form-simple" onSubmit={submitSignUp}>
            <label className="field">
              <span>Full name</span>
              <input
                name="full_name"
                type="text"
                value={signUpForm.full_name}
                onChange={updateSignUp}
                autoComplete="name"
                placeholder="Birat Khadka"
                required
              />
            </label>

            <label className="field">
              <span>Email</span>
              <input
                name="email"
                type="email"
                value={signUpForm.email}
                onChange={updateSignUp}
                autoComplete="email"
                placeholder="name@healthsphere.ai"
                required
              />
            </label>

            <label className="field">
              <span>Password</span>
              <input
                name="password"
                type="password"
                value={signUpForm.password}
                onChange={updateSignUp}
                autoComplete="new-password"
                placeholder="Minimum 10 characters"
                minLength={10}
                required
              />
            </label>

            <p className="auth-helper-note">
              We create your username from your email. Profile details can be completed later.
            </p>

            <button className="primary-button accent-button auth-submit-button" type="submit" disabled={busy}>
              {busy ? "Creating account..." : "Create account"}
            </button>
          </form>
        ) : (
          <form className="login-form auth-form-stack auth-form-simple" onSubmit={submitSignIn}>
            <label className="field">
              <span>Email or username</span>
              <input
                name="username"
                type="text"
                value={signInForm.username}
                onChange={updateSignIn}
                autoComplete="username"
                placeholder="name@healthsphere.ai"
                required
              />
            </label>

            <label className="field">
              <span>Password</span>
              <input
                name="password"
                type="password"
                value={signInForm.password}
                onChange={updateSignIn}
                autoComplete="current-password"
                placeholder="Enter your password"
                minLength={10}
                required
              />
            </label>

            <button className="primary-button accent-button auth-submit-button" type="submit" disabled={busy}>
              {busy ? "Signing in..." : "Sign in"}
            </button>
          </form>
        )}

        {error ? <p className="error-text auth-error-text">{error}</p> : null}
      </div>

      <p className="auth-footer-note subtle-copy">
        Provider buttons activate automatically when identity providers are configured in the backend deployment.
      </p>
    </section>
  );
};

export default LoginPanel;
