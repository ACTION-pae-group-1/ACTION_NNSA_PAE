# Custom PPI Escalation Index
## MCP data interface and UI/UX collaboration brief

### What I'm hoping we can explore

I'm designing the MCP side of a custom PPI escalation index app and wanted to share the information the service can return, along with a concrete sample response. I'm looking for the UI/UX team's help shaping how that information is experienced. The layouts and chart types below are suggestions, not requirements or implementation instructions.

The index combines Producer Price Index (PPI) series normalized to a common base year, each with a fixed allocation weight. The weights total 100%, and the weighted normalized series add up to a composite index. This experience focuses on exploring an already-calculated result, not choosing source series, editing weights, or retrieving new BLS data.

### What the MCP returns

The attached `index_visualization_v1.schema.json` defines the proposed version 1.0 result structure; `index_visualization_v1.example.json` is a concrete, illustrative response that follows that structure. The schema is the interface reference, while the example is a useful starting point for mockups and design discussion.

| Payload section | What the UI can use it for |
| --- | --- |
| `index_identity` | Index name, IDs, revision, snapshot, methodology version, and frequency. |
| `normalization` | Base year, base factor, and normalization method. |
| `components[]` | Names, descriptions, BLS series IDs, weights, display order, optional raw reference details and suggested colors. |
| `component_points[]` | Period-by-component raw observations, normalized factors, weighted levels, and observation IDs. |
| `composite_points[]` | Composite factor for each period. |
| `base_year_adjustment` | Optional source-year-to-base-year factor and signed component steps; can be `null`. |
| `warnings[]` | Structured messages with code, severity, and text. |

The payload is deliberately long-form: component definitions and period observations are separate records linked by stable `component_id` values. Numeric calculation results are represented as **decimal strings** to preserve precision. The UI can format them as percentages or reshape them for a chart, but the MCP remains authoritative for the economic calculations. `color_hex` is optional presentation metadata, not a requirement to use a particular palette.

### A concrete example to design against

The example response describes a **Courthouse Renovation Escalation Index**, with **2024** as its annual base year. It contains two components: **Steel mill products (40%)** and **Electrical equipment (60%)**. These are illustrative values, not a proposed production basket.

| Value in sample | 2023 | 2024 (base year) |
| --- | --- | --- |
| Steel normalized factor | 0.94 (94%) | 1.00 (100%) |
| Steel weighted level | 0.376 | 0.400 |
| Electrical normalized factor | 0.97 (97%) | 1.00 (100%) |
| Electrical weighted level | 0.582 | 0.600 |
| **Composite factor** | **0.958 (95.8%)** | **1.000 (100%)** |

The composite is the sum of the weighted levels for each period. For example, in 2023, `0.376 + 0.582 = 0.958`. The example also supplies raw PPI observations (94 and 97 for 2023; 100 and 100 for 2024), along with the observation IDs. Raw PPI and normalized percentage are distinct concepts, even though the example's numbers happen to align.

The optional adjustment object illustrates **2023 → 2024**. It returns a factor of **1.0438413361**, or approximately **+4.3841%**. Its two component contributions are approximately **+2.5052 percentage points** (steel) and **+1.8789 percentage points** (electrical), measured against a starting point of 100% of the selected-year basket. Their sum leads to about **104.3841%**. Minor differences in final digits reflect rounding in the sample.

This small example should be enough to prototype selection, chart labeling, tooltips, an adjustment explanation, and a data table. It is only two years and two components, so it does not by itself test crowded legends, longer histories, or missing-data states.

### What users should be able to explore

**Basket composition.** Users should understand which PPI series are included and their allocation weights. A horizontal allocation ribbon with labels or a compact component list could work. I'm open to a different treatment if it scales better.

**Composite history.** Users should see how the overall index changes and how the weighted component levels combine. A stacked-area view with a composite line is one possible approach. The areas would represent `weighted_level`, not raw PPI or period-over-period contribution percentages; the composite would correspond to `composite_factor`.

**Individual component history.** Selecting a component could show its name, description, BLS series ID, weight, and unweighted history. A switch between normalized percent-of-base and raw PPI could be useful. A normalized factor of 1.0 displays as 100%; raw values retain their original reference basis. The component detail should not apply its weight again.

**Adjustment to base year.** If `base_year_adjustment` is present, users could explore how the selected source year adjusts to the base year. A waterfall is a candidate, but other explanations are welcome. The returned steps describe signed contributions to an adjustment factor starting at 1.0, not a bridge from the source-year composite level to the base-year index level. Positive and negative adjustments are both possible.

**Audit and export.** A searchable or filterable table could expose the underlying component-period records, with an option to export the filtered dataset to CSV. The table should make it possible to reconcile chart values to source observations and the returned composite. I'd be interested in the team's view on how much provenance to show up front versus in details.

### Possible information hierarchy

One starting point is a concise index header and base-year context, followed by basket composition and the composite trend, then component detail, adjustment, and underlying data in tabs or stacked sections. This is a suggestion about what information may be useful together, not a proposed screen specification.

Consistent component labels, accessible selection controls, meaningful non-color indicators, and understandable empty or error states would help make the result usable. The schema provides a `warnings[]` collection; we should decide together how prominent those messages need to be.

### Data semantics to keep intact

The annual base-year normalized and composite factors are 1.0. Weights sum to 1.0; each `weighted_level` is the weight times the normalized factor; and the composite is the sum of the weighted levels for a period. Adjustment contributions reconcile to the returned adjustment factor. Missing values should not be silently treated as zero or interpolated. These are responsibilities of the MCP calculation and validation layer, not extra calculations the UI needs to invent.

The result is intended to be usable from its supplied snapshot without a live BLS request. The optional adjustment may be absent (`null`), and warnings may be an empty array. The UI should handle those cases without assuming every panel has content.

### Where I'd value the team's input

I'd especially like feedback on which information deserves first-screen attention, how to navigate larger baskets, whether the suggested charts convey the right quantities, and whether the payload needs additional fields to support a better experience. I'm happy to adapt the MCP data interface where there's a clear UX benefit. The schema is a proposed handoff, not a reason to make the UI work harder than necessary.

**Companion files:** `index_visualization_v1.schema.json` (proposed machine-readable interface) and `index_visualization_v1.example.json` (illustrative response). The schema and example describe the data available today; this brief is an invitation to shape its presentation together.
