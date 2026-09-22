import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { ErrorBanner, LoadingState, PageHeader, Panel, RefreshButton, SearchBox, StatusPill } from "../components";
import type { Station } from "../types";
import { formatNumber, humanizeState } from "../utils";

const tabs = ["ALL", "RUNNING", "WAITING", "OFFLINE", "FAULT", "CONSTRUCTING"];

export function StationsPage() {
  const navigate = useNavigate();
  const [stations, setStations] = useState<Station[]>([]);
  const [status, setStatus] = useState("ALL");
  const [query, setQuery] = useState("");
  const [address, setAddress] = useState("");
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try { setStations(await api.stations()); } catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to load stations"); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void load(); }, [load]);

  const visible = useMemo(() => stations.filter((station) => {
    const matchesStatus = status === "ALL" || station.status === status;
    const matchesQuery = !query || `${station.name} ${station.id}`.toLowerCase().includes(query.toLowerCase());
    return matchesStatus && matchesQuery && station.address.toLowerCase().includes(address.toLowerCase()) && station.email.toLowerCase().includes(email.toLowerCase());
  }), [stations, status, query, address, email]);

  return (
    <div className="page" data-testid="station-list-page">
      <PageHeader eyebrow="Portfolio overview" title="Station List" actions={<span className="page-note">1 synthetic site · 10 kW</span>} />
      {error && <ErrorBanner message={error} />}
      <Panel>
        <div className="filter-bar">
          <button className="filter-button">☷ Filter</button>
          <SearchBox value={query} onChange={setQuery} placeholder="Station / device name / SN" testId="station-search" />
          <SearchBox value={address} onChange={setAddress} placeholder="Station address" />
          <SearchBox value={email} onChange={setEmail} placeholder="Email" />
          <RefreshButton onClick={load} loading={loading} />
        </div>
        <div className="tabs" role="tablist" aria-label="Station status">
          {tabs.map((tab) => <button key={tab} className={status === tab ? "active" : ""} onClick={() => setStatus(tab)} role="tab" aria-selected={status === tab}>{humanizeState(tab)} <span>{tab === "ALL" ? stations.length : stations.filter((s) => s.status === tab).length}</span></button>)}
        </div>
        {loading ? <LoadingState /> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Station information</th><th>Station status</th><th>Today&apos;s generation</th><th>Cumulative generation</th><th>Specific yield</th><th>PV power</th><th>Note</th><th>Operation</th></tr></thead>
              <tbody>{visible.map((station) => (
                <tr key={station.id} data-testid="station-row">
                  <td><button className="station-cell" onClick={() => navigate("/devices")} data-testid="station-link"><span className="site-thumb"><i/><i/><i/></span><span><strong>{station.name}</strong><small>{station.address}</small><small>{station.capacityKw} kW installed</small></span></button></td>
                  <td><StatusPill status={station.status} /></td>
                  <td><strong>{formatNumber(station.todayGenerationKwh)}</strong><small className="unit"> kWh</small></td>
                  <td><strong>{formatNumber(station.cumulativeGenerationKwh)}</strong><small className="unit"> kWh</small></td>
                  <td>{formatNumber(station.specificYieldKwhKwp)}<small className="unit"> kWh/kWp</small></td>
                  <td>{formatNumber(station.pvPowerKw)}<small className="unit"> kW</small></td>
                  <td><span className="muted-text">{station.note}</span></td>
                  <td><button className="text-button" onClick={() => navigate("/devices")}>View devices →</button></td>
                </tr>
              ))}</tbody>
            </table>
            {!visible.length && <div className="no-results">No stations match these filters.</div>}
          </div>
        )}
        <div className="pagination"><span>Showing {visible.length} of {stations.length}</span><button disabled>‹</button><button className="current">1</button><button disabled>›</button></div>
      </Panel>
    </div>
  );
}

