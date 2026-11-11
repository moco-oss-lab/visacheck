"""visacheck — entry-requirement checker for multi-country trips.

Tell it where you are going (ISO country codes) and how long you plan to
stay in each place, and it reports, for a Japanese passport holder:

- whether you can enter visa-free, and for how many days,
- whether your passport is valid long enough at the date of entry,
- whether a yellow-fever certificate is required or recommended,
- anything else worth knowing before you go (e.g. an eTA/ESTA to file).

The built-in table covers the South America crossing (Peru, Bolivia,
Brazil, Argentina, Chile, ...) plus common transit and stopover countries.
Rules change — always double-check with the official embassy or IATA
Travel Centre before you travel. This tool is a planning aid, not legal
advice.

Standard library only. No dependencies to install. Python 3.9+.
"""

import argparse
import datetime as dt
import json
import sys

SUPPORTED_ORIGIN = "JP"

# visa_free_days: days a Japanese passport holder may stay without a visa
#   (None = a visa / e-visa / authorisation is required in advance).
# passport_months: passport validity required beyond the date of entry
#   (0 = valid for the stay only).
# yellow_fever: "required" | "recommended" | "no".
COUNTRIES = {
    # --- South America ---
    "PE": {"name": "Peru", "visa_free_days": 90, "passport_months": 6,
           "yellow_fever": "recommended",
           "notes": "Yellow fever vaccination recommended for the Amazon basin, "
                    "not for Lima / Cusco / Machu Picchu."},
    "BO": {"name": "Bolivia", "visa_free_days": 90, "passport_months": 6,
           "yellow_fever": "required",
           "notes": "Yellow fever certificate required when arriving from a "
                    "risk country; strongly recommended for the Amazon and "
                    "lowlands. Salar de Uyuni itself is high altitude."},
    "BR": {"name": "Brazil", "visa_free_days": 90, "passport_months": 6,
           "yellow_fever": "recommended",
           "notes": "Visa-free for Japanese passport holders since 2023. "
                    "Yellow fever vaccination recommended, including for "
                    "Iguazu Falls."},
    "AR": {"name": "Argentina", "visa_free_days": 90, "passport_months": 6,
           "yellow_fever": "no",
           "notes": "Reciprocity fee abolished. Yellow fever vaccination "
                    "recommended only for the Iguazu / Misiones area."},
    "CL": {"name": "Chile", "visa_free_days": 90, "passport_months": 6,
           "yellow_fever": "no", "notes": ""},
    "UY": {"name": "Uruguay", "visa_free_days": 90, "passport_months": 6,
           "yellow_fever": "no", "notes": ""},
    "PY": {"name": "Paraguay", "visa_free_days": 90, "passport_months": 6,
           "yellow_fever": "recommended",
           "notes": "Yellow fever vaccination recommended, especially for "
                    "travel to Iguazu Falls."},
    "CO": {"name": "Colombia", "visa_free_days": 90, "passport_months": 6,
           "yellow_fever": "recommended",
           "notes": "CheckMig form must be completed online before arrival."},
    "EC": {"name": "Ecuador", "visa_free_days": 90, "passport_months": 6,
           "yellow_fever": "recommended",
           "notes": "Yellow fever vaccination recommended for the Amazon. "
                    "Galapagos visitors also need a transit control card."},
    "VE": {"name": "Venezuela", "visa_free_days": 90, "passport_months": 6,
           "yellow_fever": "recommended",
           "notes": "Entry rules change often — check the latest advisory "
                    "before planning."},
    # --- Common transit / stopovers ---
    "US": {"name": "United States", "visa_free_days": 90, "passport_months": 0,
           "yellow_fever": "no",
           "notes": "Visa Waiver Program: apply for ESTA at least 72 hours "
                    "before travel. Passport must be valid for the stay."},
    "CA": {"name": "Canada", "visa_free_days": 180, "passport_months": 0,
           "yellow_fever": "no",
           "notes": "eTA required for air arrivals. Passport must be valid "
                    "for the stay."},
    "MX": {"name": "Mexico", "visa_free_days": 180, "passport_months": 0,
           "yellow_fever": "no",
           "notes": "Fill in the FMM tourist card on arrival."},
    # --- Europe (Schengen) ---
    "FR": {"name": "France", "visa_free_days": 90, "passport_months": 3,
           "yellow_fever": "no",
           "notes": "Schengen: 90 days in any 180-day period. Passport must "
                    "be valid 3 months beyond the planned departure."},
    "DE": {"name": "Germany", "visa_free_days": 90, "passport_months": 3,
           "yellow_fever": "no",
           "notes": "Schengen: 90 days in any 180-day period. Passport must "
                    "be valid 3 months beyond the planned departure."},
    "ES": {"name": "Spain", "visa_free_days": 90, "passport_months": 3,
           "yellow_fever": "no",
           "notes": "Schengen: 90 days in any 180-day period. Passport must "
                    "be valid 3 months beyond the planned departure."},
    "IT": {"name": "Italy", "visa_free_days": 90, "passport_months": 3,
           "yellow_fever": "no",
           "notes": "Schengen: 90 days in any 180-day period. Passport must "
                    "be valid 3 months beyond the planned departure."},
    "GB": {"name": "United Kingdom", "visa_free_days": 180, "passport_months": 0,
           "yellow_fever": "no",
           "notes": "ETA required for visa-free visitors. Passport must be "
                    "valid for the stay."},
    # --- Asia-Pacific ---
    "KR": {"name": "South Korea", "visa_free_days": 90, "passport_months": 0,
           "yellow_fever": "no",
           "notes": "K-ETA required for visa-free entry (exemptions may apply "
                    "— check before travel)."},
    "TH": {"name": "Thailand", "visa_free_days": 60, "passport_months": 6,
           "yellow_fever": "no",
           "notes": "60-day visa exemption for tourism."},
    "AU": {"name": "Australia", "visa_free_days": None, "passport_months": 6,
           "yellow_fever": "no",
           "notes": "Visa or ETA/eVisitor required in advance — no "
                    "visa-on-arrival."},
    "IN": {"name": "India", "visa_free_days": None, "passport_months": 6,
           "yellow_fever": "no",
           "notes": "e-Visa required in advance; apply at least 4 days "
                    "before travel."},
    "CN": {"name": "China", "visa_free_days": 30, "passport_months": 6,
           "yellow_fever": "no",
           "notes": "30-day visa-free entry for Japanese passport holders."},
}


