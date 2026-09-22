import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { BrandMark } from "../components";

export function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("researcher@example.local");
  const [password, setPassword] = useState("test-password");
  const [remember, setRemember] = useState(true);
  const [agreement, setAgreement] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!agreement) {
      setError("Please accept the local simulator service agreement.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const session = await api.login(email, password);
      localStorage.setItem("cer-session", session.accessToken);
      if (remember) localStorage.setItem("cer-email", email);
      navigate("/stations");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <section className="login-visual" aria-label="Synthetic solar research landscape">
        <BrandMark />
        <div className="sun" />
        <div className="horizon" />
        <div className="solar-grid"><i/><i/><i/><i/><i/><i/></div>
        <div className="login-visual__copy"><span>LOCAL RESEARCH ENVIRONMENT</span><h1>Safe energy control,<br/>built for testing.</h1><p>A deterministic, offline CER simulator. No physical devices. No external energy services.</p></div>
      </section>
      <section className="login-panel">
        <form onSubmit={submit} data-testid="login-form">
          <span className="kicker">CER TEST PORTAL</span>
          <h2>Welcome back</h2>
          <p>Sign in to the local simulator workspace.</p>
          <label>Email<input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" data-testid="login-email" /></label>
          <label>Password<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" data-testid="login-password" /></label>
          <label className="check-row"><input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} /><span>Remember password on this test browser</span></label>
          <label className="check-row"><input type="checkbox" checked={agreement} onChange={(e) => setAgreement(e.target.checked)} data-testid="service-agreement"/><span>I agree to use this offline simulator for authorised research.</span></label>
          {error && <div className="login-error" role="alert">{error}</div>}
          <button className="primary-button login-button" type="submit" disabled={loading} data-testid="login-button">{loading ? "Signing in…" : "Login"}</button>
          <div className="test-credentials"><strong>Default test account</strong><code>researcher@example.local</code><code>test-password</code></div>
        </form>
      </section>
    </div>
  );
}

