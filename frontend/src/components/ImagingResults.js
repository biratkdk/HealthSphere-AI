import React, { useState } from "react";

import { analyzeImaging, getRequestErrorMessage } from "../services/api";

const ImagingResults = ({ patientId }) => {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const submit = async (event) => {
    event.preventDefault();

    if (!file) {
      setError("Select an image before submitting.");
      return;
    }

    try {
      setLoading(true);
      setError("");
      const analysis = await analyzeImaging(file, patientId);
      setResult(analysis);
    } catch (requestError) {
      setError(getRequestErrorMessage(requestError, "Imaging analysis failed."));
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="panel">
      <div className="panel-header">
        <h3>Imaging triage</h3>
        <span className="subtle-copy">Attach study for patient {patientId}</span>
      </div>

      <form className="upload-form" onSubmit={submit}>
        <label className="field upload-field">
          <span>Study file</span>
          <input type="file" accept=".png,.jpg,.jpeg" onChange={(event) => setFile(event.target.files?.[0] || null)} />
        </label>
        <button className="primary-button accent-button" type="submit" disabled={loading}>
          {loading ? "Analyzing..." : "Run analysis"}
        </button>
      </form>

      <p className="subtle-copy imaging-note">
        Imaging triage is an operational review aid. The confidence score reflects model scoring behavior on the packaged
        inference workflow and should not be treated as a confirmed clinical diagnosis.
      </p>

      {error ? <p className="error-text">{error}</p> : null}

      {result ? (
        <div className="analysis-card">
          <p>{result.result}</p>
          <div className="analysis-metrics">
            <span>Confidence: {Math.round(result.confidence * 100)}%</span>
            <span>Anomaly score: {Math.round(result.anomaly_score * 100)}%</span>
          </div>
          <p className="subtle-copy">{result.suggested_next_step}</p>
          {result.study_reference ? <p className="subtle-copy">Study: {result.study_reference}</p> : null}
          {result.stored_uri ? <p className="subtle-copy">Stored in the durable imaging archive.</p> : null}
        </div>
      ) : (
        <p className="subtle-copy">
          The imaging service stores the uploaded study, records the triage result, and generates a notification for the
          signed-in user.
        </p>
      )}
    </section>
  );
};

export default ImagingResults;
