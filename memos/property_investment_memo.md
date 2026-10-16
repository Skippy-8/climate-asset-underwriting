# Investment memo: 150-unit multifamily acquisition and retrofit, Washington, DC

Illustrative underwriting case built on public benchmarks; not a real property or offer.
Data as of 2026-10-15. Model inputs fingerprint `b49b9c9c6063`; every figure below is generated from
`models/property_underwriting.xlsx` and its Python engine.

## Recommendation

Proceed with the acquisition at $47.0m ($313,333 per unit, a 5.56% going-in cap rate) on
status-quo underwriting. Approve the electrification and solar retrofit as compliance capital rather
than as a return enhancement: it lowers the levered IRR by 41 bp and does not pay back on
utility savings, but it takes the building through the DC Building Energy Performance Standards
pathway and removes up to $1.50m of penalty exposure. The retrofit decision should be
revisited if heat pump bids come in above $10,000 per unit.

## Asset and underwriting

The asset is a 150-unit mid-rise of 119,250 net rentable square feet (150,000 square feet gross) with
central gas boilers for heat and hot water. The owner pays for gas, common-area electricity, water and
sewer; residents pay for in-unit electricity.

In-place rents are $1,750 (studio), $2,050 (one-bedroom), $2,600 (two-bedroom) and
$3,150 (three-bedroom). The two-bedroom rent sits at the top of the FY2026 HUD Small Area Fair
Market Rent range for District ZIP codes ($2,030 to $2,620), so there is little
mark-to-market upside assumed; rent growth is 3.0% a year against 3.0% expense
growth.

Year-one gross potential rent is $3.98m. After 5.0% vacancy and other income, effective gross
income is $3.96m. Operating expenses of $1.35m (34.1% of income) include real estate tax at
the District's multifamily rate of 0.85% of assessed value and owner-paid utilities priced at EIA's
District commercial averages ($0.1707/kWh; $14.36/Mcf). Net operating income is $2.61m, and net cash
flow after $300 per unit of reserves is $2.57m.

## Financing

The loan is sized at the lowest of three tests on year-one status-quo cash flow:

| Test | Maximum loan |
| --- | ---: |
| 65% loan-to-value | $30.6m |
| 1.25x DSCR on a 7.91% amortising constant | $26.0m |
| 8.0% debt yield | $32.7m |

The DSCR test binds, giving a $26.0m loan at 55.2% loan-to-value. The rate is 6.91% fixed (the
ten-year Treasury at 5.21% plus 170 bp), with 2 years interest-only and a
30-year amortisation. Leverage is held below the LTV limit by the rate, not by value; the
floating alternative (SOFR at 3.88% plus 290 bp) is available in the model but carries
unhedged rate risk.

Proposed covenants are a cash trap at 1.20x DSCR or 7.5% debt yield and a default at
1.10x or 6.5%. Minimum DSCR over the hold is 1.33x in the status quo and
1.35x with the retrofit; minimum debt yield is 10.1%. Year-one NOI could fall
16.1% before the cash trap is reached.

## Returns

10-year hold, sold at a 5.75% exit cap on forward NOI:

|  | Status quo | Retrofit |
| --- | ---: | ---: |
| Equity | $22.2m | $24.2m |
| Unlevered IRR | 7.6% | 7.4% |
| Levered IRR | 8.2% | 7.8% |
| Equity multiple | 2.05x | 1.96x |
| Gross exit value | $61.0m | $62.1m |
| Minimum DSCR | 1.33x | 1.35x |

The retrofit adds $1.08m to the exit value through higher NOI but costs $1.99m at closing,
so both IRR measures are lower in the retrofit case.

## Retrofit

| Measure | Cost |
| --- | ---: |
| Central air-to-water heat pumps, heat and hot water ($10,000/unit) | $1.50m |
| Envelope and air sealing | $0.23m |
| Common-area LEDs and controls | $0.04m |
| Rooftop solar, 180 kWdc | $0.32m |
| Less: solar tax credit | ($0.10m) |
| Net retrofit capex | $1.99m |

