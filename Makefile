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
	@echo "make test              Run repo verification (fast smoke checks)"
	@echo "make check             Alias for test"
	@echo "make doctor            Run ytf doctor"

# ---- Repo verification (thin wrappers) ----
.PHONY: test
test:
	@$(PY) -m compileall -q src
	@$(PY_ENV) $(PY) -m ytf --help >/dev/null
	@$(PY_ENV) $(PY) -m ytf doctor

.PHONY: check
check: test

.PHONY: doctor
doctor:
	@$(PY_ENV) $(PY) -m ytf doctor

# ---- Task workflow ----
.PHONY: next
next:
	@$(PY_ENV) $(PY) -m ytf.tools.tasks --file "$(TASKS_FILE)" next

.PHONY: verify
verify:
	@if [ -z "$(TASK)" ]; then echo "Usage: make verify TASK=T001"; exit 2; fi
	@$(PY_ENV) $(PY) -m ytf.tools.tasks --file "$(TASKS_FILE)" verify "$(TASK)"

.PHONY: done
done:
	@if [ -z "$(TASK)" ]; then echo "Usage: make done TASK=T001 [FORCE=1]"; exit 2; fi
	@if [ "$(FORCE)" = "1" ]; then \
		$(PY_ENV) $(PY) -m ytf.tools.tasks --file "$(TASKS_FILE)" done "$(TASK)" --force; \
	else \
		$(PY_ENV) $(PY) -m ytf.tools.tasks --file "$(TASKS_FILE)" done "$(TASK)"; \
	fi


