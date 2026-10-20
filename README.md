# Climate-aligned asset underwriting

Two illustrative deals underwritten the way a credit or real-estate team would, built on public data:

- **Multifamily acquisition with a decarbonization retrofit.** A 150-unit mid-rise in Washington, DC,
  bought at $47.0m, with the option to replace gas boilers with heat pumps and add rooftop solar to
  meet the District's Building Energy Performance Standards (BEPS).
- **Solar + storage project financing.** 200 MWac of tracking solar and a 100 MW / 400 MWh battery
  in West Texas (ERCOT), financed with a senior term loan sculpted to P50 and P90 cash flow.

Each deal has an Excel model with live formulas, a Python engine that computes the same numbers, a
memo written from the model's outputs, and a monitoring dashboard on top. Neither deal is real: the
assets are composites, and every input is labelled with where it came from.

> **Related public tool: [open-bps](https://github.com/Skippy-8/open-bps).** The property deal here tests a
> single building against DC's Building Energy Performance Standards. open-bps applies the same kind of
> test to every covered building in DC and Denver, using public data. It is checked against DOEE's
> published verdicts and refreshed monthly as an open dataset.

## What's here

| | Property | Solar + storage |
| --- | --- | --- |
| Excel model | `models/property_underwriting.xlsx` | `models/solar_storage_pf.xlsx` |
| Python engine | `cau/engine/property.py` | `cau/engine/solar_storage.py` |
| Memo | `memos/property_investment_memo.md` | `memos/solar_storage_credit_memo.md` |
| Inputs | `data/property_inputs.yaml` | `data/solar_storage_inputs.yaml` |

Shared pieces: stress cases in `data/stress_cases.yaml`, the source register in `data/sources.yaml`,
the stress and sensitivity runner in `cau/engine/stress.py`, and the dashboard in `dashboard/`.

## Headline results

| Property | Base case |
| --- | ---: |
| Loan (DSCR-sized, 1.25x) | $26.0m, 55.2% LTV |
| Minimum DSCR, status quo / retrofit | 1.33x / 1.35x |
| Levered IRR, status quo / retrofit | 8.2% / 7.8% |
| Site EUI, before / after retrofit | 59.6 / 37.1 kBtu/sf |
| Owner Scope 1+2 avoided | 212 tCO2e a year (64%) |

| Solar + storage | Base case |
| --- | ---: |
| Senior debt | $222.4m, 52.2% of project capex |
| Minimum DSCR, P50 / P90 | 1.35x / 1.20x |
| After-tax equity IRR | 8.1% |
| Output at which coverage falls to 1.00x | 82.1% of P50 |
| Severe case minimum DSCR | 1.08x |

The main conclusions:

- **Property.** The retrofit is compliance capital, not a return enhancement. It costs about 41 bp of
  levered IRR and does not pay back on utility savings, but it clears the BEPS target and removes up
  to $1.50m of penalty exposure.
- **Solar + storage.** The loan is well covered on resource risk, so the real credit risk is the
  contract. The PPA it sizes off is $51/MWh, 27% above the top of Berkeley Lab's 2024 range. At
  $40/MWh the same structure supports $42.0m less debt.

The memos give the full reasoning.

## How it is built

**The Python engines are the reference.**
- `cau/engine/` computes both deals in numpy, annual periods, from the YAML inputs.
- The Excel workbooks are generated from the same inputs by `cau/xlsx/` with openpyxl.
- Every input becomes a named cell on the Inputs tab, and every calculation is a formula that refers
  to those names.

**What the workbooks hold to:**
- **Live formulas, no typed numbers in calculations.** About 2,700 formulas across the two files; a
  test parses every one and allows no constant other than 0 and 1.
- **No circular references.**
  - The solar debt is sculpted in closed form:
    - service in each year is the lower of P50 cash flow / 1.35 and P90 cash flow / 1.00;
    - the loan is the present value of that schedule, capped at 70% gearing;
    - interest during construction is computed from that debt directly.
  - The property loan is the lowest of the LTV, DSCR and debt-yield tests.
- **A Checks tab in each workbook.** It covers sources equal uses, the loan within its limits, the
  debt repaid at maturity, the balance never negative, NPV at the IRR equal to zero, and similar. An
  "All checks pass" flag is shown on the Cover and Summary.
- **Scenarios.** `Case_Select` on the Inputs tab switches Base / Downside / Severe live. The Scenarios
  tab also keeps a snapshot of all three cases, the sensitivities and the break-evens.

**Engine and workbook must agree.** The test suite evaluates each workbook with the `formulas`
package and requires that:
- every named output equals the engine's value;
- every engine row exists in the workbook;
- both hold under every scenario.

The committed workbooks were recalculated in Excel before saving, so they open with values in any
viewer.

**The memos are templates.** `memos/templates/` holds the prose with placeholders, and
`python -m cau.memos` fills them from the engines. A test fails if a rendered memo drifts from its
template or contains a typed number.

**The dashboard** (`dashboard/app.py`, Streamlit) has four tabs:
- **Budget vs actual for the property.** A pre-flight data check runs first: duplicate rows, missing
  months, sign errors and unmapped GL lines. Lines with a missing month are reported as incomplete
  rather than netted.
- **Covenant tracking** for both deals, by case.
- **Stress and sensitivity,** with sliders that re-run the engine.
- **Decarbonization:** EUI against the BEPS target, emissions by scope, and capital per tonne avoided.

## Data

Every input carries one of four tags:

| Tag | Meaning | Property | Solar + storage |
| --- | --- | ---: | ---: |
| Sourced | Taken from a cited public source | 18 | 21 |
| Estimated | My judgement, anchored to a cited source | 44 | 16 |
| Illustrative | A deal term or assumption with no public benchmark | 23 | 17 |
| Definition | A unit conversion or constant | 9 | 9 |

Sources include:
- ENERGY STAR and EIA (energy use and prices);
- EPA eGRID 2022 and the EPA emission factor hub;
- HUD FY2026 Small Area Fair Market Rents and the DC Office of Tax and Revenue;
- DOEE (BEPS);
- NREL ATB 2024 and PVWatts (solar);
- Berkeley Lab's Utility-Scale Solar 2025 (PPA prices, ERCOT market value);
- NLR's battery cost study;
- FRED (Treasury and SOFR);
- the IRS (MACRS).

Each source has a URL and a retrieval date in `data/sources.yaml`. The Sources tab in each workbook
lists them.

Inputs worth knowing about before relying on the numbers:

- **In-place rents are estimates** anchored to HUD Small Area FMRs; the Census API needs a key, so
  no tract-level rents were pulled.
- **The one-year generation uncertainty (6%) is an estimate.** Public sources don't publish P50/P90
  spreads for a specific site; an independent engineer's study would replace it.
- **The $51/MWh PPA price was solved, not observed.** At the benchmark costs and today's rates it is
  the price that gives the sponsor an 8% after-tax equity return. Market prints are lower, and the
  credit memo treats that as the central risk.
- **The battery toll ($12/kW-month for 15 years) is illustrative.** ERCOT has no capacity market and
  no public toll benchmark.
- **The property actuals are synthetic.** `data/actuals/property_actuals_ytd.csv` is a seeded draw
  around the budget with four deliberate data errors for the QC step to catch.

## Running it

Python 3.11 or later. With [uv](https://docs.astral.sh/uv/):

```bash
uv venv && uv pip install -e ".[dashboard,dev]"
make test         # engines, workbook parity, stress, memos, QC, dashboard render
make dashboard    # streamlit run dashboard/app.py
```

To regenerate the outputs after changing an input:

```bash
make models       # rebuild both workbooks; recalculates in Excel if it is installed (macOS)
make memos        # re-render both memos from the engines
make actuals      # rewrite the synthetic actuals file
```

Without Excel, `make models` writes formula-only workbooks. Excel recalculates them on open, and the
tests evaluate them either way. One test is then skipped: the one that requires stored values.

## Limitations

- **Annual periods throughout.** There is no monthly construction draw schedule, no intra-year
  seasonality in the project cash flows, and the DSRA is funded at close and released at maturity
  without being drawn.
- **Property.**
  - The building is assumed to sit at the ENERGY STAR national median EUI, with end-use shares
    estimated from EIA RECS.
  - SOFR, utility rate structures and the grid emission rate are held flat.
  - The BEPS penalty is shown as exposure, not deducted from returns.
- **Solar + storage.**
  - No tax-equity partnership; the after-tax view assumes the sponsor uses losses as they arise and
    the credits are transferred at $0.92.
  - No battery augmentation or repowering after year 15.
  - Curtailment is held constant.
  - Emissions use the ERCOT average rate, not a marginal one.
- **The stress cases are judgement.** They are defined in one file so they can be argued with, but
  they are not calibrated to a loss history.
- **None of this is a rating, an offer or investment advice.**

## Layout

```
cau/            engines, workbook builders, memo renderer, actuals and QC
data/           inputs, stress cases, source register, synthetic actuals
models/         generated Excel workbooks
memos/          rendered memos and their templates
dashboard/      Streamlit app
scripts/        build_models.py
tests/          pytest suite
```
