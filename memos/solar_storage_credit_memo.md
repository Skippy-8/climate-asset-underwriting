# Credit memo: senior secured term loan, 200 MWac solar and 100 MW / 400 MWh storage, West Texas (ERCOT)

Illustrative project financing built on public benchmarks; not a real project, rating or offer.
Data as of 2026-10-15. Model inputs fingerprint `358aa6d73eb6`; every figure below is generated from
`models/solar_storage_pf.xlsx` and its Python engine.

## Recommendation

Approve a $222.4m senior secured term loan (52.2% of project capex), 18-year tenor from
commercial operation, fixed at 6.96% through a swap, sculpted to 1.35x on P50 and 1.00x on P90 cash
flow. The debt is well covered: it services at 1.00x until output falls to 82.1% of P50 in every
year, roughly a one-in-721 annual outcome. The credit question is the contract, not the
resource. The loan sizes off a solar PPA at $51.00/MWh, which is 27% above the top of Berkeley
Lab's 2024 contract range; approval is conditional on that PPA being signed with an
investment-grade offtaker.

## Transaction

The project is 200 MWac (268 MWdc at a 1.34 inverter loading ratio) of single-axis tracking
solar and a 4-hour, 100 MW battery, financed at a single financial close.

| Uses |  | Sources |  |
| --- | ---: | --- | ---: |
| Solar ($1.38/Wac) | $276.0m | Senior debt | $222.4m (49.5%) |
| Battery ($334/kWh) | $133.6m | Tax-credit transfer | $113.0m (25.2%) |
| Development, owner, interconnection | $16.4m | Sponsor equity | $114.0m (25.4%) |
| Interest during construction | $7.7m |  |  |
| Financing fees | $3.3m |  |  |
| Debt service reserve (6 months) | $12.4m |  |  |
| **Total uses** | **$449.5m** | **Total sources** | **$449.5m** |

Solar capex is Berkeley Lab's 2024 ERCOT installed cost of $1.38/Wac; battery capex is NLR's
bottom-up cost of $334/kWh for a 4-hour system. Tax credits of 30% on both are assumed
transferred at $0.92 per dollar of credit; in practice these proceeds would bridge to closing rather than
arrive at it.

## Revenue and output

| | Year one |
| --- | ---: |
| Solar revenue (P50) | $27.3m |
| Battery toll | $14.4m |
| Operating costs | ($8.2m) |
| CFADS (P50) | $33.5m |

- Output. NREL ATB resource-class capacity factor of 32.9%, less ERCOT's 7.1% solar curtailment
  rate, gives a 30.6% net capacity factor and 535 GWh in year one, degrading 0.7% a
  year. P90 and P99 one-year output are 92.3% and 86.0% of P50, from an assumed 6%
  one-year uncertainty.
- Solar contract. As-generated PPA at $51.00/MWh flat for 20 years, then merchant at ERCOT's
  2024 solar market value of $24/MWh (against $29/MWh for a flat block). The PPA price
  was solved so the sponsor's after-tax equity return is 8% at benchmark capex and today's
  rates. For comparison, the 2024 national average was $29/MWh (interquartile range
  $22 to $40/MWh) and Berkeley Lab puts ERCOT's after-credit solar LCOE at $34/MWh.
- Battery contract. Tolling agreement at $12/kW-month for 15 years, matching the battery's
  15-year life; the battery is 35% of year-one revenue. ERCOT has no capacity market,
  so the toll stands in for capacity and ancillary value.

## Debt sizing

Debt service in each year is the lower of P50 CFADS / 1.35x and P90 CFADS / 1.00x. The loan is the
present value of that schedule at the coupon, capped at 70% gearing; the cap does not bind.
Interest is charged on the opening balance and principal is service less interest, so the balance
repays exactly at maturity with no circular calculation.

