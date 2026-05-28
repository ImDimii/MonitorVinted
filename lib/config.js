const REQUIRED_ENV = ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "VINTED_SEARCH_URL"];

export function readConfig() {
  const config = {
    telegramBotToken: process.env.TELEGRAM_BOT_TOKEN || "",
    telegramChatId: process.env.TELEGRAM_CHAT_ID || "",
    vintedSearchUrl: process.env.VINTED_SEARCH_URL || "",
    maxItemsPerRun: Number(process.env.MAX_ITEMS_PER_RUN || "20"),
    upstashUrl: process.env.UPSTASH_REDIS_REST_URL || "",
    upstashToken: process.env.UPSTASH_REDIS_REST_TOKEN || "",
    cronSecret: process.env.CRON_SECRET || "",
  };
  return config;
}

export function validateConfig(config) {
  const missing = [];
  if (!config.telegramBotToken) missing.push("TELEGRAM_BOT_TOKEN");
  if (!config.telegramChatId) missing.push("TELEGRAM_CHAT_ID");
  if (!config.vintedSearchUrl) missing.push("VINTED_SEARCH_URL");
  if (!config.upstashUrl) missing.push("UPSTASH_REDIS_REST_URL");
  if (!config.upstashToken) missing.push("UPSTASH_REDIS_REST_TOKEN");
  return missing;
}

export function requiredEnvNames() {
  return REQUIRED_ENV;
}
