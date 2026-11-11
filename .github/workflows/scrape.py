import csv, os, re
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
from bs4 import BeautifulSoup

URL = "https://krew.info/zapasy/"
CSV_FILE = "data.csv"
FIELDS = ["czas", "centrum", "typ", "grupa", "poziom", "procent", "wartosc"]
LEVELS = {"critical": 10, "low": 30, "medium": 50, "sufficient": 75, "high": 100}
ALT_RE = re.compile(r"^(Płytki krwi )?(0|A|B|AB)([+-]):")

def parse():
    html = requests.get(URL, timeout=30,
                        headers={"User-Agent": "historia-zapasow-krwi (prywatny projekt)"}).text
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for img in soup.find_all("img", alt=True):
        m = ALT_RE.match(img["alt"].strip())
        if not m:
            continue
        h2 = img.find_previous("h2")
        if not h2:
            continue
        src = img.get("src", "")
        poziom, procent = "", ""
        pm = re.search(r"[?&]p=(\d+)", src)
        if pm:
            procent = pm.group(1)
        else:
            lm = re.search(r"/(\w+)\.svg", src)
            poziom = lm.group(1) if lm else "unknown"
        wartosc = procent if procent else LEVELS.get(poziom, "")
        rows.append({
            "centrum": h2.get_text(strip=True),
            "typ": "plytki" if m.group(1) else "krew",
            "grupa": m.group(2) + m.group(3),
            "poziom": poziom, "procent": procent, "wartosc": wartosc,
        })
    return rows

def last_values():
    last = {}
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                last[(r["centrum"], r["typ"], r["grupa"])] = (r["poziom"], r["procent"])
    return last

def main():
    rows = parse()
    if len(rows) < 100:  # zabezpieczenie: strona zmieniła układ / nie wczytała się
        raise SystemExit(f"Podejrzanie mało odczytów: {len(rows)}")
    last = last_values()
    now = datetime.now(ZoneInfo("Europe/Warsaw")).isoformat(timespec="minutes")
    new = [dict(r, czas=now) for r in rows
           if last.get((r["centrum"], r["typ"], r["grupa"])) != (r["poziom"], str(r["procent"]))]
    exists = os.path.exists(CSV_FILE)
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if not exists:
            w.writeheader()
        w.writerows(new)
    print(f"Odczytano {len(rows)}, zapisano zmian: {len(new)}")

if __name__ == "__main__":
    main()
