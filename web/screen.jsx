/* Screen.jsx — Family E-Paper Display, Nest Hub aesthetic
 * 800x480, 1-bit (pure black/white), Rubik font, Material Symbols icons.
 *
 * Composition:
 *   ┌─────────────────────────────────────────────┐
 *   │  HEADER STRIP                               │
 *   │  weekday + date (right)         time (left) │
 *   ├─────────────────────────────────────────────┤
 *   │  CARDS ROW                                  │
 *   │  ┌────────┐  ┌────────┐  ┌────────┐         │
 *   │  │מזג אוויר│  │  לוח    │  │ עומר  │         │
 *   │  └────────┘  └────────┘  └────────┘         │
 *   ├─────────────────────────────────────────────┤
 *   │  SHABBAT STRIP (only Fri/Sat)               │
 *   └─────────────────────────────────────────────┘
 *
 * Reserved zones (firmware overpaints):
 *   battery icon: x=8..38, y=442..472   (we keep this corner clear)
 */

const SCREEN_W = 800;
const SCREEN_H = 480;

// --- Moon phase from a YYYY-MM-DD or DD.MM.YYYY string ---------------------
// Returns a value in [0, 1): 0 = new, 0.25 = first quarter, 0.5 = full, 0.75 = last
function moonPhaseFromDate(dateStr) {
  if (!dateStr) return 0.5;
  let y, m, d;
  // try DD.MM.YYYY first
  const a = String(dateStr).match(/^(\d{1,2})\.(\d{1,2})\.(\d{4})$/);
  if (a) { d = +a[1]; m = +a[2]; y = +a[3]; }
  else {
    const b = String(dateStr).match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);
    if (b) { y = +b[1]; m = +b[2]; d = +b[3]; }
    else return 0.5;
  }
  // Conway's algorithm (approximate, ±1 day accurate)
  if (m < 3) { y -= 1; m += 12; }
  const c = Math.floor(365.25 * y);
  const e = Math.floor(30.6 * (m + 1));
  const jd = c + e + d - 694039.09; // days since known new moon
  const cycle = jd / 29.5305882;
  return cycle - Math.floor(cycle);
}

// --- Material Symbols glyph helper -----------------------------------------
// We use the "Material Symbols Outlined" font, but we want everything to be
// strictly 1-bit. We render glyphs at 1.5em weight 400, fill="black" — they
// rasterize to clean black on white.
function MIcon({ name, size = 24, weight = 400 }) {
  return (
    <span
      className="material-symbols-outlined"
      style={{
        fontSize: size,
        fontVariationSettings: `'FILL' 0, 'wght' ${weight}, 'GRAD' 0, 'opsz' 24`,
        lineHeight: 1,
        color: '#000',
        userSelect: 'none',
      }}
    >
      {name}
    </span>
  );
}