Heat and hot water move to central air-to-water heat pumps (seasonal COP 2.6 for heating,
2.8 for hot water, replacing boilers at 80% seasonal efficiency). Rooftop solar of
180 kWdc produces about 237 MWh a year (1,317.7 kWh per kWdc from PVWatts), all of
it used on site.

Year-one owner utility savings are $48,310: solar $40,488, LEDs $8,050 and envelope work
$3,853. Electrification on its own adds $4,082 a year, because at
District prices heat pump electricity and the gas it replaces cost about the same per unit of heat
delivered.
Simple payback is 41.3 years,
or 32.0 years after crediting the $450,000 boiler replacement the status quo would
need in year 3. On utility savings alone the retrofit is not an investment.

|  | Status quo | Retrofit |
| --- | ---: | ---: |
| Site EUI (kBtu/sf) | 59.6 | 37.1 |
| Owner Scope 1 (tCO2e/yr) | 237 | 0 |
| Owner Scope 2 (tCO2e/yr) | 94 | 119 |
| Owner Scope 1 + 2 (tCO2e/yr) | 332 | 119 |
| Tenant electricity, Scope 3 (tCO2e/yr) | 298 | 298 |

Site EUI falls 37.8%, from 59.6 to 37.1 kBtu per square foot (31.7 net of on-site
solar), against the 20% reduction the BEPS performance pathway requires, so the retrofit
meets the standard. Without it the building is exposed to a penalty of up to $10 per
square foot, $1.50m in total, which is not included in the IRRs above. Owner Scope 1 and 2
emissions fall by 212 tCO2e a year (64%), at $469 per tonne over a
20-year measure life. Grid emissions use the eGRID RFC East rate of 660.3 lb CO2e
per MWh, held flat, so the benefit of a cleaner grid over the hold is not counted.

## Downside cases

The loan is held at its closing size and operations, the exit and the retrofit underperform:

| Assumption | Base | Downside | Severe |
| --- | ---: | ---: | ---: |
| Vacancy and credit loss | 5.0% | 7.0% | 10.0% |
| Rent growth | 3.0% | 2.0% | 1.0% |
| Expense growth | 3.0% | 3.5% | 4.0% |
| Utility price growth | 2.5% | 3.5% | 5.0% |
| Exit cap rate | 5.75% | 6.25% | 6.75% |
| Heat pump cost per unit | $10,000 | $12,500 | $15,000 |
| Heat pump COP (heating) | 2.6 | 2.3 | 2.0 |

|  | Base | Downside | Severe |
| --- | ---: | ---: | ---: |
| Minimum DSCR, status quo | 1.33x | 1.24x | 1.09x |
| Minimum DSCR, retrofit | 1.35x | 1.27x | 1.11x |
| Minimum debt yield, status quo | 10.1% | 9.8% | 9.3% |
| Covenant flag-years, status quo | 0 | 0 | 8 |
| Levered IRR, status quo | 8.2% | 2.6% | -6.2% |
| Levered IRR, retrofit | 7.8% | 2.2% | -6.1% |
| Equity multiple, retrofit | 1.96x | 1.22x | 0.57x |
| Exit value, retrofit | $62.1m | $47.2m | $34.6m |
| Retrofit simple payback | 41.3 yrs | 54.1 yrs | 72.4 yrs |

In the Severe case the minimum DSCR falls to 1.09x, below the 1.10x default covenant, with
8 covenant flag-years over the hold. Holding the loan, vacancy would have to reach
16.3% before the minimum DSCR hits the default covenant. The largest single levers on the
retrofit-case levered IRR are:

- Rent growth -1.5 pts: 3.6% (-417 bp from base)
- Vacancy +5 pts: 5.9% (-190 bp from base)
- Floating rate, SOFR +200 bp: 6.2% (-163 bp from base)

## Risks and mitigants

