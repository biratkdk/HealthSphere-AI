import { useEffect, useMemo, useState } from "react";
import useSWR from "swr";

import { useAuth } from "../context/AuthContext";
import { useOperationsStream } from "./useOperationsStream";
import { getRequestErrorMessage, markNotificationRead } from "../services/api";

export const useDashboardData = (initialPatientId = null) => {
  const { user } = useAuth();
  const [selectedPatientId, setSelectedPatientId] = useState(initialPatientId);
  const canViewModels = Boolean(user && user.role !== "service");

  const {
    data: patients = [],
    error: patientsError,
    isLoading: patientsLoading,
  } = useSWR(user ? ["patients"] : null);
  const {
    data: alerts = [],
    error: alertsError,
    isLoading: alertsLoading,
    mutate: mutateAlerts,
  } = useSWR(user ? ["alerts"] : null);
  const {
    data: analytics = null,
    error: analyticsError,
    isLoading: analyticsLoading,
    mutate: mutateAnalytics,
  } = useSWR(user ? ["analytics"] : null);
  const {
    data: notifications = [],
    error: notificationsError,
    isLoading: notificationsLoading,
    mutate: mutateNotifications,
  } = useSWR(user ? ["notifications", 8, false] : null);
  const {
    data: reportJobs = [],
    error: reportJobsError,
    isLoading: reportJobsLoading,
    mutate: mutateReportJobs,
  } = useSWR(user ? ["reportJobs", 8] : null);
  const {
    data: models = [],
    error: modelsError,
    isLoading: modelsLoading,
  } = useSWR(user && canViewModels ? ["models"] : null);

  useEffect(() => {
    if (!patients.length) {
      return;
    }

    const preferredPatientId = user?.preferences?.last_selected_patient_id;
    if (preferredPatientId && patients.some((patient) => patient.patient_id === preferredPatientId)) {
      setSelectedPatientId((current) => current || preferredPatientId);
      return;
    }

    if (!patients.some((patient) => patient.patient_id === selectedPatientId)) {
      setSelectedPatientId(patients[0].patient_id);
    }
  }, [patients, selectedPatientId, user?.preferences?.last_selected_patient_id]);

  const activePatientId = selectedPatientId || patients[0]?.patient_id || user?.preferences?.last_selected_patient_id;
  const {
    data: summary = null,
    error: summaryError,
    isLoading: summaryLoading,
    mutate: mutateSummary,
  } = useSWR(user && activePatientId ? ["patientSummary", activePatientId] : null);

  const {
    snapshot,
    connected: liveFeedConnected,
    lastEventAt: liveFeedLastEventAt,
    error: liveFeedError,
  } = useOperationsStream(Boolean(user));

  useEffect(() => {
    if (!snapshot) {
      return;
    }

    mutateAnalytics(
      (current) =>
        current
          ? {
              ...current,
              unread_notifications: snapshot.unread_notifications,
              open_alerts: snapshot.open_alerts,
              critical_alerts: snapshot.critical_alerts,
              report_queue: snapshot.report_queue,
            }
          : current,
      false
    );
    mutateReportJobs(snapshot.active_jobs || [], false);
    mutateAlerts(snapshot.latest_alerts || [], false);
    mutateNotifications(snapshot.latest_notifications || [], false);
  }, [snapshot, mutateAlerts, mutateAnalytics, mutateNotifications, mutateReportJobs]);

  const metrics = useMemo(() => {
    if (!summary || !analytics) {
      return [];
    }

    const queueDepth = analytics.report_queue.queued + analytics.report_queue.running;

    return [
      {
        label: "ICU deterioration",
        value: `${Math.round(summary.icu_risk.icu_risk * 100)}%`,
        tone: summary.icu_risk.risk_band,
      },
      {
        label: "Open alerts",
        value: `${analytics.open_alerts}`,
        tone: analytics.critical_alerts > 0 ? "high" : "low",
      },
      {
        label: "Unread inbox",
        value: `${analytics.unread_notifications}`,
        tone: analytics.unread_notifications > 0 ? "medium" : "low",
      },
      {
        label: "Report queue",
        value: `${queueDepth}`,
        tone: queueDepth > 0 ? "medium" : "low",
      },
      {
        label: "Patients monitored",
        value: `${analytics.total_patients}`,
        tone: "low",
      },
      {
        label: "Care follow-up",
        value: `${summary.treatment.recommended_follow_up_minutes} min`,
        tone: summary.treatment.priority,
      },
    ];
  }, [analytics, summary]);

  const markNotificationAsRead = async (notificationId) => {
    const updated = await markNotificationRead(notificationId);
    mutateNotifications(
      (current = []) =>
        current.map((notification) =>
          notification.notification_id === updated.notification_id ? updated : notification
        ),
      false
    );
    mutateAnalytics(
      (current) =>
        current
          ? {
              ...current,
              unread_notifications: Math.max(0, current.unread_notifications - 1),
            }
          : current,
      false
    );
    return updated;
  };

  const loading =
    patientsLoading ||
    alertsLoading ||
    analyticsLoading ||
    notificationsLoading ||
    reportJobsLoading ||
    summaryLoading ||
    (canViewModels && modelsLoading);

  const error =
    getRequestErrorMessage(patientsError, "") ||
    getRequestErrorMessage(summaryError, "") ||
    getRequestErrorMessage(analyticsError, "") ||
    getRequestErrorMessage(alertsError, "") ||
    getRequestErrorMessage(notificationsError, "") ||
    getRequestErrorMessage(reportJobsError, "") ||
    getRequestErrorMessage(modelsError, "") ||
    "";

  return {
    patients,
    alerts,
    analytics,
    notifications,
    reportJobs,
    models,
    summary,
    metrics,
    loading,
    error,
    selectedPatientId: activePatientId,
    setSelectedPatientId,
    markNotificationAsRead,
    canViewModels,
    liveFeedConnected,
    liveFeedLastEventAt,
    liveFeedError,
    refreshSummary: mutateSummary,
  };
};
