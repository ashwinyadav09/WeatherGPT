PY ?= python

.PHONY: doctor up down test lint eval replay-alerts contracts acceptance ci progress secret-scan demo

doctor:
	$(PY) scripts/dev.py doctor
up:
	$(PY) scripts/dev.py up
down:
	$(PY) scripts/dev.py down
test:
	$(PY) scripts/dev.py test
lint:
	$(PY) scripts/dev.py lint
eval:
	$(PY) scripts/dev.py eval --lang $(LANG)
replay-alerts:
	$(PY) scripts/dev.py replay-alerts
contracts:
	$(PY) scripts/dev.py contracts
acceptance:
	$(PY) scripts/dev.py acceptance
ci:
	$(PY) scripts/dev.py ci
progress:
	$(PY) scripts/dev.py progress
secret-scan:
	$(PY) scripts/dev.py secret-scan
demo:
	$(PY) scripts/dev.py demo
