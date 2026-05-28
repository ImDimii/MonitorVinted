import { readConfig } from "../lib/config.js";
import { getState, normalizeState } from "../lib/state.js";

export default async function handler(req, res) {
  try {
    const config = readConfig();
    const state = normalizeState(await getState(config));
    return res.status(200).json({
      ok: true,
      checks: state.checks,
      totalFound: state.found,
      initialized: state.initialized,
      lastRunAt: state.lastRunAt,
      lastError: state.lastError,
      seenItemsCount: state.seenIds.length,
    });
  } catch (error) {
    return res.status(500).json({ ok: false, error: String(error?.message || error) });
  }
}
