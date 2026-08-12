SHELL := /bin/bash
PYTHON ?= python3
UV ?= uv
UV_PYTHON := $(UV) run python

.PHONY: setup doctor requirements docs docs-check gates test test-gates lint typecheck imports build check

setup:
	$(PYTHON) scripts/dev.py setup

doctor:
	$(UV_PYTHON) scripts/dev.py doctor

requirements:
	$(UV_PYTHON) scripts/dev.py requirements

docs:
	$(UV_PYTHON) scripts/dev.py docs

docs-check:
	$(UV_PYTHON) scripts/dev.py docs-check

gates:
	$(UV_PYTHON) scripts/dev.py gates

test:
	$(UV_PYTHON) scripts/dev.py test

test-gates:
	$(UV_PYTHON) scripts/dev.py test-gates

lint:
	$(UV_PYTHON) scripts/dev.py lint

typecheck:
	$(UV_PYTHON) scripts/dev.py typecheck

imports:
	$(UV_PYTHON) scripts/dev.py imports

build:
	$(UV_PYTHON) scripts/dev.py build

check:
	$(UV_PYTHON) scripts/dev.py check
