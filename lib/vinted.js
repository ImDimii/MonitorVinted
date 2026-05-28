function parseSearchUrl(searchUrl) {
  const parsed = new URL(searchUrl);
  const baseUrl = `${parsed.protocol}//${parsed.host}`;
  const params = new URLSearchParams(parsed.search);
  params.delete("page");
  params.delete("time");
  params.delete("search_id");
  params.set("order", params.get("order") || "newest_first");
  return { baseUrl, params };
}

function buildBaseHeaders(baseUrl) {
  return {
    accept: "application/json, text/plain, */*",
    "accept-language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
    referer: `${baseUrl}/`,
    origin: baseUrl,
    "user-agent":
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
  };
}

async function warmSession(baseUrl) {
  const response = await fetch(baseUrl, {
    method: "GET",
    headers: buildBaseHeaders(baseUrl),
  });

  const anonymousToken =
    response.headers.get("x-anonymous-token") ||
    response.headers.get("x-anon-token") ||
    response.headers.get("x-anon-id") ||
    "";

  let setCookies = [];
  if (typeof response.headers.getSetCookie === "function") {
    setCookies = response.headers.getSetCookie();
  } else {
    const raw = response.headers.get("set-cookie");
    if (raw) setCookies = [raw];
  }

  const cookieHeader = setCookies
    .map((cookie) => cookie.split(";")[0])
    .filter(Boolean)
    .join("; ");

  return { cookieHeader, anonymousToken };
}

async function callCatalogApi(apiUrl, headers) {
  const response = await fetch(apiUrl, { method: "GET", headers });
  if (response.ok) {
    const data = await response.json();
    return { status: response.status, data };
  }

  const text = await response.text();
  return { status: response.status, errorBody: text };
}

export async function fetchVintedItems(searchUrl, perPage = 20) {
  const { baseUrl, params } = parseSearchUrl(searchUrl);
  params.set("per_page", String(perPage));

  const apiUrl = `${baseUrl}/api/v2/catalog/items?${params.toString()}`;
  const warmed = await warmSession(baseUrl);

  const firstHeaders = buildBaseHeaders(baseUrl);
  if (warmed.cookieHeader) firstHeaders.cookie = warmed.cookieHeader;
  if (warmed.anonymousToken) firstHeaders["x-anonymous-token"] = warmed.anonymousToken;

  let result = await callCatalogApi(apiUrl, firstHeaders);

  // Alcuni edge Vinted richiedono il token anonimo anche come Bearer.
  if (!result.data && result.status === 401 && warmed.anonymousToken) {
    const retryHeaders = { ...firstHeaders, authorization: `Bearer ${warmed.anonymousToken}` };
    result = await callCatalogApi(apiUrl, retryHeaders);
  }

  if (!result.data) {
    throw new Error(`Vinted API error ${result.status}: ${(result.errorBody || "").slice(0, 300)}`);
  }

  const data = result.data;
  const items = Array.isArray(data?.items) ? data.items : [];
  return { baseUrl, items };
}

export function itemTimestamp(item) {
  const ts = Number(item?.created_at_ts || 0);
  if (Number.isFinite(ts) && ts > 0) return ts;

  const createdAt = item?.created_at;
  if (createdAt) {
    const date = new Date(createdAt);
    const parsed = date.getTime() / 1000;
    if (Number.isFinite(parsed) && parsed > 0) return parsed;
  }

  const photoTs = Number(item?.photo?.created_at_ts || 0);
  if (Number.isFinite(photoTs) && photoTs > 0) return photoTs;
  return 0;
}

export function buildItemMessage(item, baseUrl) {
  const title = item?.title || "Senza titolo";
  const priceObj = item?.price;
  let amount = "N/A";
  let currency = "EUR";

  if (priceObj && typeof priceObj === "object") {
    amount = priceObj.amount || "N/A";
    currency = priceObj.currency_code || "EUR";
  } else if (priceObj) {
    amount = String(priceObj);
    currency = item?.currency || "EUR";
  }

  let itemUrl = item?.url || "";
  if (itemUrl && !itemUrl.startsWith("http")) {
    itemUrl = `${baseUrl}${itemUrl}`;
  }

  const seller = item?.user?.login || "Sconosciuto";
  const brand = item?.brand_title || "";
  const size = item?.size_title || "";

  let message = [
    "🛍️ <b>Nuovo annuncio trovato!</b>",
    "━━━━━━━━━━━━━━━━━━━━━",
    `📌 <b>${title}</b>`,
    `💰 <b>${amount} ${currency}</b>`,
  ];

  if (brand) message.push(`🏷️ Marca: ${brand}`);
  if (size) message.push(`📏 Taglia: ${size}`);
  message = message.concat([
    `👤 Venditore: ${seller}`,
    "━━━━━━━━━━━━━━━━━━━━━",
    `🔗 <a href="${itemUrl}">Apri su Vinted</a>`,
  ]);

  return message.join("\n");
}

export function itemPhotoUrl(item) {
  const directPhoto = item?.photo;
  if (directPhoto) {
    for (const key of ["url", "full_size_url", "dominant_color_url"]) {
      if (directPhoto[key]) return directPhoto[key];
    }
  }

  const photos = item?.photos;
  if (Array.isArray(photos) && photos[0]?.url) return photos[0].url;
  return null;
}
