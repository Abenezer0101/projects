/* Weather logic — pure functions, no DOM, no network.
 *
 * Everything that can be wrong without a network round-trip lives here:
 * URL construction, response mapping, WMO code translation, unit conversion
 * and error classification. The UI only renders what these return, which is
 * what makes the app testable without hitting a live API.
 */

export const GEOCODE_URL = 'https://geocoding-api.open-meteo.com/v1/search';
export const FORECAST_URL = 'https://api.open-meteo.com/v1/forecast';

/* WMO 4677 weather codes. Open-Meteo returns an integer; a human needs words. */
const WMO = {
  0:['Clear sky','☀️'], 1:['Mainly clear','🌤️'], 2:['Partly cloudy','⛅'], 3:['Overcast','☁️'],
  45:['Fog','🌫️'], 48:['Freezing fog','🌫️'],
  51:['Light drizzle','🌦️'], 53:['Drizzle','🌦️'], 55:['Heavy drizzle','🌦️'],
  56:['Freezing drizzle','🌧️'], 57:['Freezing drizzle','🌧️'],
  61:['Light rain','🌧️'], 63:['Rain','🌧️'], 65:['Heavy rain','🌧️'],
  66:['Freezing rain','🌧️'], 67:['Freezing rain','🌧️'],
  71:['Light snow','🌨️'], 73:['Snow','🌨️'], 75:['Heavy snow','🌨️'], 77:['Snow grains','🌨️'],
  80:['Light showers','🌦️'], 81:['Showers','🌦️'], 82:['Violent showers','⛈️'],
  85:['Snow showers','🌨️'], 86:['Heavy snow showers','🌨️'],
  95:['Thunderstorm','⛈️'], 96:['Thunderstorm with hail','⛈️'], 99:['Severe thunderstorm','⛈️'],
};

export function describeCode(code) {
  const hit = WMO[code];
  return hit ? { text: hit[0], icon: hit[1] }
             : { text: `Unknown conditions (code ${code})`, icon: '❓' };
}

/* ------------------------------------------------------------------ URLs */

export function geocodeUrl(query, count = 5) {
  const q = String(query ?? '').trim();
  if (!q) throw new Error('Enter a place name');
  const u = new URL(GEOCODE_URL);
  u.searchParams.set('name', q);
  u.searchParams.set('count', String(count));
  u.searchParams.set('language', 'en');
  u.searchParams.set('format', 'json');
  return u.toString();
}

export function forecastUrl({ latitude, longitude, unit = 'celsius' }) {
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude))
    throw new Error('Coordinates are required');
  if (latitude < -90 || latitude > 90) throw new Error('Latitude out of range');
  if (longitude < -180 || longitude > 180) throw new Error('Longitude out of range');
  const u = new URL(FORECAST_URL);
  u.searchParams.set('latitude', latitude.toFixed(4));
  u.searchParams.set('longitude', longitude.toFixed(4));
  u.searchParams.set('current', 'temperature_2m,relative_humidity_2m,apparent_temperature,' +
                                'is_day,precipitation,weather_code,wind_speed_10m');
  u.searchParams.set('hourly', 'temperature_2m,precipitation_probability,weather_code');
  u.searchParams.set('daily', 'weather_code,temperature_2m_max,temperature_2m_min,' +
                              'precipitation_probability_max,sunrise,sunset');
  u.searchParams.set('timezone', 'auto');
  u.searchParams.set('forecast_days', '7');
  if (unit === 'fahrenheit') {
    u.searchParams.set('temperature_unit', 'fahrenheit');
    u.searchParams.set('wind_speed_unit', 'mph');
  }
  return u.toString();
}

/* ------------------------------------------------------------- transforms */

export function parsePlaces(json) {
  const results = json?.results;
  if (!Array.isArray(results) || results.length === 0) return [];
  return results.map(r => ({
    name: r.name,
    admin: r.admin1 || '',
    country: r.country || '',
    countryCode: r.country_code || '',
    latitude: r.latitude,
    longitude: r.longitude,
    timezone: r.timezone,
    label: [r.name, r.admin1, r.country].filter(Boolean).join(', '),
  }));
}

export function parseForecast(json) {
  if (!json || !json.current || !json.daily)
    throw new Error('Unexpected response shape from the weather service');

  const c = json.current, d = json.daily, h = json.hourly;
  const current = {
    temperature: round(c.temperature_2m),
    feelsLike: round(c.apparent_temperature),
    humidity: c.relative_humidity_2m,
    precipitation: c.precipitation,
    windSpeed: round(c.wind_speed_10m),
    isDay: c.is_day === 1,
    ...describeCode(c.weather_code),
    code: c.weather_code,
    time: c.time,
  };

  const days = (d.time || []).map((date, i) => ({
    date,
    high: round(d.temperature_2m_max?.[i]),
    low: round(d.temperature_2m_min?.[i]),
    rainChance: d.precipitation_probability_max?.[i] ?? null,
    sunrise: d.sunrise?.[i],
    sunset: d.sunset?.[i],
    ...describeCode(d.weather_code?.[i]),
  }));

  // Hourly comes back as a flat 7-day array; only the next 24h is useful.
  let hours = [];
  if (h?.time) {
    const now = new Date(c.time).getTime();
    hours = h.time.map((t, i) => ({
      time: t,
      temperature: round(h.temperature_2m?.[i]),
      rainChance: h.precipitation_probability?.[i] ?? null,
      ...describeCode(h.weather_code?.[i]),
    })).filter(x => new Date(x.time).getTime() >= now).slice(0, 24);
  }

  return {
    current, days, hours,
    units: {
      temperature: json.current_units?.temperature_2m || '°C',
      wind: json.current_units?.wind_speed_10m || 'km/h',
    },
    timezone: json.timezone,
  };
}

const round = n => (n == null ? null : Math.round(n));

/** Turn a failed request into something a person can act on. */
export function classifyError(err, status) {
  if (status === 401 || status === 403) return 'That API key was rejected. Check it and try again.';
  if (status === 429) return 'Too many requests — wait a minute and retry.';
  if (status === 404) return 'The weather service had no data for that location.';
  if (status && status >= 500) return 'The weather service is having problems. Try again shortly.';
  const msg = String(err?.message || err || '');
  if (/failed to fetch|networkerror|load failed/i.test(msg))
    return 'Could not reach the weather service. Check your connection.';
  return msg || 'Something went wrong.';
}

/* ------------------------------------------------------------------ keys
 * Open-Meteo needs no key. For an optional keyed provider the key is held in
 * sessionStorage, never localStorage: it dies with the tab, so it cannot sit
 * on disk waiting to be found, and it is never written to a file that could
 * be committed. */
const KEY_NAME = 'weather-app-optional-key';

export function saveKey(key, storage = sessionStorage) {
  const k = String(key ?? '').trim();
  if (!k) { clearKey(storage); return false; }
  try { storage.setItem(KEY_NAME, k); return true; } catch { return false; }
}
export function loadKey(storage = sessionStorage) {
  try { return storage.getItem(KEY_NAME) || ''; } catch { return ''; }
}
export function clearKey(storage = sessionStorage) {
  try { storage.removeItem(KEY_NAME); } catch { /* nothing to do */ }
}
export function maskKey(key) {
  const k = String(key || '');
  if (!k) return '';
  return k.length <= 8 ? '•'.repeat(k.length) : k.slice(0, 4) + '•'.repeat(k.length - 8) + k.slice(-4);
}
