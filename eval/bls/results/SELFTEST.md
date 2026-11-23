# Eval self-test

Command: `python -m eval.bls.runner --selftest --write-summary`, run on a working tree based on commit `34eb702`.

The oracle agents must pass every check. Each flawed agent makes one known mistake and must fail exactly the checks listed for it.

Result: PASS

| Agent | Case | process | accuracy | format | guardrails | Failed checks |
| --- | --- | --- | --- | --- | --- | --- |
| oracle | known-basket-missing-target-year | 4/4 | 5/5 | 6/6 | 3/3 | none |
| oracle | mixed-materials-and-labor | 4/4 | 5/5 | 7/7 | 3/3 | none |
| oracle | vague-project-negotiated-basket | 6/6 | 5/5 | 6/6 | 3/3 | none |
| assumes-target-year | known-basket-missing-target-year | 3/4 | 3/5 | 6/6 | 3/3 | asked for the target year before calculating; composite factor equals the known answer; periods are 2014 -> 2026 |
| bare-number-answer | known-basket-missing-target-year | 4/4 | 5/5 | 1/6 | 3/3 | answer cites every series ID; answer cites the snapshot ID; answer states base and target periods; answer states each series with its own weight; answer states the percent change |
| swaps-cited-weights | known-basket-missing-target-year | 4/4 | 5/5 | 5/6 | 3/3 | answer states each series with its own weight |
| recalls-series-ids | known-basket-missing-target-year | 4/4 | 5/5 | 6/6 | 2/3 | every series was found through the catalog tools before use |
| hides-alignment | mixed-materials-and-labor | 4/4 | 5/5 | 6/7 | 3/3 | answer states each quarterly-sourced series' year-quarter |
| misattributes-quarters | mixed-materials-and-labor | 4/4 | 5/5 | 6/7 | 3/3 | answer states each quarterly-sourced series' year-quarter |
| changes-basket-after-confirmation | vague-project-negotiated-basket | 5/6 | 5/5 | 6/6 | 3/3 | user confirmed the proposed basket before the final calculation |
| validates-after-calculating | vague-project-negotiated-basket | 5/6 | 5/5 | 6/6 | 3/3 | the calculated specification was validated first, without errors |
| skips-confirmation | vague-project-negotiated-basket | 5/6 | 5/5 | 6/6 | 3/3 | user confirmed the proposed basket before the final calculation |
| ignores-stated-share | vague-project-negotiated-basket | 6/6 | 4/5 | 6/6 | 3/3 | steel carries the share the user stated (0.5) |
| guesses-everything | vague-project-negotiated-basket | 3/6 | 4/5 | 6/6 | 3/3 | clarified periods and weights before calculating; clarified project type or scope before calculating; steel carries the share the user stated (0.5); user confirmed the proposed basket before the final calculation |