def lookup(code):
    """Return the entry-requirements record for an ISO country code."""
    code = code.strip().upper()
    if code not in COUNTRIES:
        raise ValueError(
            "unknown country code: %s (run with --list to see supported codes)"
            % code
        )
    return dict(COUNTRIES[code], code=code)


def list_countries():
    """Return all supported country records, sorted by code."""
    return [lookup(code) for code in sorted(COUNTRIES)]


def _months_between(start, end):
    """Whole calendar months from start to end (negative if end < start)."""
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day < start.day:
        months -= 1
    return months


def check_destination(code, stay_days=None, entry_date=None,
                       passport_expiry=None):
    """Check one destination. Returns a dict with status and findings.

    status is "ok", "warning" or "issue".
    """
    rec = lookup(code)
    findings = []

    if rec["visa_free_days"] is None:
        findings.append(("issue", "Visa/e-visa required in advance — "
                         "apply before travel."))
    elif stay_days is not None:
        if stay_days > rec["visa_free_days"]:
            findings.append(("issue", "Planned stay of %d days exceeds the "
                             "%d-day visa-free allowance — a visa is needed."
                             % (stay_days, rec["visa_free_days"])))
        else:
            findings.append(("ok", "Visa-free for %d days (planned stay: %d)."
                             % (rec["visa_free_days"], stay_days)))
    else:
        findings.append(("ok", "Visa-free for %d days."
                         % rec["visa_free_days"]))

    if entry_date is not None and passport_expiry is not None:
        valid_months = _months_between(entry_date, passport_expiry)
        needed = rec["passport_months"]
        if valid_months < needed:
            findings.append(("issue", "Passport valid only %d month(s) at "
                             "entry, but %d month(s) required."
                             % (valid_months, needed)))
        else:
            findings.append(("ok", "Passport validity OK (%d month(s) at "
                             "entry, %d required)."
                             % (valid_months, needed)))

    if rec["yellow_fever"] == "required":
        findings.append(("warning", "Yellow fever vaccination certificate "
                         "required — get vaccinated at least 10 days before "
                         "travel."))
    elif rec["yellow_fever"] == "recommended":
        findings.append(("warning", "Yellow fever vaccination recommended."))

    status = "ok"
    for level, _ in findings:
        if level == "issue":
            status = "issue"
            break
        if level == "warning":
            status = "warning"
    return {"code": rec["code"], "name": rec["name"],
            "visa_free_days": rec["visa_free_days"],
            "passport_months": rec["passport_months"],
            "yellow_fever": rec["yellow_fever"],
            "notes": rec["notes"], "status": status,
            "findings": findings}


