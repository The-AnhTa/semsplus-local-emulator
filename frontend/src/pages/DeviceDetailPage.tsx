import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { ErrorBanner, Icon, LoadingState, StatusPill } from "../components";
import type { ControlAction, ControlRequest, Device, HistoryPoint, MpptPoint, Telemetry } from "../types";
import { formatNumber } from "../utils";

function today(): string { return new Date().toISOString().slice(0, 10); }

function InverterIllustration({ active }: { active: boolean }) {
  return (
    <svg className="inverter" viewBox="0 0 460 390" role="img" aria-label="Generic synthetic inverter illustration">
      <defs><linearGradient id="body" x1="0" y1="0" x2="1" y2="1"><stop stopColor="#f1f5f7"/><stop offset=".52" stopColor="#aeb6bc"/><stop offset="1" stopColor="#707981"/></linearGradient><linearGradient id="edge"><stop stopColor="#667078"/><stop offset="1" stopColor="#272c31"/></linearGradient><filter id="shadow"><feDropShadow dx="0" dy="18" stdDeviation="16" floodOpacity=".5"/></filter></defs>
      <ellipse cx="230" cy="345" rx="142" ry="28" fill="#090b0d" opacity=".8"/>
      <g filter="url(#shadow)"><path d="M117 87 153 64v236l-36-26Z" fill="url(#edge)"/><rect x="145" y="55" width="220" height="250" rx="35" fill="url(#body)" stroke="#eff3f5" strokeWidth="3"/><path d="M172 64v230" stroke="#f8fafb" opacity=".45"/><path d="M346 78v202" stroke="#5f686f" opacity=".35"/></g>
      <circle cx="255" cy="178" r="23" fill="#353c42" opacity=".22"/><path d="m245 178 8 8 15-18" fill="none" stroke={active ? "#52d892" : "#9aa2aa"} strokeWidth="6" strokeLinecap="round" strokeLinejoin="round"/>
      <circle cx="255" cy="267" r="5" fill={active ? "#52d892" : "#697078"}/><text x="255" y="332" textAnchor="middle" fill="#889199" fontSize="13" letterSpacing="3">SYNTHETIC DEVICE</text>
    </svg>
  );
}

function LineChart({ points, keyName, color }: { points: Array<HistoryPoint | MpptPoint>; keyName: "activePowerKw" | "powerKw"; color: string }) {
  const values = points.map((point) => Number(point[keyName as keyof typeof point]));
  const max = Math.max(1, ...values);
  const path = values.map((value, index) => `${index ? "L" : "M"} ${48 + index * (660 / Math.max(1, values.length - 1))} ${236 - value / max * 180}`).join(" ");
  const area = `${path} L 708 236 L 48 236 Z`;
  return (
    <svg className="chart" viewBox="0 0 750 280" role="img" aria-label="Synthetic power chart">
      {[0,1,2,3,4].map((line) => <g key={line}><line x1="48" x2="708" y1={56 + line*45} y2={56 + line*45} stroke="#3c4349"/><text x="38" y={60 + line*45} textAnchor="end" fill="#77818a" fontSize="11">{formatNumber(max * (1-line/4), 1)}</text></g>)}
      <defs><linearGradient id={`area-${keyName}`} x1="0" y1="0" x2="0" y2="1"><stop stopColor={color} stopOpacity=".28"/><stop offset="1" stopColor={color} stopOpacity="0"/></linearGradient></defs>
      {values.length > 0 && <><path d={area} fill={`url(#area-${keyName})`}/><path d={path} fill="none" stroke={color} strokeWidth="3" strokeLinejoin="round"/></>}
      <line x1="48" x2="708" y1="236" y2="236" stroke="#586169"/><text x="48" y="258" fill="#77818a" fontSize="11">00:00</text><text x="370" y="258" textAnchor="middle" fill="#77818a" fontSize="11">12:00</text><text x="708" y="258" textAnchor="end" fill="#77818a" fontSize="11">24:00</text>
    </svg>
  );
}

