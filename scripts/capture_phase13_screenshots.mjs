/** Capture recruiter-facing screenshots from the live FinAccess application. */

import { spawn } from "node:child_process";
import { copyFile, mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

const projectRoot = path.resolve(import.meta.dirname, "..");
const outputDir = path.join(projectRoot, "reports", "phase_13", "screenshots");
const deploymentScreenshotDir = path.join(projectRoot, "frontend", "docs", "screenshots");
const profileDir = path.join(projectRoot, ".runtime", "phase13-browser-profile");
const edgePath = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const debugPort = 9333;
const liveUrl = "https://finaccess-eswatini.vercel.app/";

const sleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

async function waitForJson(url, timeoutMs = 20_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url);
      if (response.ok) return response.json();
    } catch {
      // The debugging endpoint is expected to reject connections during startup.
    }
    await sleep(250);
  }
  throw new Error(`Timed out waiting for ${url}`);
}

function createCdpClient(socketUrl) {
  const socket = new WebSocket(socketUrl);
  const pending = new Map();
  let sequence = 0;

  const opened = new Promise((resolve, reject) => {
    socket.addEventListener("open", resolve, { once: true });
    socket.addEventListener("error", reject, { once: true });
  });

  socket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (!message.id || !pending.has(message.id)) return;
    const { resolve, reject } = pending.get(message.id);
    pending.delete(message.id);
    if (message.error) reject(new Error(message.error.message));
    else resolve(message.result);
  });

  return {
    async send(method, params = {}) {
      await opened;
      const id = ++sequence;
      const result = new Promise((resolve, reject) => pending.set(id, { resolve, reject }));
      socket.send(JSON.stringify({ id, method, params }));
      return result;
    },
    close() {
      socket.close();
    },
  };
}

async function main() {
  await mkdir(outputDir, { recursive: true });
  await mkdir(deploymentScreenshotDir, { recursive: true });
  await mkdir(profileDir, { recursive: true });

  const browser = spawn(
    edgePath,
    [
      "--headless=new",
      "--disable-gpu",
      "--hide-scrollbars",
      "--no-first-run",
      "--no-default-browser-check",
      `--remote-debugging-port=${debugPort}`,
      `--user-data-dir=${profileDir}`,
      "--window-size=1440,1050",
      liveUrl,
    ],
    { stdio: "ignore", windowsHide: true },
  );

  try {
    const targets = await waitForJson(`http://127.0.0.1:${debugPort}/json/list`);
    const page = targets.find((target) => target.type === "page" && target.url.startsWith(liveUrl));
    if (!page) throw new Error("The FinAccess browser target was not created.");

    const cdp = createCdpClient(page.webSocketDebuggerUrl);
    await cdp.send("Page.enable");
    await cdp.send("Runtime.enable");
    await cdp.send("Emulation.setDeviceMetricsOverride", {
      width: 1440,
      height: 1050,
      deviceScaleFactor: 1,
      mobile: false,
    });

    async function evaluate(expression, awaitPromise = false) {
      const result = await cdp.send("Runtime.evaluate", {
        expression,
        awaitPromise,
        returnByValue: true,
      });
      if (result.exceptionDetails) throw new Error(result.exceptionDetails.text);
      return result.result.value;
    }

    async function capture(filename, selector = null) {
      await evaluate("document.fonts.ready.then(() => true)", true);
      await sleep(500);
      const clip = selector
        ? await evaluate(`(() => {
            const element = document.querySelector(${JSON.stringify(selector)});
            if (!element) return null;
            const rect = element.getBoundingClientRect();
            const padding = 16;
            return {
              x: Math.max(0, rect.left + window.scrollX - padding),
              y: Math.max(0, rect.top + window.scrollY - padding),
              width: Math.min(document.documentElement.scrollWidth, rect.width + padding * 2),
              height: rect.height + padding * 2,
              scale: 1,
            };
          })()`)
        : undefined;
      if (selector && !clip) throw new Error(`Screenshot target not found: ${selector}`);
      const result = await cdp.send("Page.captureScreenshot", {
        format: "png",
        fromSurface: true,
        captureBeyondViewport: Boolean(clip),
        ...(clip ? { clip } : {}),
      });
      await writeFile(path.join(outputDir, filename), Buffer.from(result.data, "base64"));
      process.stdout.write(`${filename}\n`);
    }

    async function clickButton(label) {
      const clicked = await evaluate(`(() => {
        const button = [...document.querySelectorAll('button')]
          .find((candidate) => candidate.textContent.trim() === ${JSON.stringify(label)} && candidate.offsetParent !== null);
        if (!button) return false;
        button.click();
        return true;
      })()`);
      if (!clicked) throw new Error(`Button not found: ${label}`);
      await sleep(750);
      await evaluate("window.scrollTo(0, 0)");
    }

    await sleep(4_000);
    await evaluate("window.scrollTo(0, 0)");
    await capture("01_overview.png");

    await clickButton("Assessment");
    await capture("02_assessment.png", ".assessment-form");

    await clickButton("Continue");
    await clickButton("Continue");
    await clickButton("Generate assessment");
    const completed = await evaluate(`new Promise((resolve) => {
      const deadline = Date.now() + 60000;
      const check = () => {
        if (document.querySelector('.assessment-results')) return resolve(true);
        if (Date.now() > deadline) return resolve(false);
        setTimeout(check, 250);
      };
      check();
    })`, true);
    if (!completed) throw new Error("The live assessment did not complete within 60 seconds.");
    await evaluate("window.scrollTo(0, 0)");
    await capture("03_assessment_results.png", ".assessment-results");

    await clickButton("Methodology");
    await capture("04_methodology.png");

    // Capture the overview again after client-side navigation. Chromium's first
    // capture can precede the initial React paint on a cold serverless visit.
    await clickButton("Overview");
    await capture("01_overview.png");
    await copyFile(
      path.join(outputDir, "01_overview.png"),
      path.join(deploymentScreenshotDir, "overview.png"),
    );
    await copyFile(
      path.join(outputDir, "03_assessment_results.png"),
      path.join(deploymentScreenshotDir, "assessment-results.png"),
    );
    cdp.close();
  } finally {
    browser.kill();
  }
}

main().catch((error) => {
  process.stderr.write(`${error.stack || error.message}\n`);
  process.exitCode = 1;
});
