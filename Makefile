.PHONY: venv test build selfcheck clean demo
venv:
	python3 -m venv .venv && . .venv/bin/activate && python -m pip install -U pip
test:
	. .venv/bin/activate && pip install -e .[dev] || pip install -e . && pytest -q
build:
	. .venv/bin/activate && python -m build && twine check dist/*
selfcheck:
	chmod +x scripts/local_selfcheck.sh && ./scripts/local_selfcheck.sh
clean:
	rm -rf .venv .venv_install_test dist *.egg-info build runs/self_demo
demo:
	python -m leakage_buster.cli --train examples/synth_train.csv --target y --time-col date --out runs/demo
