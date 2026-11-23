"""Configuration and text cleaning for the PARS WBS pipeline.

Constants (abbreviations, stop phrases, stop words, domain terms) are ported from
WBS Modeling's DuckDB tables (bronze_abbreviations, bronze_stop_phrases,
silver_stop_words, etc.) for local use in PARS MCP.

Cleaning functions are verbatim ports of pure functions from WBS Modeling/functions.py.
This module is the single home for cleaning: hierarchy concatenation, stitching and
text normalization.
"""

from __future__ import annotations

import re

import polars as pl

# Abbreviations: acronym -> full text mapping (case-sensitive)
ABBREVIATIONS = {
    "WBS": "Work Breakdown Structure",
    "TBD": "To Be Determined",
    "CEO": "Chief Executive Officer",
    "CFO": "Chief Financial Officer",
    "CTO": "Chief Technology Officer",
    "API": "Application Programming Interface",
    "REST": "Representational State Transfer",
    "OAuth": "Open Authorization",
    "JWT": "JSON Web Token",
    "CRUD": "Create Read Update Delete",
    "ETL": "Extract Transform Load",
    "ELT": "Extract Load Transform",
    "KPI": "Key Performance Indicator",
    "SLA": "Service Level Agreement",
    "RTO": "Recovery Time Objective",
    "RPO": "Recovery Point Objective",
    "DR": "Disaster Recovery",
    "HA": "High Availability",
    "CI": "Continuous Integration",
    "CD": "Continuous Deployment",
    "QA": "Quality Assurance",
    "UAT": "User Acceptance Testing",
    "MVP": "Minimum Viable Product",
    "POC": "Proof of Concept",
    "RFP": "Request for Proposal",
    "RFI": "Request for Information",
    "SOW": "Statement of Work",
    "KDD": "Key Decision Document",
    "CM": "Construction Management",
    "TTO": "Transition to Operations",
    "k8s": "Kubernetes",
    "IAM": "Identity and Access Management",
    "VPC": "Virtual Private Cloud",
    "RDS": "Relational Database Service",
    "EC2": "Elastic Compute Cloud",
    "S3": "Simple Storage Service",
    "IaC": "Infrastructure as Code",
}

# Stop phrases: common project-related phrases to remove during cleaning
STOP_PHRASES = [
    "Construction Management",
    "Transition to Operations",
    "Project Management",
    "Phase Management",
    "Task Management",
    "Quality Management",
    "Risk Management",
    "Scope Management",
    "Schedule Management",
    "Cost Management",
    "Resource Management",
]

# Stop words: common English words to filter. Extends
# sklearn.feature_extraction.text.ENGLISH_STOP_WORDS.
STOP_WORDS = [
    "a",
    "about",
    "after",
    "again",
    "against",
    "all",
    "am",
    "an",
    "and",
    "any",
    "are",
    "as",
    "at",
    "be",
    "because",
    "been",
    "before",
    "being",
    "below",
    "between",
    "both",
    "but",
    "by",
    "can",
    "could",
    "did",
    "do",
    "does",
    "doing",
    "down",
    "during",
    "each",
    "few",
    "for",
    "from",
    "further",
    "had",
    "has",
    "have",
    "having",
    "he",
    "her",
    "here",
    "hers",
    "herself",
    "him",
    "himself",
    "his",
    "how",
    "i",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "itself",
    "just",
    "me",
    "might",
    "more",
    "most",
    "must",
    "my",
    "myself",
    "no",
    "nor",
    "not",
    "of",
    "off",
    "on",
    "once",
    "only",
    "or",
    "other",
    "our",
    "ours",
    "ourselves",
    "out",
    "over",
    "own",
    "same",
    "she",
    "should",
    "so",
    "some",
    "such",
    "than",
    "that",
    "the",
    "their",
    "theirs",
    "them",
    "themselves",
    "then",
    "there",
    "these",
    "they",
    "this",
    "those",
    "through",
    "to",
    "too",
    "under",
    "until",
    "up",
    "very",
    "was",
    "we",
    "were",
    "what",
    "when",
    "where",
    "which",
    "while",
    "who",
    "whom",
    "why",
    "will",
    "with",
    "you",
    "your",
    "yours",
    "yourself",
    "yourselves",
    # Project-specific stop words (domain)
    "project",
    "phase",
    "task",
    "activity",
    "deliverable",
    "workstream",
]