- Rent growth. It is the largest single lever on returns (rent growth -1.5 pts: 417 bp of levered IRR),
  and rents already sit at the top of the HUD range for District ZIP codes. Mitigant: the cash trap
  captures cash before a payment default.
- Exit pricing. Returns rely on a 5.75% exit cap at today's rates. Mitigant: the DSCR-sized loan
  leaves value cushion below the 65% LTV limit.
- Retrofit cost and performance. Heat pump cost and efficiency are estimates and the largest
  retrofit sensitivity. Mitigant: phase the work, fix pricing before committing, and keep the
  boiler replacement as the fallback.
- Policy. The solar tax credit depends on federal rules after the recent law changes; the model
  stresses it to zero. The BEPS penalty structure is taken from the first compliance cycle and is
  assumed to carry over.

## Data and limitations

Annual periods; SOFR and the grid emission rate are held flat; the building is assumed to sit at the
ENERGY STAR national multifamily median EUI; end-use shares are estimates anchored to EIA RECS;
rents are estimates anchored to HUD Small Area FMRs. Sourced inputs:

- NREL/NLR Annual Technology Baseline 2024b, Commercial PV: CAPEX $1.78/Wdc (2023), fixed O&M ~$19/kWdc-yr; 200 kWdc flat-roof reference system (https://atb.nlr.gov/electricity/2024b/commercial_pv)
- DC Office of Tax and Revenue: Class 1A real property tax rate (residential, 3+ units) $0.85 per $100 of assessed value (https://otr.cfo.dc.gov/page/real-property-tax-rates)
- DC DOEE Building Energy Performance Standards Compliance Guidebook (Aug 2021) and Perkins Eastman BEPS guide: performance pathway = 20% site EUI reduction; penalty up to $10/ft2, capped at $7.5 million, prorated by progress. Cycle 2 (from 2027) assumed to carry the same structure. (https://doee.dc.gov/service/building-energy-performance-standards-beps)
- EPA eGRID2022 Summary Tables: total output emission rates, RFC East (RFCE) 660.3 lb CO2e/MWh; ERCOT All (ERCT) 774.3 lb CO2e/MWh; U.S. 827.5 lb CO2e/MWh (https://www.epa.gov/system/files/documents/2024-01/egrid2022_summary_tables.pdf)
- EIA Electric Power Annual, Table 2.10: District of Columbia average price to commercial customers, 17.07 cents/kWh (2024) (https://www.eia.gov/electricity/annual/html/epa_02_10.html)
- EIA Natural Gas Navigator, District of Columbia price delivered to commercial consumers (N3020DC3), $14.36/Mcf (2025 annual, released 2026-09-30) (https://www.eia.gov/dnav/ng/hist/n3020dc3a.htm)
- EPA GHG Emission Factors Hub (January 2025), Table 1: natural gas 53.06 kg CO2, 1.0 g CH4, 0.10 g N2O per mmBtu; 0.001026 mmBtu/scf; GWP CH4 28, N2O 265 (https://www.epa.gov/system/files/documents/2025-01/ghg-emission-factors-hub-2025.pdf)
- ENERGY STAR Portfolio Manager, U.S. National Median Table (August 2024): Multifamily Housing site EUI 59.6 kBtu/ft2, source EUI 118.1 (https://portfoliomanager.energystar.gov/pdf/reference/US%20National%20Median%20Table.pdf)
- FRED DGS10, 10-year Treasury constant maturity, 5.21% on 2026-10-13 (fetched with quantlab.data.sources.extra.fred_series) (https://fred.stlouisfed.org/series/DGS10)
- FRED SOFR, Secured Overnight Financing Rate, 3.88% on 2026-10-14 (fetched with quantlab.data.sources.extra.fred_series) (https://fred.stlouisfed.org/series/SOFR)
- NREL/NLR PVWatts v8.5 API run, Washington DC (38.90, -77.03), fixed roof mount, tilt 10, azimuth 180, 14% losses, DC/AC 1.2: 1,317.7 kWh AC per kWdc per year (https://developer.nlr.gov/docs/solar/pvwatts/v8/)
