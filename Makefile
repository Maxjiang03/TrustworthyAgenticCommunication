.PHONY: setup lint test gate campaign reproduce figures

setup:
	uv sync

lint:
	pre-commit run --all-files

test:
	pytest -q

gate:
	@test -n "$(GATE)" || (echo "usage: make gate GATE=g1"; exit 1)
	python smoke/$(GATE)/spike.py

# Part H step 7. Executes the frozen campaign ONCE and writes results/raw/
# (ADR 0045). It REFUSES to overwrite an existing result: a second run is a
# decision, recorded in DEVIATIONS.md, never a default.
campaign:
	python -m src.harness.campaign_driver --run-mode confirmatory

# Every table and figure, regenerated from results/raw/ by one command
# (design J.3 item 12). No manual step, no spreadsheet.
reproduce:
	python -m analysis.report --run-mode confirmatory

# Every figure and table artefact of the results chapter, regenerated from
# results/raw/ + results/tables/ by one command (ADR 0048: the presentation
# layer lives in tools/figures/, outside the seal, and computes nothing).
# Latency artefacts (FIG-4/5/6, TAB-6/7/8) are D3-gated and NOT built here.
figures:
	python -X utf8 tools/figures/build_all.py