# Domain-specific text replacements (exact match or pattern)
# Used in clean_text() function to normalize domain terminology
DOMAIN_REPLACEMENTS = {
    r"-[Cc]osts|-[Cc]osts\b": " costs",  # Normalize costs variations
    # Normalize commissioning spelling
    r"[Cc]ommisioning|[Cc]omissioning": "commissioning",
    r"cd-": "critical decision ",  # Expand cd- prefix
}

# Project name patterns (used to remove project context from WBS titles)
PROJECT_NAME_PATTERNS = [
    r"Project [A-Za-z0-9]+",
    r"Program [A-Za-z0-9]+",
    r"Initiative [A-Za-z0-9]+",
]


def transform(df: pl.DataFrame) -> pl.DataFrame:
    lf = df.lazy()
    cols = lf.collect_schema().names()
    level_cols = [c for c in cols if c.startswith("level_")]

    # everything(): cast to string, blank literal "0", normalize text, squish
    lf = (
        lf.with_columns([pl.col(c).cast(pl.Utf8).alias(c) for c in cols])
        .with_columns([pl.col(c).str.replace_all(r"^0$", "").alias(c) for c in cols])
        .with_columns(
            [
                pl.col(c)
                .str.replace_all(r"-Costs|-costs", " costs")
                .str.replace_all(r"Commisioning|commisioning", "commissioning")
                .str.replace_all(r"\s+", " ")
                .str.strip_chars()
                .alias(c)
                for c in cols
            ]
        )
        .with_columns(
            [
                pl.col(c).str.to_lowercase().str.replace(r"^((\d+)*\.*)*", "").alias(c)
                for c in level_cols
            ]
        )
        .with_columns(
            [
                pl.col("wbs")
                .str.replace(r"^(\d)\.", r"0$1.")
                .str.replace(r"^(\d)$", r"0$1")
                .str.replace_all("00000000000001", ""),
                pl.col("parent_wbs")
                .str.replace(r"^(\d)\.", r"0$1.")
                .str.replace(r"^(\d)$", r"0$1")
                .str.replace_all("00000000000001", ""),
            ]
        )
    )
    return lf.unique().collect()