|  | Value |
| --- | ---: |
| Coupon (fixed, swapped) | 6.96% |
| Tenor | 18 years |
| Gearing | 52.2% |
| Minimum DSCR, P50 (target 1.35x) | 1.35x |
| Minimum DSCR, P90 (target 1.00x) | 1.20x |
| LLCR / PLCR | 1.35x / 1.46x |
| Debt service, year 1 | $24.8m |

P50 coverage is a flat 1.35x by construction, and the LLCR equals it. Debt service steps down
from $20.4m to $12.9m after year 15, when the toll and the battery's assumed life
end; the sculpting absorbs the loss of battery revenue rather than leaving a coverage cliff. Maturity
falls inside the PPA, so no merchant revenue supports the debt.

## Stress cases

Generation and price stresses run against the debt schedule fixed at close; the rate shock and the
capex overrun act at close (the shock re-sizes the debt; the overrun is funded with equity).

| Assumption | Base | Downside | Severe |
| --- | ---: | ---: | ---: |
| Output, every year | P50 | P90 (one-year) | P99 (one-year) |
| Merchant tail price | base | -25% | -50% |
| EPC overrun (equity-funded) | none | +10% | +20% |
| Rate at pricing | base | +100 bp | +200 bp |

|  | Base | Downside | Severe |
| --- | ---: | ---: | ---: |
| Senior debt | $222.4m | $208.4m | $195.7m |
| Minimum DSCR (operating case) | 1.35x | 1.20x | 1.08x |
| Average DSCR (operating case) | 1.35x | 1.25x | 1.17x |
| LLCR (operating case) | 1.35x | 1.26x | 1.19x |
| Years in distribution lock-up | 0 | 0 | 3 |
| Years below the default trigger | 0 | 0 | 0 |
| Sponsor equity | $114.0m | $159.6m | $203.9m |
| Equity IRR, pre-tax | 6.3% | 0.4% | -4.9% |
| Equity IRR, after tax | 8.1% | 1.1% | -5.0% |
| Project IRR, pre-tax | 7.4% | 4.9% | 2.6% |

At one-year P90 in every year, minimum coverage is 1.20x; at P99 it is 1.08x, with
3 years in distribution lock-up and 0 below the default trigger. Equity
absorbs the stress: after-tax equity IRR falls to 1.1% in the Downside and -5.0% in the
Severe case. The largest single levers, one at a time from the base case:

On minimum coverage:

- P99 output (1-yr): 1.08x (-0.27x from base)
- P90 output (1-yr): 1.20x (-0.15x from base)

On after-tax equity IRR:

- No solar tax credit: 2.4% (-576 bp from base)
- EPC overrun +20%: 3.5% (-462 bp from base)
- P99 output (1-yr): 3.5% (-460 bp from base)
- Battery toll -25%: 5.2% (-296 bp from base)

## Key credit risks

- Contract price. The PPA is priced above recent market prints. At $40.00/MWh, the top of the
  2024 range, the same sculpting supports $180.4m of debt ($42.0m less), equity
  rises to $151.7m and the after-tax equity IRR falls to 3.3%. The loan should not be sized
  on an unsigned price.
- Resource and curtailment. ERCOT's solar curtailment rate was higher than CAISO's and SPP's in
  2024 and is concentrated in West Texas; it is held constant here. P99 output still covers debt service above the 1.05x default trigger.
- Battery. The toll's 15 years of revenue rest on one counterparty and one asset with a shorter life
  than the solar. Debt service is sculpted down when the toll ends, but toll default before then is
  not mitigated by the structure.
- Tax credits. Equity relies on transferring the credits; federal rules for solar credits changed
  recently, and the model shows no solar credit as a sensitivity. The credits sit with equity, not debt.
- Construction and capex. Overruns are equity-funded in the model; the term sheet needs a completion
  guarantee or contingent equity to make that true.
- Interest rate. A higher rate at pricing reduces the loan ($195.7m in the Severe case) but does
  not change coverage, because the schedule is fixed to cash flow; the coupon must be swapped at close.

