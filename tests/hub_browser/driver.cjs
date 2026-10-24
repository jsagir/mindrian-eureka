"use strict";
// Scenario-driven Playwright runner for the hub tests.
//
// Usage: node driver.cjs --playwright DIR --scenario FILE
// It prints one JSON object to stdout and exits 0, even when a page check fails.
// It exits 2 with a plain message on stderr only for driver errors.
//
// Network rule: every request to http, https, ws, wss or ftp is aborted and recorded in
// `blockedRequests`. A page that obeys the offline rule shows an empty list.

const fs = require("fs");
const path = require("path");

const REMOTE = /^(https?|wss?|ftp):/i;
const LOCAL = /^(file|data|blob):/i;
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;

function fail(message) {
  process.stderr.write(String(message) + "\n");
  process.exit(2);
}

function parseArgs(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i] === "--playwright") out.playwright = argv[++i];
    else if (argv[i] === "--scenario") out.scenario = argv[++i];
    else fail("unknown argument: " + argv[i]);
  }
  if (!out.playwright || !out.scenario) {
    fail("usage: driver.cjs --playwright DIR --scenario FILE");
  }
  return out;
}

function stripQuery(url) {
  const cut = url.search(/[?#]/);
  const clean = cut === -1 ? url : url.slice(0, cut);
  return clean.length > 200 ? clean.slice(0, 200) : clean;
}

function launchOptions(scenario) {
  const webgl = scenario.webgl !== false;
  const block = scenario.blockNetwork !== false;
  const options = { headless: true };
  if (scenario.browser === "chromium") {
    options.args = webgl
      ? [
          "--use-gl=angle",
          "--use-angle=swiftshader",
          "--enable-unsafe-swiftshader",
          "--ignore-gpu-blocklist",
        ]
      : ["--disable-gpu", "--disable-3d-apis"];
    // Second layer: no host name resolves, so a request that skips the route still fails.
    if (block) options.args.push("--host-resolver-rules=MAP * ~NOTFOUND");
  } else if (scenario.browser === "firefox") {
    const prefs = {};
    if (!webgl) prefs["webgl.disabled"] = true;
    if (block) {
      // Second layer: all remote traffic goes to a closed local port. Firefox does not
      // route some upgraded image requests, so the route alone is not enough.
      prefs["network.proxy.type"] = 1;
      prefs["network.proxy.http"] = "127.0.0.1";
      prefs["network.proxy.http_port"] = 9;
      prefs["network.proxy.ssl"] = "127.0.0.1";
      prefs["network.proxy.ssl_port"] = 9;
      prefs["network.proxy.no_proxies_on"] = "";
    }
    options.firefoxUserPrefs = prefs;
  }
  return options;
}

function readBody(file) {
  return fs.readFileSync(file, "utf8");
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  let scenario;
  try {
    scenario = JSON.parse(fs.readFileSync(args.scenario, "utf8"));
  } catch (error) {
    fail("cannot read scenario: " + error.message);
  }
  let playwright;
  try {
    playwright = require(path.resolve(args.playwright));
  } catch (error) {
    fail("cannot load playwright: " + error.message);
  }
  const kind = playwright[scenario.browser || "chromium"];
  if (!kind) fail("unknown browser: " + scenario.browser);

  let browser;
  try {
    browser = await kind.launch(launchOptions(scenario));
  } catch (error) {
    fail("browser cannot start (" + scenario.browser + "): " + String(error.message).split("\n")[0]);
  }

  const result = {
    browser: scenario.browser || "chromium",
    version: browser.version(),
    ok: false,
    results: {},
    screenshots: [],
    blockedRequests: [],
    localRequests: [],
    console: [],
    pageErrors: [],
    cspViolations: [],
    stepErrors: [],
  };
  const timeoutMs = scenario.timeoutMs || 30000;
  let context;
  try {
    const contextOptions = {
      viewport: scenario.viewport || { width: 1280, height: 800 },
      javaScriptEnabled: scenario.javaScript !== false,
      reducedMotion: scenario.reducedMotion ? "reduce" : "no-preference",
      forcedColors: scenario.forcedColors === "active" ? "active" : "none",
      serviceWorkers: "block",
      acceptDownloads: false,
      locale: "en-US",
      timezoneId: "UTC",
    };
    context = await browser.newContext(contextOptions);
    context.setDefaultTimeout(timeoutMs);
    context.setDefaultNavigationTimeout(timeoutMs);

    // Every remote attempt is recorded once per URL and type. The route aborts the request.
    // The request event is a second source: Firefox does not route some upgraded requests.
    const seen = new Set();
    const noteRemote = (url, type, method) => {
      const clean = stripQuery(url);
      const key = clean + "|" + type;
      if (seen.has(key)) return;
      seen.add(key);
      result.blockedRequests.push({ url: clean, type, method });
    };
    if (scenario.blockNetwork !== false) {
      await context.route(
        (url) => REMOTE.test(url.toString()),
        async (route) => {
          const request = route.request();
          noteRemote(request.url(), request.resourceType(), request.method());
          await route.abort("blockedbyclient");
        },
      );
      await context.routeWebSocket(/^wss?:/i, (socket) => {
        noteRemote(socket.url(), "websocket", "GET");
        socket.close();
      });
    }

    await context.addInitScript(() => {
      window.__csp = [];
      document.addEventListener(
        "securitypolicyviolation",
        (event) => {
          window.__csp.push({
            directive: event.effectiveDirective,
            blocked: String(event.blockedURI || "").slice(0, 200),
          });
        },
        true,
      );
    });
    for (const file of scenario.initScripts || []) {
      await context.addInitScript({ path: file });
    }

    const page = await context.newPage();
    // Chromium reports file requests. Firefox reports none for file URLs.
    page.on("request", (request) => {
      if (LOCAL.test(request.url())) {
        result.localRequests.push(stripQuery(request.url()));
      } else if (REMOTE.test(request.url())) {
        noteRemote(request.url(), request.resourceType(), request.method());
      }
    });
    page.on("console", (message) => {
      result.console.push({ type: message.type(), text: message.text().slice(0, 500) });
    });
    page.on("pageerror", (error) => {
      result.pageErrors.push(String(error.message || error).slice(0, 500));
    });

    const harvestCsp = async () => {
      if (scenario.javaScript === false) return;
      try {
        const list = await page.evaluate(() => window.__csp || []);
        for (const item of list) result.cspViolations.push(item);
      } catch (error) {
        // The page may be closed or navigating. Missing data is acceptable here.
      }
    };

    const steps = [];
    if (scenario.url) steps.push({ kind: "goto", url: scenario.url });
    for (const step of scenario.steps || []) steps.push(step);

    let allRan = true;
    for (let index = 0; index < steps.length; index += 1) {
      const step = steps[index];
      try {
        switch (step.kind) {
          case "goto":
            await harvestCsp();
            await page.goto(step.url, { waitUntil: "load" });
            break;
          case "reload":
            await harvestCsp();
            await page.reload({ waitUntil: "load" });
            break;
          case "click":
            await page.click(step.selector);
            break;
          case "fill":
            await page.fill(step.selector, step.value);
            break;
          case "press":
            await page.press(step.selector || "body", step.key);
            break;
          case "hover":
            await page.hover(step.selector);
            break;
          case "focus":
            await page.focus(step.selector);
            break;
          case "wait":
            await page.waitForTimeout(step.ms);
            break;
          case "waitFor":
            await page.waitForSelector(step.selector, { state: step.state || "attached" });
            break;
          case "waitForFunction": {
            const body = readBody(step.file);
            await page.waitForFunction(new Function(body));
            break;
          }
          case "setViewport":
            await page.setViewportSize({ width: step.width, height: step.height });
            break;
          case "screenshot":
            await page.screenshot({ path: step.path, fullPage: Boolean(step.fullPage) });
            result.screenshots.push(step.path);
            break;
          case "dom": {
            const html = await page.content();
            if (step.path) fs.writeFileSync(step.path, html);
            if (step.as) result.results[step.as] = html;
            break;
          }
          case "eval": {
            const fn = new AsyncFunction("args", readBody(step.file));
            const value = await page.evaluate(fn, step.args === undefined ? {} : step.args);
            if (step.as) result.results[step.as] = value;
            break;
          }
          default:
            throw new Error("unknown step kind: " + step.kind);
        }
      } catch (error) {
        allRan = false;
        result.stepErrors.push({ step: index, message: String(error.message).split("\n")[0] });
        break;
      }
    }
    await harvestCsp();
    result.ok = allRan;
  } catch (error) {
    result.stepErrors.push({ step: -1, message: String(error.message).split("\n")[0] });
  } finally {
    if (context) await context.close().catch(() => {});
    await browser.close().catch(() => {});
  }
  process.stdout.write(JSON.stringify(result) + "\n");
}

main().then(
  () => process.exit(0),
  (error) => fail("driver error: " + (error && error.message ? error.message : error)),
);
