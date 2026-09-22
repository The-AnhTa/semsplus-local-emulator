import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { EmptyState, ErrorBanner, LoadingState, PageHeader, Panel, RefreshButton, SearchBox, StatusPill } from "../components";
import type { Alarm } from "../types";
import { humanizeState } from "../utils";

const tabs = ["ALL", "OCCURRING", "RECOVERED"];

export function AlarmsPage() {
  const [alarms, setAlarms] = useState<Alarm[]>([]);
  const [status, setStatus] = useState("ALL");
  const [query, setQuery] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    setLoading(true); setError("");
    try { setAlarms(await api.alarms()); } catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to load alarms"); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void load(); }, [load]);
  const recover = async (id: number) => {
    setError("");
    try { await api.recoverAlarm(id); await load(); } catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to recover alarm"); }
  };
  const visible = useMemo(() => alarms.filter((alarm) => {
    const text = `${alarm.alarmName} ${alarm.deviceName} ${alarm.stationName}`.toLowerCase();
    const day = alarm.alarmTime.slice(0, 10);
    return (status === "ALL" || alarm.status === status) && text.includes(query.toLowerCase()) && (!start || day >= start) && (!end || day <= end);
  }), [alarms, status, query, start, end]);
  return (
    <div className="page" data-testid="alarm-center-page">
      <PageHeader eyebrow="Event monitoring" title="Alarm Center" actions={<span className="page-note">Synthetic events only</span>}/>
      {error && <ErrorBanner message={error}/>}<Panel>
        <div className="filter-bar alarm-filters"><button className="filter-button">☷ Filter</button><SearchBox value={query} onChange={setQuery} placeholder="Device / station / SN" testId="alarm-search"/><label className="date-filter"><span>From</span><input type="date" value={start} onChange={(e) => setStart(e.target.value)}/></label><label className="date-filter"><span>To</span><input type="date" value={end} onChange={(e) => setEnd(e.target.value)}/></label><RefreshButton onClick={load} loading={loading}/></div>
        <div className="tabs" role="tablist" aria-label="Alarm status">{tabs.map((tab) => <button key={tab} className={status === tab ? "active" : ""} onClick={() => setStatus(tab)} role="tab" aria-selected={status === tab}>{humanizeState(tab)} <span>{tab === "ALL" ? alarms.length : alarms.filter((a) => a.status === tab).length}</span></button>)}</div>
        {loading ? <LoadingState/> : visible.length ? <div className="table-wrap"><table><thead><tr><th>Alarm name</th><th>Device name</th><th>Status</th><th>Alarm level</th><th>Alarm time</th><th>Station name</th><th>Operation</th></tr></thead><tbody>{visible.map((alarm) => <tr key={alarm.id} data-testid="alarm-row"><td><strong>{alarm.alarmName}</strong><small className="alarm-code">{alarm.alarmType}</small></td><td>{alarm.deviceName}</td><td><StatusPill status={alarm.status}/></td><td><span className={`level level--${alarm.level.toLowerCase()}`}>{humanizeState(alarm.level)}</span></td><td>{new Date(alarm.alarmTime).toLocaleString("en-AU")}</td><td>{alarm.stationName}</td><td>{alarm.status === "OCCURRING" ? <button className="text-button" onClick={() => recover(alarm.id)} data-testid="recover-alarm">Mark recovered</button> : <span className="muted-text">Recovered</span>}</td></tr>)}</tbody></table></div> : <EmptyState title="No alarms to show" detail="Inject a research scenario through the admin API to create a synthetic alarm."/>}
      </Panel>
    </div>
  );
}

