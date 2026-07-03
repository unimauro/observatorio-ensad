#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Consulta Amigable MEF -> serie histórica UE 123 ENSAD (pliego 010 MINEDU).
Drill: Año -> Nivel de Gobierno -> E: GOBIERNO NACIONAL -> Sector 10 EDUCACION
       -> Pliego 010 M. DE EDUCACION -> Unidad Ejecutora 123 (ENSAD).
Parsea PIA/PIM/Certificado/.../Devengado/Girado de la fila de la UE 123.
Fusiona en data/presupuesto-ensad.json SIN tocar 2025/2026 ni detalle.
"""
import requests, re, json, os, time, sys
from bs4 import BeautifulSoup

BASE = "https://apps5.mineco.gob.pe/transparencia/Navegador/"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
HERE = os.path.dirname(os.path.abspath(__file__))


def new_session():
    s = requests.Session()
    s.headers.update({"User-Agent": UA})
    s.get(BASE + "default.aspx", timeout=40)
    return s


def fields(soup):
    d = {}
    for inp in soup.select("input"):
        n = inp.get("name"); t = (inp.get("type") or "text").lower()
        if not n or t in ("submit", "button", "image", "reset"):
            continue
        if t in ("radio", "checkbox"):
            if inp.has_attr("checked"):
                d[n] = inp.get("value", "on")
        else:
            d[n] = inp.get("value", "")
    for sel in soup.select("select"):
        n = sel.get("name")
        if n:
            o = sel.select_one("option[selected]") or sel.select_one("option")
            d[n] = o.get("value", "") if o else ""
    return d


def rows_with_grp1(soup):
    """[(label, grp1_value)] filas seleccionables."""
    out = []
    for tr in soup.find_all("tr"):
        radio = tr.find("input", {"name": "grp1"})
        if not radio:
            continue
        lbl = None
        for td in tr.find_all("td"):
            t = td.get_text(" ", strip=True)
            if re.match(r"^[\wÑ]+:\s", t):
                lbl = t; break
        out.append((lbl, radio.get("value")))
    return out


def find_button(soup, text):
    """Devuelve (name, value) del input submit cuyo value == text (o lo contiene)."""
    for inp in soup.select("input[type=submit]"):
        v = inp.get("value", "")
        if v.strip() == text:
            return inp.get("name"), v
    for inp in soup.select("input[type=submit]"):
        v = inp.get("value", "")
        if text.lower() in v.lower():
            return inp.get("name"), v
    return None, None


def num(s):
    s = (s or "").replace(",", "").strip()
    try:
        return round(float(s), 2)
    except ValueError:
        return None


def parse_target_row(soup, code):
    """Encuentra la fila cuyo label empieza 'code' (con sufijo -NNNN opcional) y devuelve (label, nums)."""
    pat = re.compile(r"^0*%s(-\d+)?\s*:" % re.escape(code))
    for tr in soup.find_all("tr"):
        cells = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
        idx = next((i for i, c in enumerate(cells) if pat.match(c)), None)
        if idx is None:
            continue
        nums = [num(c) for c in cells[idx + 1:]
                if re.match(r"^-?[\d,]+(\.\d+)?$", c.replace(",", ""))]
        nums = [n for n in nums if n is not None]
        if len(nums) >= 6:
            return cells[idx], nums
    return None, None


def find_row_grp1(soup, code):
    """grp1 value de la fila cuyo label empieza 'code:'."""
    pat = re.compile(r"^0*%s\s*:" % re.escape(code))
    for lbl, val in rows_with_grp1(soup):
        if lbl and pat.match(lbl.strip()):
            return val
    return None


def post(s, soup, click_name, click_val, grp1_val, year):
    action = soup.find("form").get("action")
    d = fields(soup)
    d["grp1"] = grp1_val
    d[click_name] = click_val
    r = s.post(BASE + action, data=d,
               headers={"Referer": f"{BASE}Navegar.aspx?y={year}&ap=ActProy"}, timeout=60)
    return BeautifulSoup(r.text, "lxml")


def scrape_year(s, year):
    s.get(f"{BASE}default.aspx?y={year}&ap=ActProy", timeout=40)
    soup = BeautifulSoup(s.get(f"{BASE}Navegar.aspx?y={year}&ap=ActProy", timeout=40).text, "lxml")
    sel = soup.select_one("#ctl00_CPH1_DrpYear option[selected]")
    if not sel or sel.get_text(strip=True) != str(year):
        raise RuntimeError(f"año no fijado ({sel.get_text(strip=True) if sel else '?'})")
    g = soup.select_one('input[name=grp1]')
    grp1 = g.get("value") if g else None

    # 1) Nivel de Gobierno
    bn, bv = find_button(soup, "Nivel de Gobierno")
    soup = post(s, soup, bn, bv, grp1, year)
    rows = rows_with_grp1(soup)
    e = next((v for l, v in rows if l and l.strip().upper().startswith("E:")), None)
    if not e:
        raise RuntimeError("no encontré E: GOBIERNO NACIONAL")

    # 2) Sector (elige E)
    bn, bv = find_button(soup, "Sector")
    soup = post(s, soup, bn, bv, e, year)
    sec = find_row_grp1(soup, "10")
    if not sec:
        raise RuntimeError("no encontré sector 10 EDUCACION")

    # 3) Pliego (elige sector 10)
    bn, bv = find_button(soup, "Pliego")
    soup = post(s, soup, bn, bv, sec, year)
    pli = find_row_grp1(soup, "010")
    if not pli:
        raise RuntimeError("no encontré pliego 010 M. DE EDUCACION")

    # 4) Unidad Ejecutora (elige pliego 010) -> buscar fila UE 123
    bn, bv = find_button(soup, "Ejecutora")
    if not bn:
        raise RuntimeError("no encontré botón Ejecutora")
    soup = post(s, soup, bn, bv, pli, year)
    label, nums = parse_target_row(soup, "123")
    if not nums:
        # ENSAD puede no existir como UE separada antes de ~2016
        raise RuntimeError("SINUE:no existe fila UE 123 (ENSAD) este año")
    return label, nums


def build_record(year, nums):
    pia, pim, cert = nums[0], nums[1], nums[2]
    if len(nums) >= 8:
        dev, gir = nums[5], nums[6]
    elif len(nums) == 7:
        dev, gir = nums[4], nums[5]
    else:
        dev, gir = nums[-2], nums[-1]
    ejec = round(100 * dev / pim, 1) if pim else 0
    return {"year": year, "pia": pia, "pim": pim, "cert": cert,
            "dev": dev, "gir": gir, "ejec_pct": ejec}


def main():
    years = list(range(2012, 2025))  # 2012..2024
    results = {}
    skipped = {}
    s = new_session()
    for y in years:
        got = False
        for attempt in range(4):
            try:
                label, nums = scrape_year(s, y)
                rec = build_record(y, nums)
                results[y] = rec
                print(f"[{y}] {label} nums={nums}\n   -> PIA {rec['pia']/1e6:.2f}M PIM {rec['pim']/1e6:.2f}M "
                      f"Cert {rec['cert']/1e6:.2f}M Dev {rec['dev']/1e6:.2f}M Gir {rec['gir']/1e6:.2f}M "
                      f"({rec['ejec_pct']}%)", flush=True)
                got = True
                break
            except Exception as e:
                msg = repr(e)
                print(f"[{y}] intento {attempt}: {msg[:90]}", flush=True)
                if "SINUE" in msg:
                    skipped[y] = "no existe UE 123 separada"
                    got = True  # no reintentar, es esperado
                    break
                time.sleep(6)
                s = new_session()
        if not got:
            skipped[y] = "falló tras reintentos"
            print(f"[{y}] FALLÓ tras reintentos", flush=True)
        time.sleep(2)

    json.dump({str(y): r for y, r in results.items()},
              open(os.path.join(HERE, "ca_ensad_raw.json"), "w"), ensure_ascii=False)
    print("\nAños obtenidos:", sorted(results.keys()), flush=True)
    print("Años saltados:", skipped, flush=True)


if __name__ == "__main__":
    main()
