import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { SWRConfig } from "swr";
import { Analytics } from "@vercel/analytics/react";
import { SpeedInsights } from "@vercel/speed-insights/react";

import App from "./App";
import { AuthProvider } from "./context/AuthContext";
import { apiFetcher } from "./services/api";
import "./styles/app.css";

const root = ReactDOM.createRoot(document.getElementById("root"));

root.render(
  <React.StrictMode>
    <SWRConfig
      value={{
        fetcher: apiFetcher,
        revalidateOnFocus: true,
        // Only retry on genuine network errors, not on 4xx / 5xx HTTP responses.
        // Retrying on 401/403/422 would just spam the server and confuse users.
        shouldRetryOnError: (err) => !err?.response?.status,
        dedupingInterval: 2000,
        errorRetryCount: 3,
        errorRetryInterval: 5000,
      }}
    >
      <AuthProvider>
        <BrowserRouter>
          <App />
          <Analytics />
          <SpeedInsights />
        </BrowserRouter>
      </AuthProvider>
    </SWRConfig>
  </React.StrictMode>
);
