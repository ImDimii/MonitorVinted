import { runMonitorOnce } from "../lib/monitor.js";

export default async function handler(req, res) {
  const authHeader = req.headers.authorization || "";
  const expected = process.env.CRON_SECRET ? `Bearer ${process.env.CRON_SECRET}` : "";

  if (expected && authHeader !== expected) {
    return res.status(401).json({ ok: false, error: "Unauthorized" });
  }

  const result = await runMonitorOnce("cron");
  const status = result.ok ? 200 : 500;
  return res.status(status).json(result);
}
