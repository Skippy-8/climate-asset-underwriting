# Developer targets.  `make help` lists them.

PY ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
BIN := $(dir $(PY))

.DEFAULT_GOAL := help
.PHONY: help test lint check models memos actuals dashboard

help:  ## list the targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F ':.*## ' '{printf "  \033[1m%-10s\033[0m %s\n", $$1, $$2}'

test:  ## the full pytest suite
	$(PY) -m pytest

lint:  ## ruff
	$(BIN)ruff check .

check: lint test  ## lint, then test

models:  ## rebuild both workbooks (recalculated in Excel when available)
	$(PY) scripts/build_models.py

memos:  ## re-render both memos from the engines
	$(PY) -m cau.memos

actuals:  ## rewrite the synthetic year-to-date actuals
	$(PY) -m cau.actuals

dashboard:  ## run the monitoring dashboard
	$(BIN)streamlit run dashboard/app.py
