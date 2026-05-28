import { runMonitorOnce } from "../lib/monitor.js";

export default async function handler(req, res) {
  if (req.method !== "POST" && req.method !== "GET") {
    return res.status(405).json({ ok: false, error: "Method not allowed" });
  }

  const authHeader = req.headers.authorization || "";
  const querySecret = typeof req.query?.secret === "string" ? req.query.secret : "";
  const expectedSecret = process.env.CRON_SECRET || "";
  const expectedBearer = expectedSecret ? `Bearer ${expectedSecret}` : "";
  const validByHeader = expectedBearer && authHeader === expectedBearer;
  const validByQuery = expectedSecret && querySecret === expectedSecret;

  if (expectedSecret && !validByHeader && !validByQuery) {
    return res.status(401).json({ ok: false, error: "Unauthorized" });
  }

  const trigger = req.method === "GET" ? "cron-job-org" : "manual";
  const result = await runMonitorOnce(trigger);
  const status = result.ok ? 200 : 500;
  return res.status(status).json(result);
}