// --- Weather glyph (big iconographic SVG, 1-bit clean) ----------------------
function WeatherGlyph({ kind = 'sun', size = 84, ...opts }) {
  // kinds: sun, cloudy_sun, cloudy, rainy, stormy, snow, night, fog
  const s = size;
  const sw = Math.max(2, Math.round(size / 28)); // stroke width scales
  const common = {
    width: s, height: s, viewBox: '0 0 100 100',
    fill: 'none', stroke: '#000', strokeWidth: sw * (100 / s),
    strokeLinecap: 'round', strokeLinejoin: 'round',
  };
  if (kind === 'sun') {
    return (
      <svg {...common}>
        <circle cx="50" cy="50" r="18" fill="#000" stroke="none" />
        {Array.from({length: 8}).map((_, i) => {
          const a = (i * 45) * Math.PI / 180;
          const x1 = 50 + Math.cos(a) * 28;
          const y1 = 50 + Math.sin(a) * 28;
          const x2 = 50 + Math.cos(a) * 40;
          const y2 = 50 + Math.sin(a) * 40;
          return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} />;
        })}
      </svg>
    );
  }
  if (kind === 'cloudy_sun') {
    return (
      <svg {...common}>
        <circle cx="35" cy="38" r="14" fill="#000" stroke="none" />
        {[0, 45, 90, 135, 180, 225, 270, 315].map((d, i) => {
          const a = d * Math.PI / 180;
          return <line key={i}
            x1={35 + Math.cos(a) * 22} y1={38 + Math.sin(a) * 22}
            x2={35 + Math.cos(a) * 30} y2={38 + Math.sin(a) * 30} />;
        })}
        <path d="M 30 70 Q 25 58 38 56 Q 42 46 56 50 Q 70 46 74 60 Q 86 60 84 72 Q 86 82 74 82 L 36 82 Q 24 82 30 70 Z" fill="#fff" stroke="#000" />
      </svg>
    );
  }
  if (kind === 'cloudy') {
    return (
      <svg {...common}>
        <path d="M 22 60 Q 16 46 32 44 Q 36 30 54 35 Q 70 30 76 50 Q 88 50 86 64 Q 88 76 74 76 L 28 76 Q 14 76 22 60 Z" fill="#fff" stroke="#000" />
      </svg>
    );
  }
  if (kind === 'rainy') {
    return (
      <svg {...common}>
        <path d="M 22 50 Q 16 36 32 34 Q 36 22 54 27 Q 70 22 76 42 Q 88 42 86 56 Q 88 66 74 66 L 28 66 Q 14 66 22 50 Z" fill="#fff" stroke="#000" />
        <line x1="32" y1="74" x2="28" y2="86" />
        <line x1="50" y1="74" x2="46" y2="86" />
        <line x1="68" y1="74" x2="64" y2="86" />
      </svg>
    );
  }
  if (kind === 'stormy') {
    return (
      <svg {...common}>
        <path d="M 22 46 Q 16 32 32 30 Q 36 18 54 23 Q 70 18 76 38 Q 88 38 86 52 Q 88 62 74 62 L 28 62 Q 14 62 22 46 Z" fill="#fff" stroke="#000" />
        <path d="M 52 64 L 40 80 L 48 80 L 42 92 L 58 74 L 50 74 L 56 64 Z" fill="#000" stroke="none" />
      </svg>
    );
  }
  if (kind === 'night') {
    // Moon phase — phase ∈ [0..1], 0=new, 0.25=first quarter, 0.5=full, 0.75=last
    const phase = (typeof opts.phase === 'number') ? opts.phase : 0.5;
    return (
      <svg {...common}>
        {/* base disc */}
        <circle cx="50" cy="50" r="30" fill="#fff" stroke="#000" />
        {/* shadow path — depending on phase, fill from one side using two arcs */}
        {(() => {
          // Compute the shaded portion as a closed path.
          // Outer arc: half-circle of moon.
          // Inner arc: ellipse with rx scaled by cos(phase * 2π).
          const r = 30, cx = 50, cy = 50;
          // p in [0,1]; map to terminator x-offset.
          // Waxing: 0..0.5 → shadow on the LEFT shrinking
          // Waning: 0.5..1 → shadow on the RIGHT growing
          const waxing = phase < 0.5;
          // ratio: 1 at new, 0 at full
          const k = waxing ? 1 - (phase / 0.5) : (phase - 0.5) / 0.5;
          // ellipse rx
          const rx = r * k;
          // shadow always covers a half-disc; the terminator is an ellipse arc on the *lit* side
          // For waxing: lit on the right, so the shadow is the left half + ellipse curving right.
          // sweep flags chosen so the ellipse "bulges" toward the lit side or away based on k sign.
          // When k≈0 (full), rx≈0 → no shadow.
          // When k≈1 (new), rx≈r → ellipse matches outer circle → entire disc shaded.
          // Use sweep so the arc curves correctly.
          let d;
          if (waxing) {
            // shadow on LEFT half. Outer: from top (50,20) down via left to bottom (50,80).
            // Inner ellipse arc: from bottom back up to top, bulging right (into lit) when k<0.5,
            // bulging left when k>=0.5 (shadow covers more than half).
            // Use sweep-flag = (k>=0.5 ? 0 : 1) for inner arc (visual choice).
            const innerSweep = (phase < 0.25) ? 1 : 0;
            d = `M ${cx} ${cy - r} A ${r} ${r} 0 0 0 ${cx} ${cy + r} A ${rx} ${r} 0 0 ${innerSweep} ${cx} ${cy - r} Z`;
          } else {
            // shadow on RIGHT half
            const innerSweep = (phase > 0.75) ? 0 : 1;
            d = `M ${cx} ${cy - r} A ${r} ${r} 0 0 1 ${cx} ${cy + r} A ${rx} ${r} 0 0 ${innerSweep} ${cx} ${cy - r} Z`;
          }
          return <path d={d} fill="#000" stroke="none" />;
        })()}
        {/* couple of stars */}
        <circle cx="14" cy="22" r="1.5" fill="#000" stroke="none" />
        <circle cx="86" cy="18" r="1.5" fill="#000" stroke="none" />
        <circle cx="20" cy="78" r="1.2" fill="#000" stroke="none" />
      </svg>
    );
  }
  if (kind === 'fog') {
    return (
      <svg {...common}>
        <line x1="18" y1="34" x2="82" y2="34" />
        <line x1="24" y1="50" x2="76" y2="50" />
        <line x1="14" y1="66" x2="86" y2="66" />
        <line x1="22" y1="82" x2="78" y2="82" />
      </svg>
    );
  }
  return null;
}

