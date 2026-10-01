import type { DeviceState } from "./types";

const DEVICE_STATE_LABELS: Record<DeviceState, string> = {
  RUNNING: "Running",
  STANDBY: "Standby",
  STARTING: "Starting",
  STOPPING: "Stopping",
  OFFLINE: "Offline",
  FAULT: "Fault",
  RAPID_SHUTDOWN: "Rapid Shutdown",
};

export function humanizeState(state: DeviceState | string): string {
  if (state in DEVICE_STATE_LABELS) return DEVICE_STATE_LABELS[state as DeviceState];
  return state.toLowerCase().split("_").map((word) => word[0].toUpperCase() + word.slice(1)).join(" ");
}

export function stateTone(state: DeviceState | string): "success" | "warning" | "danger" | "muted" {
  if (state === "RUNNING") return "success";
  if (["FAULT", "RAPID_SHUTDOWN", "OCCURRING"].includes(state)) return "danger";
  if (["STARTING", "STOPPING", "STANDBY"].includes(state)) return "warning";
  return "muted";
}

export function formatNumber(value: number, decimals = 2): string {
  return new Intl.NumberFormat("en-AU", { minimumFractionDigits: decimals, maximumFractionDigits: decimals }).format(value);
}
