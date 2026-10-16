# Investment memo: {units}-unit multifamily acquisition and retrofit, Washington, DC

Illustrative underwriting case built on public benchmarks; not a real property or offer.
Data as of {as_of}. Model inputs fingerprint `{fingerprint}`; every figure below is generated from
`models/property_underwriting.xlsx` and its Python engine.

## Recommendation

Proceed with the acquisition at {price} ({price_unit} per unit, a {going_in_cap} going-in cap rate) on
status-quo underwriting. Approve the electrification and solar retrofit as compliance capital rather
than as a return enhancement: it lowers the levered IRR by {irr_delta} and does not pay back on
utility savings, but it takes the building through the DC Building Energy Performance Standards
pathway and removes up to {beps_penalty} of penalty exposure. The retrofit decision should be
revisited if heat pump bids come in above {hp_unit} per unit.

## Asset and underwriting

The asset is a {units}-unit mid-rise of {nrsf} net rentable square feet ({gfa} square feet gross) with
central gas boilers for heat and hot water. The owner pays for gas, common-area electricity, water and
sewer; residents pay for in-unit electricity.

In-place rents are {rent_studio} (studio), {rent_1br} (one-bedroom), {rent_2br} (two-bedroom) and
{rent_3br} (three-bedroom). The two-bedroom rent sits at the top of the FY{hud_fy} HUD Small Area Fair
Market Rent range for District ZIP codes ({hud_2br_low} to {hud_2br_high}), so there is little
mark-to-market upside assumed; rent growth is {rent_growth} a year against {exp_growth} expense
growth.

Year-one gross potential rent is {gpr_y1}. After {vacancy} vacancy and other income, effective gross
income is {egi_y1}. Operating expenses of {opex_y1} ({opex_ratio} of income) include real estate tax at
the District's multifamily rate of {tax_rate} of assessed value and owner-paid utilities priced at EIA's
District commercial averages ({elec_price}; {gas_price}). Net operating income is {noi_y1}, and net cash
flow after {reserves} per unit of reserves is {ncf_y1}.

## Financing

The loan is sized at the lowest of three tests on year-one status-quo cash flow:

| Test | Maximum loan |
| --- | ---: |
| {ltv_max} loan-to-value | {max_ltv_loan} |
| {dscr_sizing} DSCR on a {debt_constant} amortising constant | {max_dscr_loan} |
| {dy_sizing} debt yield | {max_dy_loan} |

The DSCR test binds, giving a {loan} loan at {ltv} loan-to-value. The rate is {rate_fixed} fixed (the
ten-year Treasury at {ust} plus {fixed_spread}), with {io_years} years interest-only and a
{amort_years}-year amortisation. Leverage is held below the LTV limit by the rate, not by value; the
floating alternative (SOFR at {sofr} plus {float_spread}) is available in the model but carries
unhedged rate risk.

Proposed covenants are a cash trap at {dscr_trap} DSCR or {dy_trap} debt yield and a default at
{dscr_default} or {dy_default}. Minimum DSCR over the hold is {min_dscr_sq} in the status quo and
{min_dscr_rf} with the retrofit; minimum debt yield is {min_dy_sq}. Year-one NOI could fall
{dscr_headroom_y1} before the cash trap is reached.

## Returns

{hold}-year hold, sold at a {exit_cap} exit cap on forward NOI:

{returns_table}

The retrofit adds {exit_uplift} to the exit value through higher NOI but costs {retro_net} at closing,
so both IRR measures are lower in the retrofit case.

## Retrofit

{retrofit_table}

Heat and hot water move to central air-to-water heat pumps (seasonal COP {cop_heat} for heating,
{cop_dhw} for hot water, replacing boilers at {boiler_eff} seasonal efficiency). Rooftop solar of
{solar_kw} kWdc produces about {solar_mwh} MWh a year ({solar_yield} kWh per kWdc from PVWatts), all of
it used on site.

Year-one owner utility savings are {savings_y1}: solar {save_solar}, LEDs {save_led} and envelope work
{save_envelope}. Electrification on its own {electrification_sign} {electrification_abs} a year, because at
District prices heat pump electricity and the gas it replaces cost about the same per unit of heat
delivered.
Simple payback is {payback} years,
or {payback_boiler} years after crediting the {boiler_cost} boiler replacement the status quo would
need in year {boiler_year}. On utility savings alone the retrofit is not an investment.

{energy_table}

Site EUI falls {eui_cut}, from {eui_base} to {eui_rf} kBtu per square foot ({eui_net} net of on-site
solar), against the {beps_cut} reduction the BEPS performance pathway requires, so the retrofit
{beps_met} the standard. Without it the building is exposed to a penalty of up to {beps_per_sf} per
square foot, {beps_penalty} in total, which is not included in the IRRs above. Owner Scope 1 and 2
emissions fall by {t_avoided} tCO2e a year ({t_avoided_pct}), at {cost_per_t} per tonne over a
{measure_life}-year measure life. Grid emissions use the eGRID RFC East rate of {grid_rate} lb CO2e
per MWh, held flat, so the benefit of a cleaner grid over the hold is not counted.

## Downside cases

The loan is held at its closing size and operations, the exit and the retrofit underperform:

{stress_definition}

{stress_table}

In the Severe case the minimum DSCR falls to {severe_min_dscr}, {severe_vs_default} the {dscr_default} default covenant, with
{trap_years_severe} covenant flag-years over the hold. Holding the loan, vacancy would have to reach
{be_vacancy} before the minimum DSCR hits the default covenant. The largest single levers on the
retrofit-case levered IRR are:

{sens_irr}

## Risks and mitigants

- Rent growth. It is the largest single lever on returns ({top_lever}: {top_lever_bp} of levered IRR),
  and rents already sit at the top of the HUD range for District ZIP codes. Mitigant: the cash trap
  captures cash before a payment default.
- Exit pricing. Returns rely on a {exit_cap} exit cap at today's rates. Mitigant: the DSCR-sized loan
  leaves value cushion below the {ltv_max} LTV limit.
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

{sources_table}
