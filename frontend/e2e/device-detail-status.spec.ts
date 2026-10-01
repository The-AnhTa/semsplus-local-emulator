import { expect, test } from "@playwright/test";

const baseDevice = {
  id: "device-test-001",
  name: "Research Inverter 01",
  serialNumber: "INV-TEST-001",
  stationId: "station-test-01",
  stationName: "Test Station 01",
  deviceType: "On-Grid Inverter",
};

const runningDevice = {
  ...baseDevice,
  status: "RUNNING",
  activePowerKw: 6.42,
  dailyGenerationKwh: 31.8,
  rapidShutdown: false,
};

const shutdownDevice = {
  ...baseDevice,
  status: "RAPID_SHUTDOWN",
  activePowerKw: 0,
  dailyGenerationKwh: 0,
  rapidShutdown: true,
};

function telemetry(activePowerKw: number) {
  return {
    timestamp: "2026-10-01T12:00:00Z",
    activePowerKw,
    reactivePowerKvar: 0,
    powerFactor: activePowerKw ? 0.99 : 0,
    acFrequencyHz: 50.01,
    dailyEnergyKwh: activePowerKw ? 31.8 : 0,
    cumulativeEnergyKwh: 22524.8,
    pvPowerKw: activePowerKw,
    phaseAVoltage: 230.4,
    phaseBVoltage: 229.8,
    phaseCVoltage: 230.7,
    phaseACurrent: activePowerKw ? 9.29 : 0,
    phaseBCurrent: activePowerKw ? 9.1 : 0,
    phaseCCurrent: activePowerKw ? 9.38 : 0,
    temperatureC: activePowerKw ? 42.6 : 27,
  };
}

test("executed rapid shutdown refreshes canonical status, telemetry, and controls", async ({ page }) => {
  let executed = false;

  await page.addInitScript(() => localStorage.setItem("cer-session", "local-research-session"));
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;

    if (request.method() === "POST" && path === "/api/control/requests") {
      await route.fulfill({
        json: {
          requestId: "CR-000006",
          deviceId: "INV-TEST-001",
          action: "RAPID_SHUTDOWN",
          status: "PENDING",
          createdAt: "2026-10-01T12:00:00Z",
          expiresAt: "2026-10-01T12:02:00Z",
          decidedAt: null,
          executedAt: null,
          decisionSource: null,
          failureReason: null,
          previousState: "RUNNING",
          resultingState: "RUNNING",
        },
      });
      return;
    }
    if (request.method() === "GET" && path === "/api/control/requests/CR-000006") {
      executed = true;
      await route.fulfill({
        json: {
          requestId: "CR-000006",
          deviceId: "INV-TEST-001",
          action: "RAPID_SHUTDOWN",
          status: "EXECUTED",
          createdAt: "2026-10-01T12:00:00Z",
          expiresAt: "2026-10-01T12:02:00Z",
          decidedAt: "2026-10-01T12:00:05Z",
          executedAt: "2026-10-01T12:00:05Z",
          decisionSource: "controller",
          failureReason: null,
          previousState: "RUNNING",
          resultingState: "RAPID_SHUTDOWN",
        },
      });
      return;
    }
    if (request.method() === "GET" && path === "/api/devices/device-test-001") {
      await route.fulfill({ json: executed ? shutdownDevice : runningDevice });
      return;
    }
    if (request.method() === "GET" && path === "/api/devices/device-test-001/telemetry") {
      await route.fulfill({ json: telemetry(executed ? 0 : 6.42) });
      return;
    }
    if (request.method() === "GET" && path === "/api/devices/device-test-001/history") {
      if (executed) {
        await route.fulfill({ status: 503, json: { detail: "Synthetic history unavailable" } });
      } else {
        await route.fulfill({ json: [] });
      }
      return;
    }
    if (request.method() === "GET" && path === "/api/devices/device-test-001/mppt") {
      await route.fulfill({ json: [] });
      return;
    }
    await route.fulfill({ status: 404, json: { detail: `Unhandled mocked route ${path}` } });
  });

  await page.goto("/devices/device-test-001");
  await expect(page.getByTestId("device-status")).toHaveText("Running");
  await expect(page.getByTestId("active-power")).toContainText("6.42 kW");

  await page.getByTestId("open-controls").click();
  const rapidShutdown = page.getByTestId("rapid-shutdown-button");
  await expect(rapidShutdown).toBeEnabled();
  await rapidShutdown.click();

  await expect(page.getByTestId("approval-message")).toContainText("CR-000006 executed");
  await expect(page.getByTestId("device-status")).toHaveText("Rapid Shutdown");
  await expect(rapidShutdown).toBeDisabled();
  await expect(page.getByTestId("active-power")).toContainText("0.00 kW");
});
