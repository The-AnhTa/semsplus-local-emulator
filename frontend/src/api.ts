import type { Alarm, Device, HistoryPoint, MpptPoint, Station, Telemetry } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", "X-Actor": "web-user", ...init?.headers },
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail ?? `Request failed with status ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  login: (email: string, password: string) => request<{ accessToken: string; displayName: string }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  }),
  stations: () => request<Station[]>("/stations"),
  devices: () => request<Device[]>("/devices"),
  device: (id: string) => request<Device>(`/devices/${id}`),
  telemetry: (id: string) => request<Telemetry>(`/devices/${id}/telemetry`),
  history: (id: string, day: string) => request<HistoryPoint[]>(`/devices/${id}/history?day=${day}`),
  mppt: (id: string) => request<MpptPoint[]>(`/devices/${id}/mppt`),
  command: (id: string, command: string) => request<Device>(`/devices/${id}/${command}`, { method: "POST" }),
  alarms: () => request<Alarm[]>("/alarms"),
  recoverAlarm: (id: number) => request<Alarm>(`/alarms/${id}/recover`, { method: "POST" }),
};

