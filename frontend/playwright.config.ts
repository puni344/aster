import { defineConfig } from "@playwright/test";
import path from "node:path";
const python =
  process.platform === "win32"
    ? ".venv/Scripts/python.exe"
    : ".venv/bin/python";
export default defineConfig({
  testDir: "./tests",
  workers: 1,
  timeout: 50000,
  use: {
    baseURL: "http://127.0.0.1:8011",
    channel: process.env.ASTER_BROWSER || "msedge",
    launchOptions: {
      args: [
        "--use-fake-device-for-media-stream",
        "--autoplay-policy=no-user-gesture-required",
      ],
    },
  },
  webServer: {
    cwd: path.resolve(".."),
    command:
      '"' +
      path.resolve("..", python) +
      '"' +
      " -m uvicorn tests.browser_server:app --port 8011 --host 127.0.0.1 --no-access-log",
    url: "http://127.0.0.1:8011/api/dashboard",
    timeout: 60000,
    reuseExistingServer: false,
  },
});
