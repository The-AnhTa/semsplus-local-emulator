import { describe, expect, it } from "vitest";
import { formatNumber, humanizeState, stateTone } from "./utils";

describe("display helpers", () => {
  it("humanizes machine states", () => expect(humanizeState("RAPID_SHUTDOWN")).toBe("Rapid Shutdown"));
  it("maps fault states to a danger tone", () => expect(stateTone("FAULT")).toBe("danger"));
  it("formats energy values consistently", () => expect(formatNumber(22524.8)).toBe("22,524.80"));
});

