/* Tests for the weather logic. Run: node test_weather.mjs
   No network: parsing is exercised against recorded Open-Meteo fixtures. */
import { readFileSync } from 'node:fs';
import { geocodeUrl, forecastUrl, parsePlaces, parseForecast, describeCode,
         classifyError, saveKey, loadKey, clearKey, maskKey } from './weather.js';

let pass=0, fail=0;
const ok=(n,c,x='')=>{c?(pass++,console.log(`  PASS  ${n}`)):(fail++,console.log(`  FAIL  ${n} ${x}`));};
const J = p => JSON.parse(readFileSync(new URL(p, import.meta.url)));
const fx = J('./fixtures/forecast_atlanta.json');
const geo = J('./fixtures/geocode_atlanta.json');

// --- URL building ---
ok('geocode url encodes the query', geocodeUrl('New York').includes('name=New+York'));
ok('geocode url handles punctuation', geocodeUrl("Coeur d'Alene").includes('Alene'));
ok('geocode rejects empty input', (()=>{try{geocodeUrl('  ');return false}catch{return true}})());
const fu = forecastUrl({latitude:33.749, longitude:-84.388});
ok('forecast url carries coordinates', fu.includes('latitude=33.7490') && fu.includes('longitude=-84.3880'));
ok('forecast url requests daily+hourly', fu.includes('daily=') && fu.includes('hourly='));
ok('forecast url defaults to celsius', !fu.includes('temperature_unit'));
ok('fahrenheit switches both units',
   forecastUrl({latitude:1,longitude:1,unit:'fahrenheit'}).includes('temperature_unit=fahrenheit') &&
   forecastUrl({latitude:1,longitude:1,unit:'fahrenheit'}).includes('wind_speed_unit=mph'));
ok('rejects missing coordinates', (()=>{try{forecastUrl({});return false}catch{return true}})());
ok('rejects out-of-range latitude',
   (()=>{try{forecastUrl({latitude:120,longitude:0});return false}catch{return true}})());
ok('rejects out-of-range longitude',
   (()=>{try{forecastUrl({latitude:0,longitude:200});return false}catch{return true}})());

// --- WMO codes ---
ok('code 0 is clear', describeCode(0).text === 'Clear sky');
ok('code 95 is a thunderstorm', /thunderstorm/i.test(describeCode(95).text));
ok('every code has an icon', [0,2,45,61,71,80,95,99].every(c=>describeCode(c).icon.length>0));
ok('unknown code degrades gracefully',
   describeCode(999).text.includes('999') && describeCode(999).icon === '❓');

// --- geocoding ---
const places = parsePlaces(geo);
ok('parses place results', places.length === 2);
ok('builds a human label', places[0].label === 'Atlanta, Georgia, United States', places[0].label);
ok('keeps coordinates numeric', typeof places[0].latitude === 'number');
ok('empty results yield []', parsePlaces(J('./fixtures/geocode_empty.json')).length === 0);
ok('null input yields []', parsePlaces(null).length === 0);

// --- forecast parsing ---
const f = parseForecast(fx);
ok('current temperature rounds', f.current.temperature === 31, String(f.current.temperature));
ok('feels-like rounds', f.current.feelsLike === 34);
ok('current condition described', f.current.text === 'Partly cloudy', f.current.text);
ok('daytime flag read', f.current.isDay === true);
ok('returns 7 days', f.days.length === 7, String(f.days.length));
ok('day highs and lows present', f.days.every(d=>d.high!=null && d.low!=null));
ok('every day has a description', f.days.every(d=>d.text && d.icon));
ok('rain chance carried through', f.days[1].rainChance === 80, String(f.days[1].rainChance));
ok('units read from the response', f.units.temperature === '°C');
ok('timezone carried through', f.timezone === 'America/New_York');

// the hourly filter is the subtle one: the feed starts before "now"
ok('hourly drops past hours', f.hours.length > 0 && new Date(f.hours[0].time) >= new Date(fx.current.time),
   `first=${f.hours[0]?.time} now=${fx.current.time}`);
ok('hourly caps at 24', f.hours.length <= 24, String(f.hours.length));
ok('hourly entries are described', f.hours.every(h=>h.text && h.icon));

// --- malformed responses ---
ok('missing current is rejected',
   (()=>{try{parseForecast({daily:{}});return false}catch{return true}})());
ok('missing daily is rejected',
   (()=>{try{parseForecast({current:{}});return false}catch{return true}})());
ok('null response is rejected',
   (()=>{try{parseForecast(null);return false}catch{return true}})());

// --- error classification ---
ok('401 mentions the key', /key/i.test(classifyError(null, 401)));
ok('429 mentions rate limiting', /too many/i.test(classifyError(null, 429)));
ok('500 blames the service', /service/i.test(classifyError(null, 500)));
ok('offline is explained', /connection/i.test(classifyError(new Error('Failed to fetch'))));
ok('unknown errors still say something', classifyError(new Error('weird')).length > 3);

// --- key handling ---
const mem = () => { const m=new Map(); return {
  getItem:k=>m.has(k)?m.get(k):null, setItem:(k,v)=>m.set(k,v), removeItem:k=>m.delete(k), _m:m }; };
const st = mem();
saveKey('abcd1234efgh5678', st);
ok('key saves and loads', loadKey(st) === 'abcd1234efgh5678');
clearKey(st);
ok('key clears', loadKey(st) === '');
ok('blank key clears rather than storing', (()=>{saveKey('x',st); saveKey('   ',st); return loadKey(st)===''})());
ok('storage failure is survivable',
   saveKey('k', {setItem(){throw new Error('blocked')}, getItem(){return null}, removeItem(){}}) === false);
ok('key is masked for display', maskKey('abcd1234efgh5678') === 'abcd••••••••5678',
   maskKey('abcd1234efgh5678'));
ok('short keys fully masked', maskKey('abc') === '•••');
ok('empty key masks to empty', maskKey('') === '');

console.log(`\n${pass}/${pass+fail} passed`);
process.exit(fail?1:0);
