import { runMonitorOnce } from "../lib/monitor.js";

export default async function handler(req, res) {
  if (req.method !== "POST") {
    return res.status(405).json({ ok: false, error: "Method not allowed" });
  }

  const authHeader = req.headers.authorization || "";
  const expected = process.env.CRON_SECRET ? `Bearer ${process.env.CRON_SECRET}` : "";
  if (expected && authHeader !== expected) {
    return res.status(401).json({ ok: false, error: "Unauthorized" });
  }

  const result = await runMonitorOnce("manual");
  const status = result.ok ? 200 : 500;
  return res.status(status).json(result);
}
