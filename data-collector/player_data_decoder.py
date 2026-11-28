#!/usr/bin/env python3
"""
sio_decode.py - decode captured Survivor.io *responses* (.data files).

Reads response bytes you already captured and turns them into readable stats.
It does not build, sign or send requests. Request files are detected and
skipped, so tokens in them are never printed.

Usage:
    python3 sio_decode.py content_12.data                 # readable report
    python3 sio_decode.py *.data --json                   # JSON output
    python3 sio_decode.py *.data --csv roster.csv         # append roster rows

Frame layout (all confirmed on captures):
    bytes 0-1   uint16 little-endian, message counter (response = request + 1)
    bytes 2-5   uint32 little-endian, payload length
    bytes 6-    protobuf payload

Field meanings are marked CONFIRMED (matched against in-game screens) or
LIKELY / UNKNOWN. Cost tables come from the community charts you supplied.
"""
import argparse
import csv
import datetime
import json
import os
import struct
import sys

# --------------------------------------------------------------------------
# Cost tables (cumulative sums are computed from these per-level costs)
# --------------------------------------------------------------------------
# SS gear, relic cores per level
FORGE_COST = [1, 2, 3, 5, 8]                      # Eternal / Void forge, levels 1-5
CHAOS_COST = [1, 2, 3, 3, 4, 4, 6, 6, 8, 8]       # Chaos, levels 1-10
# Chaos level c needs Eternal + Void >= max(3, c)
TRANSMUTE_COST = [1, 1, 2, 2, 4, 4, 4, 6, 6, 6, 8, 8, 8]   # levels 1-13

# Tech part resonance (multiplier 1.0x -> 5.0x = 20 upgrades, shown as level 1..21)
RES_CHIPS = [1, 1, 2, 2, 3, 3, 4, 4, 5, 5] + [6] * 10
RES_RED = [0] * 10 + [1] * 10
# Tech part overload, levels 1-18
OVL_CHIPS = [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5, 5, 5, 5]
OVL_RED = [0] * 12 + [1] * 6

# Survivors, S rating
AWAKEN_COST = [1, 2, 4, 8, 15, 30, 30, 30]        # awakening (red star) levels 1-8
# Synergy: awaken cores per block of 5 levels, block upper bounds 5,10,...,80
SYNERGY_BLOCK_COST = [3, 3, 5, 5, 8, 8, 8, 8, 15, 15, 15, 15, 15, 15, 15, 15]
SYNERGY_BLOCK_TOP = [5 * (i + 1) for i in range(len(SYNERGY_BLOCK_COST))]
BASE_MAX_LEVEL = 120

# The tool shows these as estimates because the response does not contain them.
BORROWED_PASSIVES_RANGE = (3, 18)
UNIVERSAL_PASSIVES_RANGE = (0, 12)

SS_SLOTS = 6
# Names taken from your screenshots, edit or extend as you learn more IDs.
SURVIVOR_NAMES = {6027: "Elaine", 6022: "Venato", 6021: "Taloxa"}


def cum(costs, level, label, warnings):
    """Cumulative cost to reach `level`, clamped to the table."""
    if level < 0:
        level = 0
    if level > len(costs):
        warnings.append(f"{label} level {level} is beyond the cost table "
                        f"({len(costs)}); clamped")
        level = len(costs)
    return sum(costs[:level])


# --------------------------------------------------------------------------
# Protobuf wire decoding
# --------------------------------------------------------------------------
def read_varint(buf, i):
    result = shift = 0
    while True:
        b = buf[i]
        i += 1
        result |= (b & 0x7F) << shift
        shift += 7
        if b < 0x80:
            return result, i
        if shift > 70:
            raise ValueError("varint too long")


def parse_msg(buf):
    """Return a list of (field, wire_type, value). Raises ValueError on junk."""
    out, i = [], 0
    while i < len(buf):
        key, i = read_varint(buf, i)
        field, wire = key >> 3, key & 7
        if field == 0:
            raise ValueError("field number 0")
        if wire == 0:
            val, i = read_varint(buf, i)
        elif wire == 2:
            n, i = read_varint(buf, i)
            if i + n > len(buf):
                raise ValueError("length overruns buffer")
            val, i = buf[i:i + n], i + n
        elif wire == 1:
            val, i = buf[i:i + 8], i + 8
        elif wire == 5:
            val, i = buf[i:i + 4], i + 4
        else:
            raise ValueError(f"unsupported wire type {wire}")
        out.append((field, wire, val))
    return out


def get(msg, field, default=None):
    for f, _, v in msg:
        if f == field:
            return v
    return default


def get_all(msg, field):
    return [v for f, _, v in msg if f == field]


