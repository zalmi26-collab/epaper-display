# מסך אי-פייפר משפחתי

מסך אי-פייפר 7.5" מונוכרומי (800×480) שמציג שעון מדויק לדקה, תאריך עברי+לועזי, מזג אוויר בית שמש, אירועים מיומן Google, וזמני שבת/חג. מבוסס XIAO ESP32-C3 על סוללה, צריכת חשמל זניחה, עלות שוטפת אפסית.

## ארכיטקטורה

הפרויקט מורכב משני רכיבים נפרדים:

- **שרת תוכן (Python)** רץ ב-GitHub Actions כל שעה. שולף נתונים מ-Open-Meteo, Hebcal ו-Google Calendar, מרכיב BMP מונוכרומי 800×480, ושומר אותו ב-branch `gh-pages` נגיש ב-HTTPS.
- **פירמוואר ESP32 (Arduino)** מתעורר מ-deep sleep כל דקה לציור שעון מקומי, וכל שעה להורדת תמונה עדכנית מהשרת.

```
┌──────────────────────────┐         ┌─────────────────────────┐
│  GitHub Actions (cron)   │         │   ESP32-C3 (סוללה)      │
│  cron: 0 * * * *         │         │                         │
│  fetch APIs ──┐          │         │  כל דקה: שעון בלבד      │
│  builder → JSON model    │  HTTPS  │  כל שעה: full refresh   │
│  Pillow → BMP            │ ◄──────►│   ↓                     │
│  push gh-pages branch    │         │  GxEPD2 → e-paper       │
│   ↓                      │         │  שעון מצויר מעל         │
│  USER.github.io/.../bmp  │         │  deep sleep             │
└──────────────────────────┘         └─────────────────────────┘
```

המסך מחלק את התמונה ל-2 שכבות: השרת מצייר הכל **חוץ** מאזור 280×120 בפינה הימנית-עליונה, וה-ESP32 מצייר שעון באותו אזור ב-partial refresh חסכוני בכל דקה.

## תכונות

