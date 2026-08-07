.PHONY: setup lint test gate campaign reproduce

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
