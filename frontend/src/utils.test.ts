import { describe, expect, it } from "vitest";
import { formatNumber, humanizeState, stateTone } from "./utils";

describe("display helpers", () => {
  it.each([
    ["RUNNING", "Running"],
    ["STANDBY", "Standby"],
    ["STARTING", "Starting"],
    ["STOPPING", "Stopping"],
    ["OFFLINE", "Offline"],
    ["FAULT", "Fault"],
    ["RAPID_SHUTDOWN", "Rapid Shutdown"],
  ])("maps canonical device state %s to %s", (state, label) => {
    expect(humanizeState(state)).toBe(label);
  });
  it("maps fault states to a danger tone", () => expect(stateTone("FAULT")).toBe("danger"));
  it("formats energy values consistently", () => expect(formatNumber(22524.8)).toBe("22,524.80"));
});
