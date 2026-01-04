SHELL := /bin/bash
.DEFAULT_GOAL := help

TASKS_FILE := docs/TASKS.md
PY ?= $(shell if [ -x ./venv/bin/python ]; then echo ./venv/bin/python; else echo python3; fi)
PY_ENV := PYTHONPATH=src

.PHONY: help
help:
	@echo "make next              Print the next unchecked task id (T###)"
	@echo "make verify TASK=T001  Run Verify commands for task"
	@echo "make done TASK=T001    Mark task done (use FORCE=1 to actually flip)"
	@echo "make test              Run repo verification (offline smoke checks)"
	@echo "make check             Alias for test"
	@echo "make doctor            Run ytf doctor (full checks including API keys)"
	@echo "make doctor-offline    Run offline doctor (local tools only, no API keys)"

# ---- Repo verification (offline, no API keys required) ----
.PHONY: test
test:
	@bash scripts/verify.sh

.PHONY: check
check: test

.PHONY: doctor
doctor:
	@$(PY_ENV) $(PY) -m ytf doctor

.PHONY: doctor-offline
doctor-offline:
	@echo "Checking local prerequisites (offline, no API keys)..."
	@$(PY) --version
	@command -v ffmpeg >/dev/null 2>&1 && echo "✓ FFmpeg found" || echo "✗ FFmpeg not found"
	@command -v ffprobe >/dev/null 2>&1 && echo "✓ FFprobe found" || echo "✗ FFprobe not found"
	@mkdir -p projects && test -w projects && echo "✓ Projects directory writable" || echo "✗ Projects directory not writable"

.PHONY: smoke
smoke:
	@PYTHONPATH=src $(PY) -m ytf new "smoke" --channel cafe_jazz --minutes 10 --tracks 2 --vocals on

# ---- Task workflow ----
.PHONY: next
next:
	@$(PY_ENV) $(PY) -m ytf.tools.tasks next --file "$(TASKS_FILE)"

.PHONY: verify
verify:
	@if [ -z "$(TASK)" ]; then echo "Usage: make verify TASK=T001"; exit 2; fi
	@$(PY_ENV) $(PY) -m ytf.tools.tasks verify "$(TASK)" --file "$(TASKS_FILE)"

.PHONY: done
done:
	@if [ -z "$(TASK)" ]; then echo "Usage: make done TASK=T001 [FORCE=1]"; exit 2; fi
	@if [ "$(FORCE)" = "1" ]; then \
		$(PY_ENV) $(PY) -m ytf.tools.tasks done "$(TASK)" --file "$(TASKS_FILE)" --force; \
	else \
		$(PY_ENV) $(PY) -m ytf.tools.tasks done "$(TASK)" --file "$(TASKS_FILE)"; \
	fi


