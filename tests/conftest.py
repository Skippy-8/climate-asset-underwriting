from pathlib import Path

import pytest

from cau.engine import property as P
from cau.engine import solar_storage as SS
from cau.inputs import load_inputs, values
from cau.xlsx import pf_book, property_book
from cau.xlsx.evaluate import evaluate

ROOT = Path(__file__).resolve().parents[1]

# name -> (engine module, workbook builder, committed file, calculation tabs)
MODELS = {
    "property": (P, property_book, "property_underwriting.xlsx",
                 ("RentRoll", "Energy", "Operating", "Debt", "Covenants", "Returns", "Retrofit", "Checks", "Summary")),
    "solar_storage": (SS, pf_book, "solar_storage_pf.xlsx",
                      ("Capex_SU", "Generation", "Revenue", "Opex", "CFADS", "Debt_Sculpt", "Ratios", "Tax", "Returns",
                       "Checks", "Summary")),
}


@pytest.fixture(scope="session")
def prop_inputs():
    return load_inputs("property")


@pytest.fixture(scope="session")
def prop(prop_inputs):
    return P.run(values(prop_inputs))


@pytest.fixture(scope="session")
def pf_inputs():
    return load_inputs("solar_storage")


@pytest.fixture(scope="session")
def pf(pf_inputs):
    return SS.run(values(pf_inputs))


@pytest.fixture(scope="session", params=list(MODELS))
def model(request, tmp_path_factory):
    """One of the two models: its inputs, engine result, a freshly built workbook and that workbook's
    evaluated named values."""
    name = request.param
    engine, builder, committed, calc = MODELS[name]
    inputs = load_inputs(name)
    path = builder.build(inputs, tmp_path_factory.mktemp(name) / committed)
    return {"name": name, "inputs": inputs, "result": engine.run(values(inputs)), "xlsx": path,
            "eval": evaluate(path), "committed": ROOT / "models" / committed, "calc_sheets": calc}