def check_trip(codes, stays=None, entry_date=None, passport_expiry=None):
    """Check a whole multi-country trip. `stays` maps code -> planned days."""
    stays = stays or {}
    return [check_destination(code, stays.get(code.upper()),
                              entry_date, passport_expiry)
            for code in codes]


def _parse_date(text, label):
    try:
        return dt.date.fromisoformat(text)
    except ValueError:
        raise ValueError("%s must be a date like 2027-03-01, got: %s"
                         % (label, text))


def format_report(results, json_out=False):
    """Render check results as text (default) or JSON."""
    if json_out:
        serialisable = []
        for r in results:
            item = dict(r)
            item["findings"] = [{"level": lv, "message": msg}
                                for lv, msg in r["findings"]]
            serialisable.append(item)
        return json.dumps(serialisable, indent=2, ensure_ascii=False)

    lines = []
    issues = sum(1 for r in results if r["status"] == "issue")
    warnings = sum(1 for r in results if r["status"] == "warning")
    for r in results:
        mark = {"ok": "OK", "warning": "!", "issue": "X"}[r["status"]]
        lines.append("[%s] %s (%s)" % (mark, r["name"], r["code"]))
        for level, msg in r["findings"]:
            lines.append("    - %s" % msg)
        if r["notes"]:
            lines.append("    note: %s" % r["notes"])
    lines.append("")
    lines.append("Summary: %d destination(s), %d issue(s), %d warning(s)."
                 % (len(results), issues, warnings))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="visacheck",
        description="Check entry requirements for a multi-country trip "
                    "(Japanese passport).")
    parser.add_argument("countries", nargs="*", metavar="CODE",
                        help="destination ISO country codes, e.g. PE BO BR")
    parser.add_argument("--from", dest="origin", default=SUPPORTED_ORIGIN,
                        help="origin passport country code (only JP is "
                             "supported for now)")
    parser.add_argument("--days", default=None,
                        help="planned stay per destination, comma-separated "
                             "in the same order, e.g. 12,8,10")
    parser.add_argument("--entry", default=None,
                        help="entry date (first destination), YYYY-MM-DD")
    parser.add_argument("--passport-expiry", default=None,
                        help="passport expiry date, YYYY-MM-DD")
    parser.add_argument("--list", action="store_true",
                        help="list all supported destination codes")
    parser.add_argument("--json", action="store_true",
                        help="machine-readable JSON output")
    args = parser.parse_args(argv)

    if args.origin.upper() != SUPPORTED_ORIGIN:
        print("error: only %s passports are supported for now"
              % SUPPORTED_ORIGIN, file=sys.stderr)
        return 2

    if args.list:
        for rec in list_countries():
            vf = ("visa-free %d days" % rec["visa_free_days"]
                  if rec["visa_free_days"] is not None
                  else "visa required")
            print("%s  %-14s %s" % (rec["code"], rec["name"], vf))
        return 0

    if not args.countries:
        parser.print_usage(sys.stderr)
        print("error: give at least one destination code, or use --list",
              file=sys.stderr)
        return 2

    stays = {}
    if args.days:
        try:
            values = [int(v) for v in args.days.split(",")]
        except ValueError:
            print("error: --days must be comma-separated integers",
                  file=sys.stderr)
            return 2
        if len(values) != len(args.countries):
            print("error: --days needs one value per destination (%d given, "
                  "%d expected)" % (len(values), len(args.countries)),
                  file=sys.stderr)
            return 2
        stays = {code.upper(): days
                 for code, days in zip(args.countries, values)}

    entry_date = (_parse_date(args.entry, "--entry")
                  if args.entry else None)
    passport_expiry = (_parse_date(args.passport_expiry, "--passport-expiry")
                       if args.passport_expiry else None)

    try:
        results = check_trip(args.countries, stays, entry_date,
                             passport_expiry)
    except ValueError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2

    print(format_report(results, args.json))
    return 1 if any(r["status"] == "issue" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
