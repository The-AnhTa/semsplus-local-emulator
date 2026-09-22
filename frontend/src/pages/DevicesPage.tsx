import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { ErrorBanner, LoadingState, PageHeader, Panel, RefreshButton, SearchBox, StatusPill } from "../components";
import type { Device } from "../types";
import { formatNumber, humanizeState } from "../utils";

const tabs = ["ALL", "RUNNING", "FAULT", "STANDBY", "OFFLINE"];

export function DevicesPage() {
  const navigate = useNavigate();
  const [devices, setDevices] = useState<Device[]>([]);
  const [status, setStatus] = useState("ALL");
  const [station, setStation] = useState("");
  const [query, setQuery] = useState("");
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    setLoading(true); setError("");
    try { setDevices(await api.devices()); } catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to load devices"); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void load(); }, [load]);
  const visible = useMemo(() => devices.filter((device) => {
    const matchesStatus = status === "ALL" || device.status === status;
    const matchesQuery = !query || `${device.name} ${device.serialNumber}`.toLowerCase().includes(query.toLowerCase());
    return matchesStatus && matchesQuery && device.stationName.toLowerCase().includes(station.toLowerCase()) && (!email || "researcher@example.local".includes(email.toLowerCase()));
  }), [devices, status, query, station, email]);

  return (
    <div className="page" data-testid="device-list-page">
      <PageHeader eyebrow="Assets" title="Device List" actions={<span className="page-note">On-grid inverters</span>} />
      {error && <ErrorBanner message={error} />}
      <Panel>
        <div className="filter-bar"><button className="filter-button">☷ Filter</button><SearchBox value={station} onChange={setStation} placeholder="Station name"/><SearchBox value={query} onChange={setQuery} placeholder="Device name / SN" testId="device-search"/><SearchBox value={email} onChange={setEmail} placeholder="Email"/><RefreshButton onClick={load} loading={loading}/></div>
        <div className="tabs" role="tablist" aria-label="Device status">{tabs.map((tab) => <button key={tab} className={status === tab ? "active" : ""} onClick={() => setStatus(tab)} role="tab" aria-selected={status === tab}>{humanizeState(tab)} <span>{tab === "ALL" ? devices.length : devices.filter((d) => d.status === tab).length}</span></button>)}</div>
        {loading ? <LoadingState/> : <div className="table-wrap"><table><thead><tr><th>Device name</th><th>Device SN</th><th>Device status</th><th>Device type</th><th>Active power</th><th>Daily generation</th><th>Operation</th></tr></thead><tbody>
          <tr className="group-row"><td colSpan={7}>⌄ <strong>Test Station 01</strong> <span>1 device</span></td></tr>
          {visible.map((device) => <tr key={device.id} data-testid="device-row"><td><button className="row-link" onClick={() => navigate(`/devices/${device.id}`)} data-testid="device-link">{device.name}</button></td><td><code>{device.serialNumber}</code></td><td><StatusPill status={device.status}/></td><td>{device.deviceType}</td><td><strong>{formatNumber(device.activePowerKw)}</strong><small className="unit"> kW</small></td><td>{formatNumber(device.dailyGenerationKwh)}<small className="unit"> kWh</small></td><td><button className="text-button" onClick={() => navigate(`/devices/${device.id}`)}>Open detail →</button></td></tr>)}
        </tbody></table>{!visible.length && <div className="no-results">No devices match these filters.</div>}</div>}
        <div className="pagination"><span>Showing {visible.length} of {devices.length}</span><button disabled>‹</button><button className="current">1</button><button disabled>›</button></div>
      </Panel>
    </div>
  );
}