- שעון 24 שעות מתעדכן בכל דקה ללא חיבור רשת (זמן פנימי + סנכרון NTP שעתי)
- תאריך עברי מלא: "כ"ז ניסן תשפ״ו" (כולל שנה)
- תאריך לועזי DD.MM.YYYY
- מזג אוויר בית שמש: טמפרטורה מקס/מין, סיכוי גשם, זריחה ושקיעה
- קוביית שבת/חג מיום חמישי 06:00 עד יציאת השבת/החג (פרשה / שם חג, נרות, שקיעה, הבדלה)
- עומר עם ניקוד מלא בתקופת הספירה (ט"ז ניסן עד ה' סיוון)
- אירועי יומן Google: היום + מחר, רק עתידיים, עם תיוג "(מחר)" לאירועים בעוד יום
- מצב לילה (23:00-05:00): מסך "לילה טוב" עם ירח וכוכבים, deep sleep ארוך של 6 שעות
- אינדיקטור סוללה (4 רמות) ואייקון שגיאה כש-3 הורדות אחרונות נכשלו

## דרישות חומרה

| רכיב | פרטים |
|---|---|
| מיקרו-בקר | XIAO ESP32-C3 (Seeed Studio) |
| מסך | Waveshare 7.5" 800×480 V2 (driver UC8179) |
| סוללה | LiPo 3.7V, 1000-2000 mAh, מחובר דרך מחלק מתח 1:2 ל-A0 |
| חיווט SPI | SCK=D8, MOSI=D10, CS=D1, DC=D2, RST=D3, BUSY=D4 |
| חיווט סוללה | VBAT דרך 100kΩ/100kΩ ל-D0 (A0/GPIO2) |

> אם יש לך Waveshare V3 במקום V2, ערוך את `firmware/display.cpp` והחלף את typedef של ה-driver ל-`GxEPD2_750_T7_V2`.

## דרישות תוכנה

- Python 3.11+ (לפיתוח מקומי) — GitHub Actions משתמש ב-3.11
- Arduino IDE 2.x או PlatformIO
- חבילות Arduino:
  - ESP32 boards (espressif): `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
  - GxEPD2 (Jean-Marc Zingg) ⩾ 1.5.x
  - Adafruit GFX (תלות של GxEPD2)

## הגדרה ראשונית

### 1. Google Cloud Service Account

1. גש ל-[Google Cloud Console](https://console.cloud.google.com/) וצור project חדש
2. APIs & Services → Library → הפעל "Google Calendar API"
3. IAM & Admin → Service Accounts → Create Service Account
4. בחר את ה-Service Account → Keys → Add Key → Create new key → JSON. הורד את הקובץ
5. העתק את כתובת המייל של ה-Service Account (משהו כמו `epaper@PROJECT.iam.gserviceaccount.com`)

### 2. Google Calendar

1. פתח ב-Google Calendar את היומן המשפחתי
2. ⋮ → Settings and sharing → Share with specific people → Add people
3. הדבק את כתובת ה-Service Account עם הרשאת "See all event details"
4. גלול למטה ל-"Calendar ID" והעתק אותו

### 3. ריפו GitHub

```bash
git remote add origin https://github.com/USERNAME/REPO.git
git push -u origin main
```

ב-`https://github.com/USERNAME/REPO/settings/secrets/actions`:
- `GOOGLE_SERVICE_ACCOUNT_JSON` — תוכן הקובץ JSON (paste שלם)
- `CALENDAR_ID` — ה-Calendar ID

ב-Settings → Pages: Source = Deploy from a branch, Branch = `gh-pages`, Folder = `/ (root)`. ה-URL יהיה `https://USERNAME.github.io/REPO/display.bmp`.

הפעל את ה-workflow ידנית פעם אחת מ-Actions tab → "Update display image" → "Run workflow" כדי לוודא שהוא רץ.

### 4. הגדרת הפירמוואר

1. פתח את `firmware/epaper_display.ino` ב-Arduino IDE
2. ערוך את `firmware/config.h`:
   - `WIFI_SSID` ו-`WIFI_PASSWORD`
   - `IMAGE_URL` ל-URL של ה-BMP מ-GitHub Pages
3. בחר Board: "XIAO_ESP32C3"
4. Tools → Partition Scheme: "Default 4MB with spiffs (1.2MB APP/1.5MB SPIFFS)"
5. Tools → Upload Speed: 921600
6. חבר את ה-XIAO ב-USB-C, לחץ Upload
7. פתח Serial Monitor (115200) — אמור לראות את הבוט מתחבר ל-WiFi, מסנכרן NTP, ומוריד תמונה

## פיתוח מקומי

```bash
# מ-clone ראשוני של הריפו
python3 -m venv .venv
source .venv/bin/activate
pip install -r server/requirements.txt

# הצב את service_account.json ב-secrets/
# ערוך משתנה סביבה:
export CALENDAR_ID='your-calendar@group.calendar.google.com'

# ריצה ידנית
python server/main.py
# הפלט: output/display.bmp
```

### בדיקת fetcher בודד

```bash
python server/fetchers/weather.py
python server/fetchers/hebcal.py
CALENDAR_ID='...' python server/fetchers/calendar.py
```

### בדיקות יחידה

```bash
python -m unittest discover server/tests -v
```

23 בדיקות: לוגיקת shabbat_box (8), night_mode (4), אירועים (5), graceful degradation (3), omer (1), ו-renderer snapshot (2).

לעדכון snapshots אחרי שינוי מכוון ב-renderer:

```bash
UPDATE_SNAPSHOTS=1 python -m unittest server.tests.test_renderer
```

### יצירת מחדש של פונט השעון

הפונט ב-`firmware/fonts/clock_font.h` נוצר אוטומטית מ-`assets/fonts/Heebo-Regular.ttf` בגודל 110px:

```bash
python firmware/fonts/generate_clock_font.py
```

לשינוי הפונט (לדוגמה DSEG7), ערוך את הסקריפט והרץ מחדש.

## מבנה הפרויקט

```
.
├── server/
│   ├── main.py              orchestration
│   ├── config.py            constants + env vars
│   ├── builder.py           data model logic
│   ├── renderer.py          Pillow → 1-bit BMP
│   ├── night_mode.py        static night image
│   ├── fetchers/
│   │   ├── weather.py       Open-Meteo
│   │   ├── hebcal.py        Hebcal + converter API
│   │   └── calendar.py      Google Calendar
│   └── tests/
│       ├── test_builder.py
│       ├── test_renderer.py
│       ├── fixtures/        sample data models
│       └── snapshots/       expected BMP outputs
├── firmware/
│   ├── epaper_display.ino   entry + state machine
│   ├── config.h             WiFi creds, URL, pins
│   ├── display.{cpp,h}      GxEPD2 wrapper + BMP draw
│   ├── clock.{cpp,h}        bitmap clock composition
│   ├── network.{cpp,h}      WiFi, NTP, HTTPS download
│   ├── power.{cpp,h}        battery ADC, deep sleep
│   ├── indicators.{cpp,h}   battery + error icons
│   └── fonts/
│       ├── clock_font.h        auto-generated
│       └── generate_clock_font.py
├── assets/fonts/
│   ├── Heebo-Regular.ttf
│   └── FrankRuhlLibre-Bold.ttf
├── .github/workflows/update.yml
├── secrets/                 .gitignore'd
└── output/                  .gitignore'd
```

## התאמות אישיות

### שינוי מיקום

ב-`server/config.py` ערוך:
- `LATITUDE`, `LONGITUDE` — מיקום
- `GEONAME_ID` — ה-ID של העיר ב-[geonames.org](https://www.geonames.org/) (משפיע על זמני שבת)
- `CITY_NAME_HE` — השם בעברית להצגה

### שינוי יומן

הזן Calendar ID אחר ב-GitHub Secret `CALENDAR_ID`. אפשר לעבור ליומן אישי במקום משפחתי, או להוסיף תמיכה במספר יומנים ע"י עריכת `server/fetchers/calendar.py`.

### שינוי שעות מצב לילה

ב-`server/config.py` (שרת) וב-`firmware/config.h` (ESP32) — חייבים להיות זהים:
```python
NIGHT_MODE_START_HOUR = 23
NIGHT_MODE_END_HOUR = 5
```

### שינוי תזמון רענון

ערוך את ה-cron ב-`.github/workflows/update.yml`. כיום: כל שעה עגולה (`0 * * * *`).

## פתרון תקלות

### "WiFi connect timeout" ב-Serial Monitor
- בדוק SSID/password ב-`config.h`
- ה-XIAO ESP32-C3 תומך רק ב-2.4GHz — לא 5GHz

### "HTTP 404" בהורדה
- ודא שה-GitHub Action רץ בהצלחה (לפחות פעם אחת)
- ודא ש-Pages פעיל על branch `gh-pages`
- שב-`IMAGE_URL` הנתיב נכון: `https://USER.github.io/REPO/display.bmp`

### תמונה מוצגת אבל בלי עדכון
- ה-Action עובד אבל ה-ESP32 לא מצליח להוריד — בדוק `setInsecure()` ב-`network.cpp` (תוקף אישור SSL מבוטל בכוונה)
- אייקון X בפינה הצד תחתונה ימצוץ אם 3 הורדות נכשלו ברצף

### עברית מוצגת הפוך ב-BMP
- ודא ש-`python-bidi` מותקן: `pip install python-bidi`
- אם הניקוד לא מוצג בעומר — ודא שמשתמשים ב-`Frank Ruhl Libre` ולא ב-`Heebo` (Heebo חסר את `U+05BD METEG`)

### הסוללה מתרוקנת מהר
- בדוק שאין `Serial.print` בלולאה במצב production
- ודא ש-`displayHibernate()` נקרא לפני deep sleep
- ודא שאין pull-up רעב לזרם בפינים שלא בשימוש

## רישוי

קוד הפרויקט: שימוש פרטי / משפחתי. הפונטים תחת SIL Open Font License (Heebo, Frank Ruhl Libre).

## תרומות

זה פרויקט אישי. אם זה עוזר לך — איזה כיף.
