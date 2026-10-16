# Credit memo: senior secured term loan, {pv_mwac} MWac solar and {bess_mw} MW / {bess_mwh} MWh storage, West Texas (ERCOT)

Illustrative project financing built on public benchmarks; not a real project, rating or offer.
Data as of {as_of}. Model inputs fingerprint `{fingerprint}`; every figure below is generated from
`models/solar_storage_pf.xlsx` and its Python engine.

## Recommendation

Approve a {debt} senior secured term loan ({gearing} of project capex), {tenor}-year tenor from
commercial operation, fixed at {rate} through a swap, sculpted to {t50} on P50 and {t90} on P90 cash
flow. The debt is well covered: it services at {t90} until output falls to {be_share} of P50 in every
year, roughly a one-in-{be_return} annual outcome. The credit question is the contract, not the
resource. The loan sizes off a solar PPA at {ppa}, which is {ppa_premium} above the top of Berkeley
Lab's {lbnl_year} contract range; approval is conditional on that PPA being signed with an
investment-grade offtaker.

## Transaction

The project is {pv_mwac} MWac ({pv_mwdc} MWdc at a {ilr} inverter loading ratio) of single-axis tracking
solar and a {bess_hours}-hour, {bess_mw} MW battery, financed at a single financial close.

{su_table}

Solar capex is Berkeley Lab's {lbnl_year} ERCOT installed cost of {pv_capex_w}; battery capex is NLR's
bottom-up cost of {bess_capex_kwh} for a {bess_hours}-hour system. Tax credits of {itc_rate} on both are assumed
transferred at {itc_price_usd} per dollar of credit; in practice these proceeds would bridge to closing rather than
arrive at it.

## Revenue and output

| | Year one |
| --- | ---: |
| Solar revenue (P50) | {pv_rev_y1} |
| Battery toll | {toll_rev} |
| Operating costs | ({opex_y1}) |
| CFADS (P50) | {cfads_y1} |

- Output. NREL ATB resource-class capacity factor of {cf}, less ERCOT's {curtailment} solar curtailment
  rate, gives a {net_cf} net capacity factor and {gen_y1} GWh in year one, degrading {degradation} a
  year. P90 and P99 one-year output are {p90_factor} and {p99_factor} of P50, from an assumed {sigma}
  one-year uncertainty.
- Solar contract. As-generated PPA at {ppa} flat for {ppa_term} years, then merchant at ERCOT's
  {lbnl_year} solar market value of {merchant} (against {flat_block} for a flat block). The PPA price
  was solved so the sponsor's after-tax equity return is {hurdle} at benchmark capex and today's
  rates. For comparison, the {lbnl_year} national average was {lbnl_avg} (interquartile range
  {lbnl_low} to {lbnl_high}) and Berkeley Lab puts ERCOT's after-credit solar LCOE at {ercot_lcoe}.
- Battery contract. Tolling agreement at {toll} for {toll_term} years, matching the battery's
  {bess_life}-year life; the battery is {bess_share} of year-one revenue. ERCOT has no capacity market,
  so the toll stands in for capacity and ancillary value.

## Debt sizing

Debt service in each year is the lower of P50 CFADS / {t50} and P90 CFADS / {t90}. The loan is the
present value of that schedule at the coupon, capped at {max_gearing} gearing; {gearing_clause}.
Interest is charged on the opening balance and principal is service less interest, so the balance
repays exactly at maturity with no circular calculation.

{ratios_table}

P50 coverage is a flat {min_dscr_p50} by construction, and the LLCR equals it. Debt service steps down
from {ds_before} to {ds_after} after year {bess_life}, when the toll and the battery's assumed life
end; the sculpting absorbs the loss of battery revenue rather than leaving a coverage cliff. Maturity
falls inside the PPA, so no merchant revenue supports the debt.

## Stress cases

Generation and price stresses run against the debt schedule fixed at close; the rate shock and the
capex overrun act at close (the shock re-sizes the debt; the overrun is funded with equity).

{stress_definition}

{stress_table}

At one-year P90 in every year, minimum coverage is {down_min}; at P99 it is {severe_min}, with
{severe_lockup} years in distribution lock-up and {severe_default} below the default trigger. Equity
absorbs the stress: after-tax equity IRR falls to {down_eq} in the Downside and {severe_eq} in the
Severe case. The largest single levers, one at a time from the base case:

On minimum coverage:

{sens_dscr}

On after-tax equity IRR:

{sens_irr}

## Key credit risks

- Contract price. The PPA is priced above recent market prints. At {low_ppa}, the top of the
  {lbnl_year} range, the same sculpting supports {low_debt} of debt ({low_debt_cut} less), equity
  rises to {low_equity} and the after-tax equity IRR falls to {low_eq_irr}. The loan should not be sized
  on an unsigned price.
- Resource and curtailment. ERCOT's solar curtailment rate was higher than CAISO's and SPP's in
  {lbnl_year} and is concentrated in West Texas; it is held constant here. {p99_clause}.
- Battery. The toll's {toll_term} years of revenue rest on one counterparty and one asset with a shorter life
  than the solar. Debt service is sculpted down when the toll ends, but toll default before then is
  not mitigated by the structure.
- Tax credits. Equity relies on transferring the credits; federal rules for solar credits changed
  recently, and the model shows no solar credit as a sensitivity. The credits sit with equity, not debt.
- Construction and capex. Overruns are equity-funded in the model; the term sheet needs a completion
  guarantee or contingent equity to make that true.
- Interest rate. A higher rate at pricing reduces the loan ({severe_debt} in the Severe case) but does
  not change coverage, because the schedule is fixed to cash flow; the coupon must be swapped at close.

## Structural mitigants

- Sculpted amortisation at {t50} P50 and {t90} P90, maturing inside the PPA.
- Debt service reserve of {dsra_months} months, funded at close ({dsra}).
- Distribution lock-up at {lockup} and event of default at {default} (proposed; the model counts the
  years each would trip). A cash sweep is not modelled; with sculpted amortisation the structure relies
  on the lock-up.
- Gearing cap of {max_gearing} of project capex as a second sizing limit.

## Conditions precedent

- Executed PPA at or above {ppa} with an investment-grade offtaker, and an executed battery toll.
- Independent engineer's energy yield and curtailment study supporting the P50 and P90 used here.
- Executed tax-credit transfer agreement, or a bridge facility sized to the credit.
- Interest rate swap at close; fixed-price EPC with completion support.

## Data and limitations

Annual periods; pre-tax CFADS for debt and an after-tax equity view that assumes the sponsor uses tax
losses as they arise (no tax-equity partnership); no battery repowering after year {bess_life}; the
merchant tail is floored at zero (the plant is idled rather than run at a loss); grid emissions use
the eGRID ERCOT average rate of {grid_rate} lb CO2e per MWh, not a marginal rate. On that basis the
project displaces {t_y1} tCO2e in year one and {t_life} million over its life ({capex_per_t} of project
capex per tonne). Sourced inputs:

{sources_table}
