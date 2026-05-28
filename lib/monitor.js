import { readConfig, validateConfig } from "./config.js";
import { getState, normalizeState, saveState } from "./state.js";
import { sendTelegramMessage, sendTelegramPhoto } from "./telegram.js";
import { buildItemMessage, fetchVintedItems, itemPhotoUrl, itemTimestamp } from "./vinted.js";

export async function runMonitorOnce(trigger = "manual") {
  const config = readConfig();
  const missing = validateConfig(config);
  if (missing.length > 0) {
    return {
      ok: false,
      error: `Missing env: ${missing.join(", ")}`,
      trigger,
    };
  }

  const loaded = await getState(config);
  const state = normalizeState(loaded);
  state.checks += 1;
  state.lastRunAt = new Date().toISOString();

  try {
    const { baseUrl, items } = await fetchVintedItems(config.vintedSearchUrl, config.maxItemsPerRun);

    if (!state.initialized) {
      const allIds = items.map((item) => String(item.id)).filter(Boolean);
      let maxTs = 0;
      for (const item of items) {
        maxTs = Math.max(maxTs, itemTimestamp(item));
      }

      state.seenIds = Array.from(new Set([...state.seenIds, ...allIds])).slice(-5000);
      state.cutoffTimestamp = maxTs > 0 ? maxTs : Math.floor(Date.now() / 1000);
      state.initialized = true;
      state.lastError = null;
      await saveState(config, state);

      await sendTelegramMessage(
        config.telegramBotToken,
        config.telegramChatId,
        `🟢 <b>Monitor Vinted avviato (Vercel Cron)</b>\n\n📦 Annunci iniziali: ${allIds.length}\n✅ Da ora in poi ricevi solo i nuovi.`,
      );

      return { ok: true, trigger, initialized: true, checks: state.checks, itemsFetched: items.length, newItems: 0 };
    }

    const seenSet = new Set(state.seenIds);
    const fetchedIds = [];
    const newItems = [];

    for (const item of items) {
      const id = String(item.id || "");
      if (!id) continue;
      fetchedIds.push(id);
      if (seenSet.has(id)) continue;

      const ts = itemTimestamp(item);
      if (ts > 0 && ts <= state.cutoffTimestamp) {
        continue;
      }

      newItems.push(item);
      if (ts > state.cutoffTimestamp) state.cutoffTimestamp = ts;
    }

    for (const item of newItems) {
      const caption = buildItemMessage(item, baseUrl);
      const photo = itemPhotoUrl(item);
      if (photo) {
        await sendTelegramPhoto(config.telegramBotToken, config.telegramChatId, photo, caption);
      } else {
        await sendTelegramMessage(config.telegramBotToken, config.telegramChatId, caption);
      }
    }

    state.found += newItems.length;
    state.seenIds = Array.from(new Set([...state.seenIds, ...fetchedIds])).slice(-5000);
    state.lastError = null;
    await saveState(config, state);

    return {
      ok: true,
      trigger,
      checks: state.checks,
      itemsFetched: items.length,
      newItems: newItems.length,
      totalFound: state.found,
      cutoffTimestamp: state.cutoffTimestamp,
    };
  } catch (error) {
    state.lastError = String(error?.message || error);
    await saveState(config, state);
    return { ok: false, trigger, checks: state.checks, error: state.lastError };
  }
}