def sub(buf):
    return parse_msg(buf) if isinstance(buf, (bytes, bytearray)) else []


def text(b):
    return b.decode("utf-8", "replace") if isinstance(b, (bytes, bytearray)) else b


# --------------------------------------------------------------------------
# Frame handling and type detection
# --------------------------------------------------------------------------
def read_frame(path):
    data = open(path, "rb").read()
    if len(data) < 6:
        raise ValueError("file shorter than the 6-byte header")
    counter = struct.unpack("<H", data[:2])[0]
    length = struct.unpack("<I", data[2:6])[0]
    warn = []
    if length != len(data) - 6:
        warn.append(f"header says {length} payload bytes but file has {len(data) - 6}")
    return counter, parse_msg(data[6:]), warn


def detect(top):
    fields = {f for f, _, _ in top}
    first = get(top, 1)
    if isinstance(first, bytes):
        try:
            inner = parse_msg(first)
            s = get(inner, 1)
            if isinstance(s, bytes) and s.startswith(b"a_"):
                return "request"
        except ValueError:
            pass
    if {24, 34, 6}.issubset(fields):
        return "profile"
    if any(f == 2 and w == 2 for f, w, _ in top):
        return "summary"
    return "unknown"


# --------------------------------------------------------------------------
# Full profile response
# --------------------------------------------------------------------------
def decode_gear(top, warnings):
    gear = []
    for raw in get_all(top, 6):
        m = sub(raw)
        code = get(m, 2, 0)
        rarity = code % 100          # LIKELY: 16 = SS, 15 = S
        gear.append({
            "item_id": get(m, 1),
            "code": code,
            "rarity": "SS" if rarity == 16 else "S" if rarity == 15 else f"?{rarity}",
            "level": get(m, 3),                 # CONFIRMED item level
            "eternal": get(m, 5, 0),            # CONFIRMED Eternal forge level
            "void": get(m, 6, 0),               # CONFIRMED Void forge level
            "chaos": get(m, 7, 0),              # CONFIRMED chaos level
            "transmute": get(m, 8, 0),          # CONFIRMED transmute level
            "f9": get(m, 9),                    # UNKNOWN (transmute-related?)
            "f10": get(m, 10),                  # UNKNOWN
        })
    return gear


def relic_and_transmute(gear, chaos_power, warnings):
    ss = [g for g in gear if g["rarity"] == "SS"]
    relic_equipped = 0
    for g in ss:
        relic_equipped += (cum(FORGE_COST, g["eternal"], "eternal", warnings)
                           + cum(FORGE_COST, g["void"], "void", warnings)
                           + cum(CHAOS_COST, g["chaos"], "chaos", warnings))
    transmute = sum(cum(TRANSMUTE_COST, g["transmute"], "transmute", warnings)
                    for g in gear)

    # Benched SS pieces: back out of Chaos Fusion Power (field 24 = total chaos
    # levels over all SS gear). Assume the cheapest build: Eternal/Void split
    # evenly to the minimum needed for each chaos level.
    benched, relic_benched = [], 0
    remaining = chaos_power - sum(g["chaos"] for g in ss)
    slots = max(0, SS_SLOTS - len(ss))
    if remaining > 0 and slots > 0:
        base, extra = divmod(remaining, slots)
        for k in range(slots):
            c = base + (1 if k < extra else 0)
            need = max(3, c)
            e, v = (need + 1) // 2, need // 2
            cost = (cum(FORGE_COST, e, "eternal", warnings)
                    + cum(FORGE_COST, v, "void", warnings)
                    + cum(CHAOS_COST, c, "chaos", warnings))
            benched.append({"chaos": c, "eternal": e, "void": v, "relic": cost})
            relic_benched += cost
    elif remaining > 0:
        warnings.append(f"{remaining} chaos levels unaccounted for but no free SS slots")
    elif remaining < 0:
        warnings.append("equipped chaos levels exceed Chaos Fusion Power")
    return {
        "relic_equipped": relic_equipped,
        "relic_benched_estimate": relic_benched,
        "relic_total": relic_equipped + relic_benched,
        "benched_pieces_assumed": benched,
        "transmute_total": transmute,
    }


