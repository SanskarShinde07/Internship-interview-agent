import { defineConfig, devices } from "@playwright/test";

// docs/BLUEPRINT.md §18/§19 Phase 8: "a scripted Playwright test that
// drives one full interview through a test-mode backend flag." The
// backend server here is that test-mode flag: a throwaway, freshly
// seeded SQLite DB with the stub AI gateway forced on (see
// backend/scripts/run_e2e_server.sh), so this suite is deterministic
// and never depends on - or spends quota against - a live model.

const BACKEND_PORT = 8765;
const FRONTEND_PORT = 3100;

export default defineConfig({
  testDir: "./e2e",
  // A full ~30-question interview exceeds Playwright's 30s default even
  // once each turn is fast; generous headroom here beats a flaky timeout.
  timeout: 120_000,
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: "list",
  use: {
    baseURL: `http://localhost:${FRONTEND_PORT}`,
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: `bash ../backend/scripts/run_e2e_server.sh ${BACKEND_PORT}`,
      url: `http://localhost:${BACKEND_PORT}/api/v1/health`,
      timeout: 60_000,
      reuseExistingServer: false,
    },
    {
      command: `npm run dev -- --port ${FRONTEND_PORT}`,
      url: `http://localhost:${FRONTEND_PORT}`,
      timeout: 60_000,
      reuseExistingServer: false,
      env: {
        NEXT_PUBLIC_API_BASE_URL: `http://localhost:${BACKEND_PORT}/api/v1`,
      },
    },
  ],
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
