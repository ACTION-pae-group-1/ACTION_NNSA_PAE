# CAEF demonstration assets

The application resolves its saved prediction and optional signed model relative to this folder.

This source patch **does not contain a trained CAEF bundle or authentic completed predictions**. Use `tools/prepare_caef_demo_assets.py` to package a verified, synthetic-origin trained run from the local checkout. The release readiness check must fail when those inputs are absent; do not invent model predictions.

Expected assets after packaging:

- `predicted_levels.parquet` — saved results for demo projects (only genuine model output)
- `demo_run.json` and `<run-id>/run_manifest.json` — completed synthetic-origin run
- `<run-id>/working.duckdb` and signed `<run-id>/bundles/untuned/*` — inference inputs/model
- `demo_verification.key` — **dedicated synthetic demo verification secret**; must never be a production signing credential

The demo key ships for an offline demonstration only. HMAC verification using a distributed key is **not** a production-grade authenticity boundary. Use a production key outside the distributable or asymmetric signatures for trusted deployment. Do not distribute genuine/restricted PARS records.

Monthly PARS refreshes are not ingested by this demo inference path. An authorized read-only adapter remains future implementation.
