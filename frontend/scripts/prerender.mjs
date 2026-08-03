import { chromium } from "playwright"
import { execSync, spawn } from "child_process"
import { writeFileSync, mkdirSync, existsSync } from "fs"
import path from "path"
import { fileURLToPath } from "url"

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const ROOT = path.resolve(__dirname, "..")
const DIST = path.resolve(ROOT, "dist")
const BASE = "http://localhost:4173" + (process.env.VITE_BASE || "/").replace(/\/+$/, "")

const routes = [
  { path: "/", file: "index.html", expectedTitle: "Log In" },
  { path: "/login", file: "login/index.html", expectedTitle: "Log In" },
  { path: "/signup", file: "signup/index.html", expectedTitle: "Sign Up" },
]

if (!existsSync(DIST)) {
  console.error("dist/ not found — run `npm run build` first")
  process.exit(1)
}

const server = spawn("npx", ["vite", "preview", "--port", "4173", "--strictPort"], {
  cwd: ROOT,
  stdio: "ignore",
  detached: true,
  env: { ...process.env, VITE_BASE: process.env.VITE_BASE || "/" },
})

server.unref()
await new Promise((r) => setTimeout(r, 4000))

let browser
let hasBrowser = false
try {
  browser = await chromium.launch()
  hasBrowser = true
} catch {
  console.log("  ~ prerender skipped (no Playwright browser)")
}

if (hasBrowser) {
  for (const route of routes) {
    let page
    try {
      page = await browser.newPage()
      await page.goto(`${BASE}${route.path}`, { waitUntil: "networkidle", timeout: 15000 })
      await page.waitForSelector("#root > *", { timeout: 10000 })

    // Wait until the expected title appears (React Helmet has fired)
    await page.waitForFunction(
      (expected) => {
        const titles = document.head.querySelectorAll("title")
        for (const t of titles) {
          if (t.textContent.includes(expected)) return true
        }
        return false
      },
      route.expectedTitle,
      { timeout: 20000 },
    )

    // Remove the original index.html title (doesn't have " | " separator from Helmet)
    // and remove duplicate titles — keep only the one matching our expected title
    await page.evaluate((expected) => {
      const head = document.head
      const titles = head.querySelectorAll("title")
      let kept = false
      for (const t of titles) {
        if (!kept && t.textContent.includes(expected)) {
          kept = true // keep the first match
        } else {
          t.remove()
        }
      }
      // Same for meta description — keep only the last one
      const descs = head.querySelectorAll('meta[name="description"]')
      if (descs.length > 1) {
        for (let i = 0; i < descs.length - 1; i++) descs[i].remove()
      }
      // Remove duplicate canonical links — keep only the last one
      const canonicals = head.querySelectorAll('link[rel="canonical"]')
      if (canonicals.length > 1) {
        for (let i = 0; i < canonicals.length - 1; i++) canonicals[i].remove()
      }
    }, route.expectedTitle)

    const html = await page.content()
    const outPath = path.resolve(DIST, route.file)
    mkdirSync(path.dirname(outPath), { recursive: true })
    writeFileSync(outPath, html)

    console.log(`  ✓ ${route.path} → ${route.file}`)
    await page.close()
    } catch (err) {
      const dbg = await page.evaluate(() => ({
        url: location.href,
        titles: Array.from(document.head.querySelectorAll("title")).map((t) => t.textContent),
        rootChildren: document.querySelector("#root")?.childElementCount ?? -1,
      })).catch(() => null)
      console.log(`  ~ skipped ${route.path} (${err.message || err})`, dbg ? JSON.stringify(dbg) : "")
    }
  }

  await browser.close()
}

try {
  process.kill(-server.pid, "SIGTERM")
} catch {
  execSync("kill $(lsof -ti:4173) 2>/dev/null || true")
}

if (hasBrowser) console.log("Prerender complete.")