def concatenate_data(
    text_data: pl.DataFrame,
    text_field: str = "wbs_title",
    level_field: str = "wbs_level",
    starting_level: int = 2,
    with_dates: bool = True,
) -> pl.DataFrame:
    """
    Docstring explaining this function's functionality will go here.
    """
    ## Create temporary duplicate levels column and filter
    # Add temporary columns for processing: "temp_level" and "original_title"
    text_data = (
        (
            text_data.with_columns(
                temp_level=pl.col(level_field)
                .alias("temp_level")
                .cast(pl.Int64)
                .alias("temp_level"),  # Temporary level column
                original_title=pl.col(text_field).alias(
                    "original_title"
                ),  # Original title column
            )
        )
        .filter(pl.col(level_field).is_not_null())
        .filter(pl.col(level_field).cast(pl.Int64) >= starting_level)
    )

    new_names = [name.replace("\n", "") for name in text_data.columns]
    text_data = text_data.rename(dict(zip(text_data.columns, new_names)))

    # Columns to add WBS level prefix to
    cols_to_prefix = [
        str(i)
        for i in range(
            starting_level, text_data[level_field].cast(pl.Int64()).max() + 1
        )
    ]
    prefix = "wbs_level_"  # Prefix for WBS level columns

    # Determine index columns based on whether dates are included
    if with_dates:
        index_cols = [
            "original_title",
            "wbs",
            "period_date",
        ]  # Include "period_date" if dates are present
    else:
        index_cols = [
            "original_title",
            "wbs",
        ]  # Use only "original_title" and wbs as the index

    # Further cleaning
    # Remove numeric strings with 3 or more digits from the text field
    # Pivot the data based on "temp_level" and "text_field" values
    pivoted_data = (
        text_data.with_columns(
            pl.col(text_field)
            .str.replace(r"[0-9]{10,}", "")
            .alias(text_field)  # Remove numeric strings
        )
        .pivot(
            on="temp_level",  # Pivot based on "temp_level"
            values=text_field,  # Use "text_field" values for pivoting
            # index = "original_title",  # Index columns for pivoting
            aggregate_function="first",  # Aggregate function for pivoting
            maintain_order=True,  # Maintain order of rows
            sort_columns=False,  # Do not sort columns
        )
        .unique(subset=index_cols, maintain_order=True)
    )

    text_data = text_data.join(pivoted_data, on=index_cols, how="inner").drop(
        pl.selectors.contains("_right")
    )
    # # Rename columns to include the WBS level prefix
    text_data = text_data.rename(
        {col: f"{prefix}{col}" for col in cols_to_prefix if col in text_data.columns}
    )
    # Create a list of column names
    col_names = text_data.columns

    # Count the number of new columns added with the WBS level prefix
    new_cols = [col for col in col_names if r"wbs_level_" in col]

    # Set the start and end index for iterating over columns
    start_col = starting_level + 1
    start = text_data.get_column_index(
        f"wbs_level_{start_col}"
    )  # Start index for WBS level columns
    # print(start)
    # print(text_data[level_field].cast(pl.Int64()).max())
    end = len(text_data.columns)  # End index for columns

    # Replace NAs with blanks if an entry exists in the previous column
    for i in range(end - 1, start, -1):  # Iterate from the last column to the start
        cur_col = text_data.columns[i]  # Current column
        prev_col = text_data.columns[i - 1]  # Previous column

        text_data = text_data.with_columns(
            pl.when(
                pl.col(cur_col).is_null()  # Check if current column is null
                & pl.col(prev_col).is_not_null()  # Check if previous column is not null
            )
            .then(pl.lit(" "))  # Replace null values with a blank space
            .otherwise(pl.col(cur_col))  # Otherwise, keep the original value
            .alias(cur_col)  # Update the current column
        )

    # Replace NAs with "--" if certain conditions are met
    for i in range(start, end):  # Iterate from the start column to the end
        cur_col = text_data.columns[i]  # Current column
        prev_col = text_data.columns[i - 1]  # Previous column
        text_data = text_data.with_columns(
            pl.when(
                pl.col(cur_col).is_null()  # Check if current column is null
                & (
                    pl.lit(i) > pl.col(level_field).cast(pl.Int64)
                )  # Check if column index exceeds level
                & pl.col(prev_col).is_not_null()  # Check if previous column is not null
            )
            .then(pl.lit("--"))  # Replace null values with "--"
            .otherwise(pl.col(cur_col))  # Otherwise, keep the original value
            .alias(cur_col)  # Update the current column
        )

    # Final preparation
    # Fill null values using forward fill strategy
    text_data = text_data.fill_null(strategy="forward")

    # # Replace dashes in new columns
    text_data = text_data.with_columns(
        [
            pl.col(col).str.replace("--", " ")
            for col in new_cols  # Replace "--" with a blank space
        ]
    )
    # Concatenate new columns into a single text field
    text_data = text_data.with_columns(
        pl.concat_str(
            new_cols,
            separator=" | ",  # Concatenate columns with " | " separator
        ).alias(text_field)  # Update the text field
    )

    # Perform regex replacements for cleaning
    text_data = text_data.with_columns(
        pl.col(text_field).str.replace_all(r"\s*\|\s*\|", "")  # Remove empty pipes
    )
    text_data = text_data.with_columns(
        pl.col(text_field)
        .str.replace_all(r"\|\s*$", "")
        .str.strip_chars()  # Remove trailing pipes and whitespace
    )
    # Return the processed DataFrame
    return text_data