// --- Time-until helper ------------------------------------------------------
function minutesUntil(nowStr, targetStr) {
  const parse = (s) => {
    const m = String(s || '').match(/^(\d{1,2}):(\d{2})/);
    if (!m) return null;
    return +m[1] * 60 + +m[2];
  };
  const a = parse(nowStr), b = parse(targetStr);
  if (a == null || b == null) return null;
  let d = b - a;
  if (d < 0) d += 24 * 60; // tomorrow
  return d;
}
function formatCountdown(mins) {
  if (mins == null) return '';
  if (mins < 60) return `עוד ${mins} דק׳`;
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  if (m === 0) return `עוד ${h} שעות`;
  return `עוד ${h}:${String(m).padStart(2, '0')}`;
}

// --- Card primitive ---------------------------------------------------------
function Card({ children, style }) {
  return (
    <div
      style={{
        border: '2px solid #000',
        borderRadius: 18,
        background: '#fff',
        padding: '14px 18px',
        display: 'flex',
        flexDirection: 'column',
        ...style,
      }}
    >
      {children}
    </div>
  );
}

// --- Card: Weather ----------------------------------------------------------
function WeatherCard({ data }) {
  return (
    <Card style={{ flex: '1 1 0', gap: 4, padding: '12px 16px' }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        fontSize: 12,
        fontWeight: 500,
        letterSpacing: 1,
      }}>
        <span>{data.city}</span>
      </div>

      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 6,
        marginTop: 2,
      }}>
        <WeatherGlyph
          kind={data.weather_kind || 'sun'}
          size={84}
          phase={data.weather_kind === 'night' ? moonPhaseFromDate(data.gregorian_date) : undefined}
        />
        <div style={{
          display: 'flex',
          alignItems: 'baseline',
          gap: 2,
        }}>
          <span style={{ fontSize: 60, fontWeight: 600, lineHeight: 0.9, letterSpacing: -2 }}>
            {data.temp_max}
          </span>
          <span style={{ fontSize: 26, fontWeight: 500, lineHeight: 1 }}>°</span>
        </div>
      </div>

      <div style={{
        display: 'flex',
        gap: 16,
        fontSize: 13,
        fontWeight: 500,
        alignItems: 'center',
      }}>
        <span style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
          <MIcon name="dark_mode" size={15} />
          {data.temp_min}°
        </span>
        <span style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
          <MIcon name="water_drop" size={15} />
          {data.rain_chance}%
        </span>
      </div>

      {data._advice && (
        <div style={{
          marginTop: 'auto',
          padding: '6px 10px',
          background: '#000',
          color: '#fff',
          borderRadius: 10,
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          fontSize: 12,
          fontWeight: 500,
          lineHeight: 1.2,
        }}>
          <MIcon name={data._advice.icon} size={14} />
          <span style={{ flex: 1 }}>{data._advice.text}</span>
        </div>
      )}
    </Card>
  );
}