def decode_reso(top, warnings):
    lvl29 = {get(sub(r), 1): get(sub(r), 2, 0) for r in get_all(top, 29)}
    lvl30 = {get(sub(r), 1): get(sub(r), 2, 0) for r in get_all(top, 30)}
    parts, chips, red = [], 0, 0
    for code in sorted(set(lvl29) | set(lvl30)):
        res = lvl29.get(code, 1)        # missing in f29 means never upgraded (level 1)
        ovl = lvl30.get(code, 0)
        rc = cum(RES_CHIPS, res - 1, "resonance", warnings)
        rr = cum(RES_RED, res - 1, "resonance", warnings)
        oc = cum(OVL_CHIPS, ovl, "overload", warnings)
        orr = cum(OVL_RED, ovl, "overload", warnings)
        parts.append({"code": code, "resonance_level": res, "overload_level": ovl,
                      "chips": rc + oc, "red": rr + orr})
        chips += rc + oc
        red += rr + orr
    return {"parts": parts, "reso_chips": chips, "red_techs": red}


def decode_survivors(top, warnings):
    block = sub(get(top, 34, b""))
    survivors = []
    for raw in get_all(block, 2):
        m = sub(raw)
        stype = get(m, 2)
        awaken = get(m, 7, 0)
        survivors.append({
            "type": stype,
            "name": SURVIVOR_NAMES.get(stype),
            "instance_id": get(m, 1),
            "level": get(m, 3),             # CONFIRMED
            "stars": get(m, 4),             # CONFIRMED (yellow stars)
            "awakening": awaken,            # CONFIRMED (red stars)
            "awaken_cores": cum(AWAKEN_COST, awaken, "awakening", warnings),
        })
    synergy = get(block, 3, 0)              # CONFIRMED ("Advancement")
    syn_cores = sum(c for c, top_lvl in zip(SYNERGY_BLOCK_COST, SYNERGY_BLOCK_TOP)
                    if synergy >= top_lvl)  # a block is paid when completed
    team = sum(s["awaken_cores"] for s in survivors)
    lo = syn_cores + team + BORROWED_PASSIVES_RANGE[0] + UNIVERSAL_PASSIVES_RANGE[0]
    hi = syn_cores + team + BORROWED_PASSIVES_RANGE[1] + UNIVERSAL_PASSIVES_RANGE[1]
    return {"survivors": survivors, "synergy_level": synergy,
            "synergy_cores": syn_cores, "team_awaken_cores": team,
            "awakening_cores_low": lo, "awakening_cores_high": hi}


def decode_profile(top):
    warnings = []
    name_msg = sub(get(top, 3, b""))
    gear = decode_gear(top, warnings)
    chaos_power = get(top, 24, 0)
    result = {
        "type": "profile",
        "player_id": get(top, 2),                      # CONFIRMED
        "name": text(get(name_msg, 1)),                # CONFIRMED
        "cosmetic_ids": [get(name_msg, 2), get(name_msg, 3)],   # LIKELY avatar/frame
        "atk": get(top, 7),                            # CONFIRMED
        "hp": get(top, 8),                             # CONFIRMED
        "clan_id": get(top, 11),                       # CONFIRMED
        "clan_name": text(get(top, 12)),               # CONFIRMED
        "clan_level": get(top, 15),                    # LIKELY (namecard badge)
        "main_survivor": get(top, 4),                  # CONFIRMED
        "chaos_fusion_power": chaos_power,             # CONFIRMED
        "gear": gear,
    }
    result.update(relic_and_transmute(gear, chaos_power, warnings))
    result["reso"] = decode_reso(top, warnings)
    result["awakening"] = decode_survivors(top, warnings)
    result["warnings"] = warnings
    return result