def clean_stitch(
    text_data: pl.DataFrame,
    text_field: str,
    abbreviations: pl.DataFrame,
    stop_words: pl.DataFrame,
    stop_phrases: pl.DataFrame,
    project_descriptions: pl.DataFrame,
):
    # 1) Initial Cleaning
    text_data = (
        text_data.with_columns(
            pl.col(text_field)
            .str.replace_many(
                patterns=["Construction Management", "Transition to Operations", "cd-"],
                replace_with=["CM", "TTO", "Critical Decision "],
            )
            .alias(text_field)
        )
        .with_row_index(name="id", offset=1)  # keep this index until the final return
        .with_columns(
            pl.col(text_field).str.replace_all(r"[()]", " ").alias(text_field)
        )
    )

    # 2) Case-sensitive acronym expansion (whole words; many per string)

    # Build your mapping from the abbreviations table as before
    abbr = abbreviations.select(
        pl.col("abbreviation").cast(pl.Utf8),
        pl.col("definition").cast(pl.Utf8),
    ).drop_nulls(subset=["abbreviation", "definition"])
    mapping = dict(zip(abbr["abbreviation"].to_list(), abbr["definition"].to_list()))

    # Start with the target column as an expression
    expr = pl.col(text_field)

    # Apply replacements longest-first to avoid partial matches
    for k, v in sorted(mapping.items(), key=lambda kv: len(kv[0]), reverse=True):
        pattern = rf"\b({re.escape(k)})\b"  # whole-word, case-sensitive+
        expr = expr.str.replace_all(pattern, v)

    # Write the updated column back
    text_data = text_data.with_columns(expr.alias(text_field))

    # 3) Remove project names, stop phrases, THEN stop words (order matters)
    project_names = (
        project_descriptions["project_name"].drop_nulls().to_list()
        if "project_name" in project_descriptions.columns
        else []
    )
    phrases_list = (
        stop_phrases.get_column(stop_phrases.columns[0]).drop_nulls().to_list()
        if len(stop_phrases.columns) > 0
        else []
    )
    words_list = (
        stop_words.get_column(stop_words.columns[0]).drop_nulls().to_list()
        if len(stop_words.columns) > 0
        else []
    )

    if project_names:
        alt_proj = "|".join(map(re.escape, project_names))
        text_data = text_data.with_columns(
            pl.col(text_field).str.replace_all(rf"\b({alt_proj})\b", "")
        )
    if phrases_list:
        alt_phr = "|".join(map(re.escape, phrases_list))
        text_data = text_data.with_columns(
            pl.col(text_field).str.replace_all(rf"\b({alt_phr})\b", "")
        )
    if words_list:
        alt_wrd = "|".join(map(re.escape, words_list))
        text_data = text_data.with_columns(
            pl.col(text_field).str.replace_all(rf"\b({alt_wrd})\b", "")
        )

    # 4) Lowercase and dedupe (preserve order)
    tidy_text = (
        text_data.with_columns(
            pl.col(text_field).str.to_lowercase().alias(text_field),
            (
                pl.selectors.contains("level_") & pl.selectors.string()
            ).str.to_lowercase(),
        ).unique(maintain_order=True)  # preserves first-appearance order
    )

    # 5) Join project descriptions & dedupe (preserve order)
    #    IMPORTANT: keep 'id' through the join and dedupe, then drop it later.
    stitched_data = (
        tidy_text.with_columns(pl.col("parsid").cast(pl.Int64))
        .join(
            project_descriptions, on=["parsid"], how="left"
        )  # left join keeps left's order
        .unique(subset=[text_field, "parsid"], keep="first", maintain_order=True)
    )

    # 6) Normalize blanks, drop nulls, clean punctuation
    stitched_data = (
        stitched_data.with_columns(pl.col(text_field).replace(" ", None))
        .drop_nulls(subset=text_field)
        .with_columns(pl.col(text_field).cast(str).str.to_lowercase())
        .with_columns(
            pl.col(text_field)
            .str.replace_all(r"\s+", " ", literal=True)
            .str.strip_chars()
            .str.replace_all(r"[!-/:-@\[-`{-~]", " ")
        )
    )

    # Optional number removal:
    stitched_data = stitched_data.with_columns(
        pl.col(text_field).str.replace_all(r"\s*\d{3,}\s*", " ").alias(text_field)
    )

    # 7) Fill NaNs/nulls and normalize zeros
    stitched_data = (
        stitched_data.fill_nan("")
        .fill_null("")
        .with_columns(
            [
                pl.col(col).cast(str).str.replace(r"^0$", " ").alias(col)
                for col in stitched_data.columns
            ]
        )
        .with_columns(
            [
                pl.col(col).cast(str).str.replace(r"^ $", "").alias(col)
                for col in stitched_data.columns
            ]
        )
    )

    # 8) Final whitespace collapse (regex: \s+ → " ")
    stitched_data = stitched_data.with_columns(
        pl.col(text_field)
        .str.replace_all(r"\s+", " ")  # IMPORTANT: regex; do NOT set literal=True
        .str.strip_chars()  # trim edges just in case
    )

    # 9) Normalize 'level_2' if present
    if "level_2" in stitched_data.columns:
        stitched_data = stitched_data.with_columns(
            pl.col("level_2").replace(" ", None)
        ).drop_nulls(subset="level_2")
    if "wbs_level_2" in stitched_data.columns:
        stitched_data = stitched_data.with_columns(
            pl.col("wbs_level_2").replace(" ", None)
        ).drop_nulls(subset="wbs_level_2")

    # FINAL: Reassert original row order and drop the helper index
    stitched_data = stitched_data.sort("id").drop("id")
    # print(stitched_data)
    return stitched_data