// --- Card: Today schedule ---------------------------------------------------
function ScheduleCard({ data }) {
  const items = [
    ...(data.all_day_events || []).slice(0, 1).map(t => ({ time: '·', title: t, allDay: true })),
    ...(data.timed_events || []).filter(e => !e.is_tomorrow).slice(0, 2),
  ].slice(0, 3);

  // compute countdown to next non-allDay event after `data.time`
  const nextTimed = (data.timed_events || [])
    .filter(e => !e.is_tomorrow && !e.allDay)
    .map(e => ({ ...e, mins: minutesUntil(data.time, e.time) }))
    .filter(e => e.mins != null && e.mins > 0)
    .sort((a, b) => a.mins - b.mins)[0];
  const countdown = nextTimed ? formatCountdown(nextTimed.mins) : null;

  return (
    <Card style={{ flex: '1.4 1 0', gap: 8 }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        fontSize: 13,
        fontWeight: 500,
        letterSpacing: 1,
      }}>
        <span>היום</span>
        {countdown ? (
          <span style={{
            background: '#000',
            color: '#fff',
            padding: '2px 8px',
            borderRadius: 8,
            fontSize: 11,
            fontWeight: 600,
            letterSpacing: 0,
          }}>
            {countdown}
          </span>
        ) : (
          <MIcon name="event" size={18} />
        )}
      </div>

      {items.length === 0 && (
        <div style={{
          flex: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 16,
          fontWeight: 400,
          color: '#000',
          opacity: 0.6,
        }}>
          אין אירועים
        </div>
      )}

      <div style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
        marginTop: 2,
      }}>
        {items.map((ev, i) => (
          <div key={i} style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
          }}>
            <span style={{
              fontSize: 18,
              fontWeight: 600,
              fontVariantNumeric: 'tabular-nums',
              minWidth: 56,
              textAlign: 'right',
              direction: 'ltr',
            }}>
              {ev.allDay ? '·' : ev.time}
            </span>
            <span style={{
              fontSize: 16,
              fontWeight: 400,
              flex: 1,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}>
              {ev.title}
            </span>
          </div>
        ))}
      </div>
    </Card>
  );
}

// --- Hebrew omer phrase generator -------------------------------------------
// Generates "הַיּוֹם עֶשְׂרִים וְאַרְבָּעָה יוֹם שֶׁהֵם שְׁלוֹשָׁה שָׁבוּעוֹת
//             וּשְׁלוֹשָׁה יָמִים בָּעֹמֶר"
const OMER_NUMBERS = {
  // 1..10 masculine, with niqqud
  1:  'אֶחָד',     2: 'שְׁנֵי',      3: 'שְׁלוֹשָׁה',
  4:  'אַרְבָּעָה', 5: 'חֲמִשָּׁה',   6: 'שִׁשָּׁה',
  7:  'שִׁבְעָה',   8: 'שְׁמוֹנָה',   9: 'תִּשְׁעָה',
  10: 'עֲשָׂרָה',
  20: 'עֶשְׂרִים', 30: 'שְׁלוֹשִׁים', 40: 'אַרְבָּעִים',
};
const DAY_WORD_SINGLE = 'יוֹם';
const DAY_WORD_PLURAL = 'יָמִים';
const WEEK_WORD_SINGLE = 'שָׁבוּעַ';
const WEEK_WORD_PAIR   = 'שָׁבוּעוֹת';   // 2
const WEEK_WORD_PLURAL = 'שָׁבוּעוֹת';

function hebrewNumberWord(n, withVav = false) {
  if (n <= 10) {
    const w = OMER_NUMBERS[n];
    return withVav ? 'וּ' + w.replace(/^./, c => c) : w;
  }
  // 11..19
  if (n < 20) {
    const ones = OMER_NUMBERS[n - 10];
    return ones + ' עָשָׂר';
  }
  // 20, 30, 40
  if (n % 10 === 0) {
    return OMER_NUMBERS[n];
  }
  // X1..X9: ones + ו + tens
  const tens = OMER_NUMBERS[Math.floor(n / 10) * 10];
  const ones = OMER_NUMBERS[n % 10];
  return ones + ' וְ' + tens;
}

const TEMPLE_WISH = 'הָרַחֲמָן הוּא יַחֲזִיר לָנוּ עֲבוֹדַת בֵּית הַמִּקְדָּשׁ לִמְקוֹמָהּ בִּמְהֵרָה בְיָמֵינוּ, אָמֵן.';

