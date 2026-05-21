# Day 1 Build Notes

This repo has two runnable paths:

1. `python main.py` starts the dependency-light live app using Python stdlib HTTP.
2. `uvicorn apps.api.main:app --reload` starts the FastAPI app after dependencies are installed.

The live app supports:

- Create Notary
- Choose privacy mode
- Upload evidence
- Paste transcript fallback when Speedmatic is not connected
- Run Witness-to-Pay
- Persist attestations, predictions, payment triggers, and karma in SQLite
- Create local Qevorpay payment links