def clean_data(
    dataframes,
    text_field="wbs_title",
    file_type="uploaded",
    level_field="wbs_level",
    starting_level=2,
    with_dates=False,
):
    """
    This function cleans a dataframe containing both the training labels if
    included, and the WBS descriptions (denoted by "level_").
    The input of this function is a set of polars dataframes.
    The output of this function is a polars dataframe.
    """

    # Load supporting files
    # project_descriptions, stop_phrases, stop_words, abbreviatons = (
    #     clean_supporting_files(dataframes)
    # )  # reconcile this

    # Set data to clean
    if file_type == "training":  # be careful with this in production
        df = dataframes["silver_cleaned_concat_sample"]
        df = df.unique(subset=[text_field, "parsid"])
    elif file_type == "inference":
        df = dataframes["silver_cleaned_concat_spae"]
        df = df.unique()
    else:
        df = dataframes["uploaded_data"]  # placeholder for uploaded_data
        # Concatenate
        df = concatenate_data(
            df,
            text_field=text_field,
            level_field=level_field,
            starting_level=starting_level,
            with_dates=with_dates,
        )
        # Clean and Stitch
        df = clean_stitch(
            text_data=df,
            text_field=text_field,
            abbreviations=dataframes["bronze_abbreviations"],
            stop_words=dataframes["silver_stop_words"],
            stop_phrases=dataframes["bronze_stop_phrases"],
            project_descriptions=dataframes["silver_project_descriptions"],
        )
        if with_dates:
            df = df.unique(subset=[text_field, "period_date"])
        else:
            df = df.unique(subset=[text_field])
    return df


def normalize_wbs(series):
    return (
        series.astype("string")
        .str.replace(r"^(\d)(?=\.|$)", r"0\1", regex=True)
        .str.lower()
        .str.strip()
    )


def normalize_title(series):
    return series.astype("string").str.lower().str.strip()


def clean_wbs(series):
    return (
        series.astype("string")
        .str.replace(r"^(\d)(?=\.|$)", r"0\1", regex=True)
        .str.replace("00000000000001", "", regex=False)
    )


def clean_text(series):
    return (
        series.astype("string")
        .str.replace(r"-Costs|-costs", " costs", regex=True)
        .str.replace(
            r"Commisioning|commisioning",
            "commissioning",
            regex=True,
        )
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )


def text_cleaning_function(text):
    return re.sub(r"[^a-zA-Z0-9\s]", "", text).lower()


def input_reshaper(X):
    # return [X[:,:-10].reshape(X.shape[0],28,28,1), X[:,-10:]]
    return X