export function DeviceDetailPage() {
  const { deviceId = "device-test-001" } = useParams();
  const [device, setDevice] = useState<Device | null>(null);
  const [telemetry, setTelemetry] = useState<Telemetry | null>(null);
  const [history, setHistory] = useState<HistoryPoint[]>([]);
  const [mppt, setMppt] = useState<MpptPoint[]>([]);
  const [tab, setTab] = useState<"monitoring" | "mppt">("monitoring");
  const [date, setDate] = useState(today());
  const [drawer, setDrawer] = useState(false);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState("");
  const [controlRequest, setControlRequest] = useState<ControlRequest | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      const [nextDevice, nextTelemetry, nextHistory, nextMppt] = await Promise.all([api.device(deviceId), api.telemetry(deviceId), api.history(deviceId, date), api.mppt(deviceId)]);
      setDevice(nextDevice); setTelemetry(nextTelemetry); setHistory(nextHistory); setMppt(nextMppt);
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to load device"); }
    finally { setLoading(false); }
  }, [deviceId, date]);
  useEffect(() => { void load(); }, [load]);

  const command = async (action: string) => {
    setActing(action); setError(""); setMessage("");
    try {
      const updated = await api.command(deviceId, action);
      setDevice(updated);
      setTelemetry(await api.telemetry(deviceId));
      setHistory(await api.history(deviceId, date));
      setMessage(`${updated.name} is now ${updated.status.toLowerCase().replace("_", " ")}.`);
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Control request failed"); }
    finally { setActing(""); }
  };

  const requestProtectedAction = async (action: ControlAction) => {
    setActing(action); setError(""); setMessage("");
    try {
      const created = await api.createControlRequest(deviceId, action);
      setControlRequest(created);
      setMessage(`Approval request ${created.requestId} created.\nAwaiting controller confirmation.`);
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Approval request failed"); }
    finally { setActing(""); }
  };

  const refreshAfterExecution = useCallback(async () => {
    try {
      const nextDevice = await api.device(deviceId);
      setDevice(nextDevice);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to refresh device state");
      return;
    }

    const [nextTelemetry, nextHistory] = await Promise.allSettled([
      api.telemetry(deviceId),
      api.history(deviceId, date),
    ]);
    if (nextTelemetry.status === "fulfilled") setTelemetry(nextTelemetry.value);
    if (nextHistory.status === "fulfilled") setHistory(nextHistory.value);
    if (nextTelemetry.status === "rejected" || nextHistory.status === "rejected") {
      setError("Device state refreshed, but some monitoring data could not be refreshed.");
    }
  }, [deviceId, date]);

  useEffect(() => {
    if (!controlRequest || !["PENDING", "APPROVED"].includes(controlRequest.status)) return;
    let active = true;
    const poll = async () => {
      try {
        const updated = await api.controlRequest(controlRequest.requestId);
        if (!active) return;
        if (updated.status === "EXECUTED") {
          setMessage(`Approval request ${updated.requestId} executed.\nDevice state: ${updated.resultingState?.toLowerCase().replace("_", " ")}.`);
          setControlRequest(updated);
          await refreshAfterExecution();
        } else if (updated.status === "DENIED") {
          setControlRequest(updated);
          setMessage(`Approval request ${updated.requestId} was denied.\nThe device was not changed.`);
        } else if (updated.status === "EXPIRED") {
          setControlRequest(updated);
          setMessage(`Approval request ${updated.requestId} expired.\nThe device was not changed.`);
        } else if (updated.status === "FAILED") {
          setControlRequest(updated);
          setError(`Approval request ${updated.requestId} failed: ${updated.failureReason ?? "operation was not executed"}`);
        } else {
          setControlRequest(updated);
        }
      } catch (caught) {
        if (active) setError(caught instanceof Error ? caught.message : "Unable to check approval request");
      }
    };
    const interval = window.setInterval(() => { void poll(); }, 1000);
    return () => { active = false; window.clearInterval(interval); };
  }, [controlRequest?.requestId, controlRequest?.status, refreshAfterExecution]);
  const phases = useMemo(() => telemetry ? [
    ["Phase A", telemetry.phaseAVoltage, telemetry.phaseACurrent],
    ["Phase B", telemetry.phaseBVoltage, telemetry.phaseBCurrent],
    ["Phase C", telemetry.phaseCVoltage, telemetry.phaseCCurrent],
  ] : [], [telemetry]);

  if (loading) return <div className="page"><LoadingState/></div>;
  if (!device || !telemetry) return <div className="page"><ErrorBanner message={error || "Device unavailable"}/></div>;
  return (
    <div className="device-detail" data-testid="device-detail-page">
      <div className="detail-heading"><div><div className="breadcrumbs"><Link to="/devices">Device List</Link><span>/</span>Device basic information</div><h1>{device.name}</h1><StatusPill status={device.status} testId="device-status"/></div><div className="device-meta"><span>Station <strong>{device.stationName}</strong></span><span>SN <strong>{device.serialNumber}</strong></span></div></div>
      {error && <ErrorBanner message={error}/>} {message && <div className="success-banner" role="status" data-testid="approval-message">{message}</div>}
      <div className="detail-grid">
        <section className="device-hero"><div className="simulation-label"><i/> LOCAL SIMULATION</div><InverterIllustration active={device.status === "RUNNING"}/><div className="common-controls"><div className="section-title"><span>Common controls</span><small>All actions affect synthetic state only</small></div><div className="control-cards"><button onClick={() => setDrawer(true)} data-testid="open-controls"><span><Icon name="controls" size={30}/></span><strong>Device Start / Stop</strong><small>Start, stop, restart or isolate</small></button><button onClick={() => setMessage("General settings are read-only in this research build.")}><span>⚙</span><strong>General Settings</strong><small>View simulator configuration</small></button></div><button className="more-control" onClick={() => setDrawer(true)}>More control <Icon name="arrow" size={15}/></button></div></section>
        <section className="detail-data">
          <div className="operating panel-inner"><div className="section-title"><span><i className="section-dot"/> Operating data</span><small>Updated {new Date(telemetry.timestamp).toLocaleTimeString("en-AU")}</small></div><div className="metric-grid"><article data-testid="active-power"><span>Active power</span><strong>{formatNumber(telemetry.activePowerKw)} <small>kW</small></strong></article><article><span>Reactive power</span><strong>{formatNumber(telemetry.reactivePowerKvar)} <small>kvar</small></strong></article><article><span>Power factor</span><strong>{formatNumber(telemetry.powerFactor)}</strong></article><article><span>AC frequency</span><strong>{formatNumber(telemetry.acFrequencyHz)} <small>Hz</small></strong></article></div><div className="phase-table"><div className="phase-head"><span>Phase</span><span>Voltage</span><span>Current</span><span>Frequency</span></div>{phases.map(([name, voltage, current]) => <div key={String(name)}><strong>{name}</strong><span>{formatNumber(Number(voltage), 1)} V</span><span>{formatNumber(Number(current))} A</span><span>{formatNumber(telemetry.acFrequencyHz)} Hz</span></div>)}</div></div>
          <div className="monitoring panel-inner"><div className="monitor-toolbar"><div className="segmented"><button className={tab === "monitoring" ? "active" : ""} onClick={() => setTab("monitoring")}>Operation Monitoring</button><button className={tab === "mppt" ? "active" : ""} onClick={() => setTab("mppt")}>MPPT Curve</button></div>{tab === "monitoring" && <input aria-label="Monitoring date" type="date" value={date} onChange={(event) => setDate(event.target.value)} data-testid="history-date"/>}</div><div className="chart-wrap"><LineChart points={tab === "monitoring" ? history : mppt} keyName={tab === "monitoring" ? "activePowerKw" : "powerKw"} color={tab === "monitoring" ? "#f2b84b" : "#5ad5b2"}/><div className="chart-legend"><i style={{background: tab === "monitoring" ? "#f2b84b" : "#5ad5b2"}}/>{tab === "monitoring" ? "Active power (kW)" : "MPPT power (kW)"}</div></div></div>
        </section>
      </div>
      {drawer && <div className="drawer-scrim" onMouseDown={(event) => { if (event.target === event.currentTarget) setDrawer(false); }}><aside className="control-drawer" role="dialog" aria-modal="true" aria-labelledby="control-title" data-testid="control-drawer"><header><div><span className="kicker">SYNTHETIC DEVICE CONTROL</span><h2 id="control-title">Device Start / Stop</h2></div><button onClick={() => setDrawer(false)} aria-label="Close controls"><Icon name="close"/></button></header><div className="drawer-device"><InverterIllustration active={device.status === "RUNNING"}/><div><strong>{device.name}</strong><code>{device.serialNumber}</code><StatusPill status={device.status}/></div></div>{controlRequest && ["PENDING", "APPROVED"].includes(controlRequest.status) && <div className="approval-pending" data-testid="pending-control-request"><strong>{controlRequest.requestId} · {controlRequest.action.replace("_", " ")}</strong><span>Awaiting controller confirmation</span></div>}<div className="control-list"><button onClick={() => requestProtectedAction("RAPID_SHUTDOWN")} disabled={!!acting || !!(controlRequest && ["PENDING", "APPROVED"].includes(controlRequest.status)) || !["RUNNING", "STANDBY"].includes(device.status)} data-testid="rapid-shutdown-button"><span className="control-symbol danger">!</span><span><strong>Rapid Shutdown</strong><small>Requires controller approval before isolation</small></span><em>{acting === "RAPID_SHUTDOWN" ? "Requesting…" : "Request"}</em></button><button onClick={() => command("start")} disabled={!!acting || !["OFFLINE", "STANDBY", "RAPID_SHUTDOWN"].includes(device.status)} data-testid="start-device-button"><span className="control-symbol success">▶</span><span><strong>Start up</strong><small>Transition through Starting to Running</small></span><em>{acting === "start" ? "Working…" : "Start"}</em></button><button onClick={() => requestProtectedAction("STOP")} disabled={!!acting || !!(controlRequest && ["PENDING", "APPROVED"].includes(controlRequest.status)) || !["RUNNING", "STANDBY", "FAULT"].includes(device.status)} data-testid="stop-device-button"><span className="control-symbol warning">■</span><span><strong>Stop</strong><small>Requires controller approval before stopping</small></span><em>{acting === "STOP" ? "Requesting…" : "Request"}</em></button><button onClick={() => requestProtectedAction("RESTART")} disabled={!!acting || !!(controlRequest && ["PENDING", "APPROVED"].includes(controlRequest.status)) || !["RUNNING", "STANDBY"].includes(device.status)} data-testid="restart-device-button"><span className="control-symbol">↻</span><span><strong>Restart</strong><small>Requires controller approval before restart</small></span><em>{acting === "RESTART" ? "Requesting…" : "Request"}</em></button></div><footer><Icon name="bolt"/><p>Stop, restart, and rapid shutdown require persisted controller approval. These controls affect only the local SQLite simulator.</p></footer></aside></div>}
    </div>
  );
}