function buildOmerPhrase(day) {
  if (day < 1 || day > 49) return { main: '', wish: '' };
  const weeks = Math.floor(day / 7);
  const remDays = day % 7;

  // day count word
  let dayPart;
  if (day === 1) {
    dayPart = 'הַיּוֹם יוֹם אֶחָד';
  } else if (day === 2) {
    dayPart = 'הַיּוֹם שְׁנֵי יָמִים';
  } else {
    dayPart = `הַיּוֹם ${hebrewNumberWord(day)} ${DAY_WORD_PLURAL}`;
  }

  if (weeks === 0) return { main: `${dayPart} לָעֹמֶר.`, wish: TEMPLE_WISH };

  // weeks part
  let weeksPart;
  if (weeks === 1) {
    weeksPart = `שֶׁהֵם שָׁבוּעַ אֶחָד`;
  } else if (weeks === 2) {
    weeksPart = `שֶׁהֵם שְׁנֵי שָׁבוּעוֹת`;
  } else {
    weeksPart = `שֶׁהֵם ${OMER_NUMBERS[weeks]} ${WEEK_WORD_PLURAL}`;
  }

  if (remDays === 0) {
    return { main: `${dayPart}, ${weeksPart} בָּעֹמֶר.`, wish: TEMPLE_WISH };
  }

  // days remainder, joined with ו
  let remPart;
  if (remDays === 1) {
    remPart = 'וְיוֹם אֶחָד';
  } else if (remDays === 2) {
    remPart = 'וּשְׁנֵי יָמִים';
  } else {
    remPart = `וּ${OMER_NUMBERS[remDays].replace(/^./, c => c)} ${DAY_WORD_PLURAL}`;
  }

  return { main: `${dayPart}, ${weeksPart} ${remPart} בָּעֹמֶר.`, wish: TEMPLE_WISH };
}

