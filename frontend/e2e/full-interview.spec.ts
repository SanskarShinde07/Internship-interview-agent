import { expect, test } from "@playwright/test";

// docs/BLUEPRINT.md §18: "a scripted Playwright test that drives one full
// interview through a test-mode backend flag, asserting the flow reaches
// COMPLETED and a report is produced." This is that test - Landing through
// the Coach, entirely through the rendered UI, against the stub-gateway
// backend started by playwright.config.ts.

const MAX_TURNS = 60;
const GENERIC_ANSWER =
  "This is a thorough answer explaining my reasoning, trade-offs, and relevant experience with this topic in detail.";

test("full interview journey: landing through coach", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("pageerror", (err) => consoleErrors.push(String(err)));
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });

  await page.goto("/");
  await expect(page.getByRole("banner").getByText("InterVue AI")).toBeVisible();
  await expect(
    page.getByRole("heading", { name: /practice interviews that actually adapt to you/i }),
  ).toBeVisible();

  // Starting an interview requires an account - the landing page's CTA
  // sends a signed-out visitor to /login instead of straight to /setup.
  await page.getByRole("link", { name: /start mock interview/i }).click();
  await page.waitForURL("**/login");
  await page.getByRole("main").getByRole("link", { name: /sign up/i }).click();
  await page.waitForURL("**/register");
  await page.getByPlaceholder("you@example.com").fill(`e2e-${Date.now()}@example.com`);
  await page.getByPlaceholder("At least 8 characters").fill("e2e-test-password-123");
  await page.getByPlaceholder("••••••••").fill("e2e-test-password-123");
  await page.getByRole("button", { name: /sign up/i }).click();
  await page.waitForURL("**/history");
  await page.getByRole("link", { name: /start mock interview/i }).click();

  await page.waitForURL("**/setup");
  await page.getByPlaceholder("Ada Lovelace").fill("Playwright E2E");
  await page.getByRole("button", { name: /continue/i }).click();

  await page.waitForURL(/\/instructions\//);
  await page.getByRole("button", { name: /start the interview/i }).click();

  await page.waitForURL(/\/interview\//);

  for (let turn = 0; turn < MAX_TURNS; turn += 1) {
    if (page.url().includes("/complete/")) break;

    // Wait for the textarea to be genuinely ready for input - visible AND
    // enabled, not just visible. A plain waitFor({state: "visible"}) will
    // happily resolve while the textarea is still disabled (mid-transition
    // from the previous submit, or permanently once the final answer's
    // response leaves it disabled while the page navigates away) - and
    // then fill() hangs retrying against a control that never becomes
    // enabled, silently eating the rest of the test's timeout budget on
    // what looks like the last turn.
    const textarea = page.locator("textarea");
    try {
      await expect(textarea).toBeEnabled({ timeout: 10_000 });
    } catch {
      break; // still disabled after 10s - the interview finished
    }
    await textarea.fill(GENERIC_ANSWER);

    // Wait for the specific /answer response rather than
    // waitForLoadState("networkidle"): Next.js dev mode's background
    // activity (HMR websocket, dev tools panel) means the network never
    // truly goes idle, which made each turn take ~15s for no reason.
    await Promise.all([
      page.waitForResponse(
        (response) =>
          response.url().includes("/answer") && response.request().method() === "POST",
        { timeout: 20_000 },
      ),
      page.getByRole("button", { name: /submit answer/i }).click(),
    ]);
  }

  // The completion page auto-redirects to the report after ~1.8s, so by the
  // time this check runs we may have already passed through /complete/ -
  // waiting directly for /report/ is what actually proves the interview
  // reached COMPLETED and a report was produced.
  await page.waitForURL(/\/report\//, { timeout: 15_000 });
  await expect(page.getByRole("heading", { name: "Your Recruiter Report" })).toBeVisible();
  await expect(page.getByText("out of 100")).toBeVisible();

  await page.getByRole("link", { name: /view analytics/i }).click();
  await page.waitForURL(/\/analytics\//);
  await expect(page.getByRole("heading", { name: "Interview Analytics" })).toBeVisible();
  await expect(page.getByText("100%")).toBeVisible(); // completion rate on a finished interview

  await page.goBack();
  await page.waitForURL(/\/report\//);
  await page.getByRole("link", { name: /ask the coach/i }).click();
  await page.waitForURL(/\/coach\//);
  await expect(page.getByRole("heading", { name: "Post-Interview Coach" })).toBeVisible();

  await page.getByPlaceholder("Ask the coach...").fill("What should I study next?");
  await page.getByRole("button", { name: /send/i }).click();
  await expect(page.locator("main")).toContainText("What should I study next?", {
    timeout: 10_000,
  });

  expect(consoleErrors, `Unexpected browser console errors: ${consoleErrors.join("; ")}`).toEqual(
    [],
  );
});
