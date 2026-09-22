import { expect, test } from "@playwright/test";

async function reset(request: import("@playwright/test").APIRequestContext) {
  const response = await request.post("http://127.0.0.1:8000/api/admin/reset");
  expect(response.ok()).toBeTruthy();
}

async function login(page: import("@playwright/test").Page) {
  await page.goto("/login");
  await page.getByTestId("service-agreement").check();
  await page.getByTestId("login-button").click();
  await expect(page.getByTestId("station-list-page")).toBeVisible();
}

test.beforeEach(async ({ request }) => { await reset(request); });

test("login, navigate, stop and start device, then open Alarm Center", async ({ page }) => {
  await login(page);
  if (process.env.CAPTURE_UI) await page.screenshot({ path: "test-results/station-list.png", fullPage: true });
  await page.getByTestId("station-link").click();
  await expect(page.getByTestId("device-list-page")).toBeVisible();
  await page.getByTestId("device-link").click();
  await expect(page.getByTestId("device-detail-page")).toBeVisible();
  if (process.env.CAPTURE_UI) await page.screenshot({ path: "test-results/device-detail.png", fullPage: true });
  await expect(page.getByTestId("device-status")).toContainText("Running");

  await page.getByTestId("open-controls").click();
  if (process.env.CAPTURE_UI) await page.screenshot({ path: "test-results/control-drawer.png", fullPage: true });
  await page.getByTestId("stop-device-button").click();
  await expect(page.getByTestId("device-status")).toContainText("Offline");

  await page.getByTestId("start-device-button").click();
  await expect(page.getByTestId("device-status")).toContainText("Running");
  await page.getByLabel("Close controls").click();

  await page.getByTestId("nav-alarms").click();
  await expect(page.getByTestId("alarm-center-page")).toBeVisible();
  await expect(page.getByText("No alarms to show")).toBeVisible();
});

test("grid overvoltage scenario creates a consistent alarm and device state", async ({ page, request }) => {
  const scenario = await request.post("http://127.0.0.1:8000/api/admin/scenario", {
    data: { scenario: "GRID_OVERVOLTAGE" },
  });
  expect(scenario.ok()).toBeTruthy();
  await login(page);
  await page.getByTestId("nav-alarms").click();
  await expect(page.getByTestId("alarm-row")).toContainText("Grid overvoltage");
  await expect(page.getByTestId("alarm-row")).toContainText("Occurring");

  await page.getByTestId("nav-devices").click();
  await page.getByTestId("device-link").click();
  await expect(page.getByTestId("device-status")).toContainText("Fault");
  await expect(page.getByText("0.00", { exact: true }).first()).toBeVisible();

  const telemetry = await request.get("http://127.0.0.1:8000/api/devices/device-test-001/telemetry");
  expect(telemetry.ok()).toBeTruthy();
  expect((await telemetry.json()).phaseAVoltage).toBe(262);
  expect((await (await request.get("http://127.0.0.1:8000/api/devices/device-test-001/telemetry")).json()).activePowerKw).toBe(0);
});