// --- Card: Omer -------------------------------------------------------------
function OmerCard({ data }) {
  if (!data.omer) return null;
  const { day, total = 49 } = data.omer;
  const phrase = buildOmerPhrase(day);
  const weeks = Math.floor(day / 7);
  const remDays = day % 7;

  return (
    <Card style={{ flex: '1.6 1 0', gap: 6, padding: '12px 16px' }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        fontSize: 12,
        fontWeight: 500,
        letterSpacing: 1,
      }}>
        <span>ספירת העומר</span>
        <span style={{ display: 'flex', gap: 4, alignItems: 'center', fontSize: 11, opacity: 0.7 }}>
          <span style={{ direction: 'ltr', fontVariantNumeric: 'tabular-nums' }}>{day}/{total}</span>
        </span>
      </div>

      {/* full Hebrew phrase, vocalized — main + temple wish */}
      <div style={{
        fontSize: 16,
        fontWeight: 500,
        lineHeight: 1.35,
        marginTop: 2,
        fontFeatureSettings: '"liga", "calt"',
      }}>
        {phrase.main}
      </div>
      <div style={{
        fontSize: 12,
        fontWeight: 400,
        lineHeight: 1.35,
        opacity: 0.7,
        fontStyle: 'normal',
        fontFeatureSettings: '"liga", "calt"',
      }}>
        {phrase.wish}
      </div>

      {/* compact summary chip + progress bar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        marginTop: 'auto',
      }}>
        <div style={{
          display: 'flex',
          gap: 4,
          fontSize: 11,
          fontWeight: 600,
          letterSpacing: 0.5,
        }}>
          <span style={{
            background: '#000', color: '#fff',
            padding: '2px 8px', borderRadius: 8,
            display: 'inline-flex', alignItems: 'center', gap: 3,
          }}>
            <span style={{ fontVariantNumeric: 'tabular-nums' }}>{weeks}</span>
            <span style={{ opacity: 0.85 }}>שב׳</span>
          </span>
          <span style={{
            border: '1.5px solid #000',
            padding: '2px 8px', borderRadius: 8,
            display: 'inline-flex', alignItems: 'center', gap: 3,
          }}>
            <span style={{ fontVariantNumeric: 'tabular-nums' }}>{remDays}</span>
            <span style={{ opacity: 0.85 }}>ימ׳</span>
          </span>
        </div>
        <div style={{
          flex: 1,
          height: 6,
          border: '1.5px solid #000',
          borderRadius: 3,
          overflow: 'hidden',
          background: '#fff',
          position: 'relative',
        }}>
          <div style={{
            position: 'absolute',
            inset: 0,
            width: `${(day / total) * 100}%`,
            background: '#000',
          }} />
        </div>
      </div>
    </Card>
  );
}

// --- Shabbat strip (only when relevant) -------------------------------------
function ShabbatStrip({ data }) {
  if (!data.shabbat) return null;
  const { parsha, candle_lighting, sunset, havdalah, mode } = data.shabbat;
  // mode: 'incoming' (Friday before sundown) | 'active' (during) | 'outgoing' (motzash)
  return (
    <div style={{
      border: '2px solid #000',
      borderRadius: 18,
      background: '#000',
      color: '#fff',
      padding: '14px 22px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: 18,
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
      }}>
        <div style={{
          width: 36, height: 36, borderRadius: '50%',
          border: '2px solid #fff',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexShrink: 0,
        }}>
          <MIcon name="local_fire_department" size={20} />
          <style>{`
            .shabbat-icon-white .material-symbols-outlined { color: #fff !important; }
          `}</style>
        </div>
        <div>
          <div style={{ fontSize: 11, fontWeight: 500, letterSpacing: 2, opacity: 0.8 }}>
            פרשת השבוע
          </div>
          <div style={{ fontSize: 20, fontWeight: 600, lineHeight: 1.1 }}>
            {parsha}
          </div>
        </div>
      </div>

      <div style={{
        display: 'flex',
        gap: 18,
        fontSize: 13,
        fontWeight: 500,
        alignItems: 'stretch',
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
          <span style={{ fontSize: 10, letterSpacing: 2, opacity: 0.7 }}>הדלקה</span>
          <span style={{
            fontSize: 22,
            fontWeight: 600,
            fontVariantNumeric: 'tabular-nums',
            direction: 'ltr',
          }}>
            {candle_lighting}
          </span>
        </div>
        {sunset && (
          <>
            <div style={{ width: 1, background: '#fff', opacity: 0.4 }} />
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
              <span style={{ fontSize: 10, letterSpacing: 2, opacity: 0.7 }}>שקיעה</span>
              <span style={{
                fontSize: 22,
                fontWeight: 600,
                fontVariantNumeric: 'tabular-nums',
                direction: 'ltr',
              }}>
                {sunset}
              </span>
            </div>
          </>
        )}
        <div style={{ width: 1, background: '#fff', opacity: 0.4 }} />
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
          <span style={{ fontSize: 10, letterSpacing: 2, opacity: 0.7 }}>הבדלה</span>
          <span style={{
            fontSize: 22,
            fontWeight: 600,
            fontVariantNumeric: 'tabular-nums',
            direction: 'ltr',
          }}>
            {havdalah}
          </span>
        </div>
      </div>
    </div>
  );
}

// --- Greeting by hour -------------------------------------------------------
function greetingForHour(hour) {
  if (hour < 5)  return 'לילה טוב';
  if (hour < 11) return 'בוקר טוב';
  if (hour < 14) return 'צהריים טובים';
  if (hour < 18) return 'אחר צהריים טובים';
  if (hour < 22) return 'ערב טוב';
  return 'לילה טוב';
}

function parseHour(timeStr) {
  if (!timeStr) return 12;
  const m = String(timeStr).match(/^(\d{1,2})/);
  return m ? Math.min(23, Math.max(0, parseInt(m[1], 10))) : 12;
}

// --- Weather advice (dynamic) ----------------------------------------------
function weatherAdvice(data) {
  const { weather_kind, temp_max, temp_min, rain_chance } = data;
  if (rain_chance >= 60 || weather_kind === 'rainy' || weather_kind === 'stormy') {
    return { icon: 'umbrella', text: 'קחו מטרייה — צפוי גשם' };
  }
  if (rain_chance >= 30) {
    return { icon: 'umbrella', text: 'יכול לרדת גשם — קחו ז׳קט' };
  }
  if (temp_max >= 32) {
    return { icon: 'water_full', text: 'יום חם מאוד — שתו הרבה מים' };
  }
  if (temp_max >= 28) {
    return { icon: 'wb_sunny', text: 'יום חם — שתו ולבשו קל' };
  }
  if (temp_min <= 8) {
    return { icon: 'ac_unit', text: 'יום קר — קחו מעיל חם' };
  }
  if (temp_min <= 14) {
    return { icon: 'ac_unit', text: 'בבוקר קריר — קחו ז׳קט' };
  }
  if (weather_kind === 'cloudy' || weather_kind === 'cloudy_sun') {
    return { icon: 'wb_cloudy', text: 'מעונן חלקית — נעים בחוץ' };
  }
  return { icon: 'sentiment_satisfied', text: 'יום נעים — תיהנו!' };
}

// --- Header (time + date + greeting) ----------------------------------------
function Header({ data }) {
  const greeting = greetingForHour(parseHour(data.time));
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: 18,
      flex: '0 0 auto',
    }}>
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'flex-start',
        gap: 0,
      }}>
        <div style={{
          fontSize: 108,
          fontWeight: 500,
          lineHeight: 0.88,
          letterSpacing: -4,
          fontVariantNumeric: 'tabular-nums',
          direction: 'ltr',
        }}>
          {data.time}
        </div>
        <div style={{
          fontSize: 14,
          fontWeight: 500,
          opacity: 0.6,
          letterSpacing: 1,
          direction: 'ltr',
          marginTop: 4,
        }}>
          {data.gregorian_date}
        </div>
      </div>

      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'flex-end',
        gap: 0,
      }}>
        <div style={{
          fontSize: 32,
          fontWeight: 600,
          lineHeight: 1.0,
          letterSpacing: -0.5,
        }}>
          {greeting}
        </div>
        <div style={{
          fontSize: 19,
          fontWeight: 400,
          marginTop: 6,
        }}>
          {data.weekday} · {data.hebrew_date}
        </div>
      </div>
    </div>
  );
}

// --- Word-of-the-day library ------------------------------------------------
// Rotates daily — Hebrew vocabulary aimed at family/kids, with definitions.
const WORDS_OF_DAY = [
  { word: 'אַלְגוֹרִיתְם',   meaning: 'סדרת פעולות לפתרון בעיה',          tag: 'מדע' },
  { word: 'נוֹסְטַלְגְיָה',  meaning: 'געגוע לעבר',                        tag: 'רגש' },
  { word: 'סִימְבְּיוֹזָה', meaning: 'חיים משותפים של שני מינים',          tag: 'טבע' },
  { word: 'אֶמְפַּתְיָה',    meaning: 'יכולת להבין רגשות של אחר',          tag: 'רגש' },
  { word: 'פָּרָדוֹקְס',    meaning: 'אמירה שסותרת את עצמה',               tag: 'הגיון' },
  { word: 'קָתַרְזִיס',     meaning: 'טיהור רגשי דרך אמנות',               tag: 'אמנות' },
  { word: 'אֶפֶמֶרִי',      meaning: 'דבר חולף, קצר ימים',                  tag: 'שפה' },
  { word: 'סֶרֶנְדִיפִּיטִי', meaning: 'גילוי מקרי של דבר טוב',             tag: 'חיים' },
  { word: 'אַנְתְרוֹפּוֹמוֹרְפִי', meaning: 'הענקת תכונות אנוש לחיה או חפץ', tag: 'שפה' },
  { word: 'דִּיכוֹטוֹמְיָה', meaning: 'חלוקה לשני חלקים מנוגדים',           tag: 'הגיון' },
  { word: 'אוֹקְסִימוֹרוֹן', meaning: 'צירוף מילים סותרות, כמו ״שקט רועם״',  tag: 'שפה' },
  { word: 'מֶטָמוֹרְפוֹזָה', meaning: 'שינוי צורה — למשל זחל לפרפר',         tag: 'טבע' },
];
function wordForDate(dateStr) {
  if (!dateStr) return WORDS_OF_DAY[0];
  // Use only date (not hour) so it's stable across the day.
  const seed = [...dateStr].reduce((a, c) => a + c.charCodeAt(0), 0);
  return WORDS_OF_DAY[seed % WORDS_OF_DAY.length];
}

// --- Quote / word-of-day combined strip ------------------------------------
function QuoteStrip({ data }) {
  const q = data.quote;
  const w = wordForDate(data.gregorian_date);
  if (!q && !w) return null;
  return (
    <div style={{
      display: 'flex',
      gap: 10,
      alignItems: 'stretch',
      flex: '0 0 auto',
    }}>
      {/* Word of the day — left side, compact */}
      {w && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          padding: '10px 16px',
          border: '2px solid #000',
          borderRadius: 14,
          background: '#fff',
          flex: '0 0 auto',
          maxWidth: 320,
        }}>
          <div style={{
            background: '#000', color: '#fff',
            padding: '4px 10px',
            borderRadius: 10,
            fontSize: 10,
            fontWeight: 600,
            letterSpacing: 2,
            flexShrink: 0,
          }}>
            מילה ביום
          </div>
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 0,
            minWidth: 0,
            overflow: 'hidden',
          }}>
            <span style={{
              fontSize: 17,
              fontWeight: 600,
              lineHeight: 1.1,
              fontFeatureSettings: '"liga", "calt"',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}>
              {w.word}
            </span>
            <span style={{
              fontSize: 12,
              fontWeight: 400,
              opacity: 0.7,
              lineHeight: 1.2,
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}>
              {w.meaning}
            </span>
          </div>
        </div>
      )}

      {/* Quote — right side, takes remaining space */}
      {q && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          padding: '10px 16px',
          border: '1.5px dashed #000',
          borderRadius: 14,
          fontSize: 13,
          fontWeight: 400,
          flex: '1 1 auto',
          minWidth: 0,
        }}>
          <MIcon name={q.icon || 'format_quote'} size={18} />
          <span style={{
            flex: 1,
            lineHeight: 1.3,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}>
            {q.text}
          </span>
          {q.attribution && (
            <span style={{ fontSize: 11, opacity: 0.6, fontStyle: 'italic', flexShrink: 0 }}>
              — {q.attribution}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

// --- Night mode (00:00–05:00): minimal screen -----------------------------
function NightScreen({ data }) {
  const phase = moonPhaseFromDate(data.gregorian_date);
  // upcoming: prefer first tomorrow event, else first untimed event of today
  const next = (data.timed_events || []).find(e => e.is_tomorrow)
            || (data.timed_events || [])[0];
  return (
    <div
      dir="rtl"
      style={{
        width: SCREEN_W,
        height: SCREEN_H,
        background: '#000',
        color: '#fff',
        fontFamily: '"Rubik", system-ui, sans-serif',
        padding: '32px 40px',
        display: 'flex',
        flexDirection: 'column',
        boxSizing: 'border-box',
        overflow: 'hidden',
      }}
    >
      {/* top: small label + tiny moon */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 12,
      }}>
        <span style={{ fontSize: 13, letterSpacing: 3, opacity: 0.55 }}>
          לילה טוב
        </span>
        <span style={{ fontSize: 13, letterSpacing: 1, opacity: 0.55, direction: 'ltr' }}>
          {data.gregorian_date}
        </span>
      </div>

      {/* center: huge clock */}
      <div style={{
        flex: 1,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 36,
      }}>
        {/* moon, inverted (white on black) */}
        <div style={{ filter: 'invert(1)' }}>
          <WeatherGlyph kind="night" size={120} phase={phase} />
        </div>
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 0,
        }}>
          <div style={{
            fontSize: 168,
            fontWeight: 300,
            lineHeight: 0.88,
            letterSpacing: -6,
            fontVariantNumeric: 'tabular-nums',
            direction: 'ltr',
          }}>
            {data.time}
          </div>
          <div style={{
            fontSize: 18,
            fontWeight: 400,
            opacity: 0.7,
            marginTop: 8,
          }}>
            {data.weekday} · {data.hebrew_date}
          </div>
        </div>
      </div>

      {/* bottom: tomorrow's first event */}
      {next ? (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          padding: '12px 16px',
          border: '1.5px solid rgba(255,255,255,0.4)',
          borderRadius: 14,
          fontSize: 15,
          fontWeight: 400,
        }}>
          <MIcon name="wb_twilight" size={20} />
          <span style={{ opacity: 0.6, fontSize: 12, letterSpacing: 2 }}>
            {next.is_tomorrow ? 'מחר' : 'בהמשך'}
          </span>
          <span style={{
            fontSize: 18,
            fontWeight: 600,
            fontVariantNumeric: 'tabular-nums',
            direction: 'ltr',
          }}>
            {next.time}
          </span>
          <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {next.title}
          </span>
        </div>
      ) : (
        <div style={{
          textAlign: 'center',
          fontSize: 14,
          opacity: 0.45,
          letterSpacing: 2,
        }}>
          אין אירועים מתוכננים
        </div>
      )}
    </div>
  );
}

// --- The Screen ------------------------------------------------------------
function Screen({ data }) {
  // Night mode: 00:00–05:00 → minimal screen
  const hour = parseHour(data.time);
  if (data.night_mode || (hour >= 0 && hour < 5)) {
    return <NightScreen data={data} />;
  }
  const showShabbat = !!data.shabbat;
  const advice = weatherAdvice(data);
  // pass advice down through data
  const weatherData = { ...data, _advice: advice };

  return (
    <div
      dir="rtl"
      style={{
        width: SCREEN_W,
        height: SCREEN_H,
        background: '#fff',
        color: '#000',
        fontFamily: '"Rubik", system-ui, sans-serif',
        padding: '18px 24px',
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
        boxSizing: 'border-box',
        overflow: 'hidden',
      }}
    >
      <Header data={data} />

      <div style={{
        display: 'flex',
        gap: 10,
        flex: '1 1 auto',
        minHeight: 0,
      }}>
        <WeatherCard data={weatherData} />
        <ScheduleCard data={data} />
        {data.omer && <OmerCard data={data} />}
      </div>

      {showShabbat ? <ShabbatStrip data={data} /> : <QuoteStrip data={data} />}
    </div>
  );
}

window.Screen = Screen;
