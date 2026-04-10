import React from "react";

import Dashboard from "../components/Dashboard";
import { useDashboardData } from "../hooks/useDashboardData";

const Home = () => {
  const dashboard = useDashboardData();

  return (
    <Dashboard
      patients={dashboard.patients}
      alerts={dashboard.alerts}
      analytics={dashboard.analytics}
      notifications={dashboard.notifications}
      reportJobs={dashboard.reportJobs}
      summary={dashboard.summary}
      models={dashboard.models}
      metrics={dashboard.metrics}
      loading={dashboard.loading}
      error={dashboard.error}
      selectedPatientId={dashboard.selectedPatientId}
      canViewModels={dashboard.canViewModels}
      liveFeedConnected={dashboard.liveFeedConnected}
      liveFeedLastEventAt={dashboard.liveFeedLastEventAt}
      liveFeedError={dashboard.liveFeedError}
      onPatientChange={dashboard.setSelectedPatientId}
      onNotificationRead={dashboard.markNotificationAsRead}
    />
  );
};

export default Home;
