.PHONY: demo
demo:
	python -m leakage_buster.cli --train examples/synth_train.csv --target y --time-col date --out runs/demo