# --------------------------------------------------------------------------
# Short "summary" response (the 257-byte kind)
# --------------------------------------------------------------------------
def decode_summary(top):
    rows = []
    for f, w, v in top:
        if w != 2:
            continue
        try:
            m = parse_msg(v)
        except ValueError:
            continue
        pid = get(m, 1)
        if not isinstance(pid, int):
            continue
        ts = get(m, 10)
        rows.append({
            "section": f,
            "player_id": pid,
            "name": text(get(m, 2)),
            "atk": get(m, 6),
            "hp": get(m, 7),
            # LIKELY last-active / last-refreshed time (Unix seconds)
            "last_active_utc": (datetime.datetime.fromtimestamp(
                ts, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                if isinstance(ts, int) and ts > 1_000_000_000 else None),
        })
    return {"type": "summary", "players": rows}


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------
def fmt(n):
    return f"{n:,}" if isinstance(n, int) else str(n)


def report_profile(r):
    print(f"{r['name']}  (ID {r['player_id']})   clan: {r['clan_name']} "
          f"[{r['clan_id']}], clan level {r['clan_level']}")
    print(f"  ATK {fmt(r['atk'])}   HP {fmt(r['hp'])}   "
          f"Chaos Fusion Power {r['chaos_fusion_power']}")
    print("\n  Gear")
    print("    code     rar  lvl  eternal void chaos transmute")
    for g in r["gear"]:
        print(f"    {g['code']:<8} {g['rarity']:<4} {g['level']:<4} {g['eternal']:<7} "
              f"{g['void']:<4} {g['chaos']:<5} {g['transmute']}")
    print(f"\n  Relic cores     {r['relic_total']}  "
          f"(equipped {r['relic_equipped']} + benched estimate {r['relic_benched_estimate']})")
    for b in r["benched_pieces_assumed"]:
        print(f"    assumed benched SS piece: chaos {b['chaos']}, eternal {b['eternal']}, "
              f"void {b['void']} -> {b['relic']} cores")
    print(f"  Transmute cores {r['transmute_total']}")
    rs = r["reso"]
    print(f"  Reso chips      {rs['reso_chips']}   (red techs: {rs['red_techs']})")
    for p in rs["parts"]:
        print(f"    part {p['code']}: resonance {p['resonance_level']}, "
              f"overload {p['overload_level']} -> {p['chips']} chips, {p['red']} red")
    a = r["awakening"]
    print(f"  Awakening cores {a['awakening_cores_low']} - {a['awakening_cores_high']}  "
          f"(synergy {a['synergy_level']} = {a['synergy_cores']}, team = {a['team_awaken_cores']}, "
          f"plus estimated passives)")
    for s in a["survivors"]:
        label = s["name"] or s["type"]
        print(f"    {label}: Lv {s['level']}, {s['stars']} stars, awakening "
              f"{s['awakening']} -> {s['awaken_cores']} cores")
    for w in r["warnings"]:
        print(f"  ! {w}")


def report_summary(r):
    print(f"{'ID':>11}  {'name':<14} {'ATK':>12} {'HP':>12}  last active (UTC)")
    for p in r["players"]:
        print(f"{p['player_id']:>11}  {(p['name'] or '-'):<14} "
              f"{fmt(p['atk']) if p['atk'] is not None else '-':>12} "
              f"{fmt(p['hp']) if p['hp'] is not None else '-':>12}  "
              f"{p['last_active_utc'] or '-'}")


CSV_COLUMNS = ["player_id", "name", "clan_id", "clan_name", "atk", "hp",
               "chaos_fusion_power", "relic_total", "transmute_total",
               "reso_chips", "red_techs", "awakening_low", "awakening_high"]


def csv_row(r):
    return {"player_id": r["player_id"], "name": r["name"], "clan_id": r["clan_id"],
            "clan_name": r["clan_name"], "atk": r["atk"], "hp": r["hp"],
            "chaos_fusion_power": r["chaos_fusion_power"],
            "relic_total": r["relic_total"], "transmute_total": r["transmute_total"],
            "reso_chips": r["reso"]["reso_chips"], "red_techs": r["reso"]["red_techs"],
            "awakening_low": r["awakening"]["awakening_cores_low"],
            "awakening_high": r["awakening"]["awakening_cores_high"]}


def main():
    ap = argparse.ArgumentParser(description="Decode captured Survivor.io responses.")
    ap.add_argument("files", nargs="+")
    ap.add_argument("--json", action="store_true", help="print JSON instead of a report")
    ap.add_argument("--csv", metavar="FILE", help="append profile rows to a CSV roster")
    args = ap.parse_args()

    results, profiles = [], []
    for path in args.files:
        try:
            counter, top, warn = read_frame(path)
        except (OSError, ValueError, IndexError) as e:
            print(f"{path}: could not read ({e})", file=sys.stderr)
            continue
        kind = detect(top)
        if kind == "request":
            print(f"{path}: request file, skipped (contains credentials; "
                  f"decode responses only)", file=sys.stderr)
            continue
        if kind == "profile":
            r = decode_profile(top)
            profiles.append(r)
        elif kind == "summary":
            r = decode_summary(top)
        else:
            print(f"{path}: unrecognized response layout "
                  f"(top-level fields {sorted({f for f, _, _ in top})})", file=sys.stderr)
            continue
        r["file"] = os.path.basename(path)
        r["counter"] = counter
        r.setdefault("warnings", []).extend(warn)
        results.append(r)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for r in results:
            print(f"== {r['file']} ({r['type']}, counter {r['counter']:#06x})")
            (report_profile if r["type"] == "profile" else report_summary)(r)
            print()

    if args.csv and profiles:
        new = not os.path.exists(args.csv) or os.path.getsize(args.csv) == 0
        with open(args.csv, "a", newline="", encoding="utf-8-sig") as fh:
            w = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
            if new:
                w.writeheader()
            for r in profiles:
                w.writerow(csv_row(r))
        print(f"appended {len(profiles)} row(s) to {args.csv}", file=sys.stderr)


if __name__ == "__main__":
    main()