## Structural mitigants

- Sculpted amortisation at 1.35x P50 and 1.00x P90, maturing inside the PPA.
- Debt service reserve of 6 months, funded at close ($12.4m).
- Distribution lock-up at 1.15x and event of default at 1.05x (proposed; the model counts the
  years each would trip). A cash sweep is not modelled; with sculpted amortisation the structure relies
  on the lock-up.
- Gearing cap of 70% of project capex as a second sizing limit.

## Conditions precedent

- Executed PPA at or above $51.00/MWh with an investment-grade offtaker, and an executed battery toll.
- Independent engineer's energy yield and curtailment study supporting the P50 and P90 used here.
- Executed tax-credit transfer agreement, or a bridge facility sized to the credit.
- Interest rate swap at close; fixed-price EPC with completion support.

## Data and limitations

Annual periods; pre-tax CFADS for debt and an after-tax equity view that assumes the sponsor uses tax
losses as they arise (no tax-equity partnership); no battery repowering after year 15; the
merchant tail is floored at zero (the plant is idled rather than run at a loss); grid emissions use
the eGRID ERCOT average rate of 774.3 lb CO2e per MWh, not a marginal rate. On that basis the
project displaces 188,071 tCO2e in year one and 5.11 million over its life ($83 of project
capex per tonne). Sourced inputs:

- NREL/NLR Annual Technology Baseline 2024b, Utility-Scale Battery Storage: fixed O&M 2.5% of capex per year (includes augmentation), 85% round-trip efficiency, 15-year life (https://atb.nlr.gov/electricity/2024b/utility-scale_battery_storage)
- NREL/NLR Annual Technology Baseline 2024b, Utility-Scale PV: CAPEX $1,430/kWac (2022), fixed O&M $22/kWac-yr (2023), ILR 1.34, degradation 0.7%/yr, 30-yr life, class 1-5 capacity factors 34.0%-28.3% (https://atb.nlr.gov/electricity/2024b/utility-scale_pv)
- EPA eGRID2022 Summary Tables: total output emission rates, RFC East (RFCE) 660.3 lb CO2e/MWh; ERCOT All (ERCT) 774.3 lb CO2e/MWh; U.S. 827.5 lb CO2e/MWh (https://www.epa.gov/system/files/documents/2024-01/egrid2022_summary_tables.pdf)
- FRED DGS10, 10-year Treasury constant maturity, 5.21% on 2026-10-13 (fetched with quantlab.data.sources.extra.fred_series) (https://fred.stlouisfed.org/series/DGS10)
- Internal Revenue Code: 21% corporate rate (IRC 11(b)); depreciable basis reduced by 50% of an investment credit (IRC 50(c)(3)) (https://www.law.cornell.edu/uscode/text/26/11)
- IRS Publication 946, Table A-1: 5-year property, half-year convention: 20.00%, 32.00%, 19.20%, 11.52%, 11.52%, 5.76% (https://www.irs.gov/publications/p946)
- Berkeley Lab, Utility-Scale Solar 2025 Edition (2024 data): installed cost $1.61/Wac national, $1.38/Wac ERCOT (slide 34); median O&M ~$11/kWac-yr; levelized PPA average $29/MWh, IQR $22-40 (slide 11); ERCOT solar curtailment 7.1% (slide 57); ERCOT solar market value $24/MWh vs $29 flat block, read from the slide-61 chart (https://emp.lbl.gov/sites/default/files/2025-10/Utility%20Scale%20Solar%202025%20Edition%20Slides.pdf)
- Cole, Ramasamy & Turan, Cost Projections for Utility-Scale Battery Storage: 2025 Update (NREL/TP-6A40-93281): 2024 cost of a 4-hour system $334/kWh (2024$) = $241/kWh energy + $372/kW power (https://docs.nlr.gov/docs/fy25osti/93281.pdf)
