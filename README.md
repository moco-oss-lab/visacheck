# visacheck

Tiny entry-requirement checker for multi-country trips — a CLI that tells a
Japanese passport holder, for each destination on the route:

- whether entry is visa-free, and for how many days,
- whether the passport is valid long enough at the date of entry,
- whether a yellow-fever certificate is required or recommended,
- anything else worth knowing before you go (ESTA, eTA, K-ETA, CheckMig …).

The built-in table covers the South America crossing (Peru, Bolivia,
Brazil, Argentina, Chile, Uruguay, Paraguay, Colombia, Ecuador) plus
common transit and stopover countries (US, Canada, Mexico, Schengen
countries, UK, Korea, Thailand, Australia, India, China).

Rules change — always double-check with the official embassy or the IATA
Travel Centre before you travel. This tool is a planning aid, not legal
advice.

Standard library only. No dependencies to install. Python 3.9+.

## Install

```sh
git clone https://github.com/moco-oss-lab/visacheck.git
cd visacheck
python3 visacheck.py --help
```

## Usage

```sh
# South America crossing: Peru 12 days, Bolivia 8, Brazil 10, Argentina 6
python3 visacheck.py PE BO BR AR --days 12,8,10,6

# Also check passport validity at the entry date
python3 visacheck.py PE BO BR AR --days 12,8,10,6 \
    --entry 2027-03-01 --passport-expiry 2028-06-01

# Machine-readable output
python3 visacheck.py PE BO --days 12,8 --json

# List every supported destination code
python3 visacheck.py --list
```

Example output:

```
[!] Peru (PE)
    - Visa-free for 90 days (planned stay: 12).
    - Passport validity OK (15 month(s) at entry, 6 required).
    - Yellow fever vaccination recommended.
    note: Yellow fever vaccination recommended for the Amazon basin,
    not for Lima / Cusco / Machu Picchu.
[!] Bolivia (BO)
    - Visa-free for 90 days (planned stay: 8).
    - Passport validity OK (15 month(s) at entry, 6 required).
    - Yellow fever vaccination certificate required — get vaccinated
      at least 10 days before travel.
[OK] Argentina (AR)
    - Visa-free for 90 days (planned stay: 6).
    - Passport validity OK (15 month(s) at entry, 6 required).

Summary: 4 destination(s), 0 issue(s), 3 warning(s).
```

Exit code is `1` when any destination has an issue (e.g. the planned stay
exceeds the visa-free allowance, or the passport is too short-lived),
`2` for a usage error such as an unknown country code, and `0` otherwise.

## Tests

```sh
python3 -m unittest test_visacheck
```

## License

MIT — see [LICENSE](LICENSE).
```

## Data notes

Visa-free allowances are for Japanese passport holders, as generally
published for 2026. A few notable cases:

- Brazil has been visa-free for Japanese passport holders since 2023.
- The US (ESTA), Canada (eTA), UK (ETA), South Korea (K-ETA) and
  Australia (ETA/eVisitor) still need an online authorisation filed in
  advance, even though no visa is required.
- Schengen countries share one 90-days-in-any-180-day-period allowance.
