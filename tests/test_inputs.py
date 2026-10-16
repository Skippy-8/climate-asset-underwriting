"""Every input is tagged and traceable to a cited source."""
import pytest

from cau.inputs import TAGS, load_inputs, load_sources


@pytest.mark.parametrize("model", ["property", "solar_storage"])
def test_every_input_is_tagged_and_sourced(model):
    sources = load_sources()
    for i in load_inputs(model):
        assert i.tag in TAGS
        assert i.source in sources
        if i.tag == "Sourced":
            assert sources[i.source]["url"], f"{i.key} is tagged Sourced but its source has no URL"
            assert i.source not in ("analyst", "asset", "definition"), i.key


def test_estimates_and_illustrations_are_not_dressed_up_as_sources():
    for i in load_inputs("property"):
        if i.source in ("analyst", "asset"):
            assert i.tag in ("Estimated", "Illustrative"), i.key
