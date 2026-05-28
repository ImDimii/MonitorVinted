const STATE_KEY = "vinted_monitor_state_v1";

async function upstashRequest(config, command, ...args) {
  const response = await fetch(`${config.upstashUrl}/${command}/${args.map(encodeURIComponent).join("/")}`, {
    method: "GET",
    headers: { Authorization: `Bearer ${config.upstashToken}` },
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Upstash error ${response.status}: ${text.slice(0, 300)}`);
  }
  return response.json();
}

export async function getState(config) {
  const result = await upstashRequest(config, "GET", STATE_KEY);
  if (!result?.result) {
    return { seenIds: [], cutoffTimestamp: 0, initialized: false, checks: 0, found: 0 };
  }

  try {
    return JSON.parse(result.result);
  } catch {
    return { seenIds: [], cutoffTimestamp: 0, initialized: false, checks: 0, found: 0 };
  }
}

export async function saveState(config, state) {
  const payload = JSON.stringify(state);
  await upstashRequest(config, "SET", STATE_KEY, payload);
}

export function normalizeState(state) {
  const seenIds = Array.isArray(state.seenIds) ? state.seenIds.map(String) : [];
  return {
    seenIds: seenIds.slice(-5000),
    cutoffTimestamp: Number(state.cutoffTimestamp || 0),
    initialized: Boolean(state.initialized),
    checks: Number(state.checks || 0),
    found: Number(state.found || 0),
    lastRunAt: state.lastRunAt || null,
    lastError: state.lastError || null,
  };
}
