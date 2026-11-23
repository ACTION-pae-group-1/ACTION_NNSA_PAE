"""Verbatim WBS Modeling functions used by the PARS WBS pipeline (ML path).

Provenance
----------
Source: WBS Modeling repository, file ``functions.py``, git revision e41fba1.
Every function and class below is copied verbatim from that file; the
"Source:" comment above each block gives its exact source line range. The
generator used to copy them is recorded in docs/wbs_model_mcp_parity.md.

Environment adaptations (the ONLY changes; no algorithm body is edited)
-----------------------------------------------------------------------
1. Module-level imports of the neural-network stack (tensorflow, keras,
   keras_tuner, ray, scikeras) and the TF numpy-behaviour toggle are not
   present. They are used only by the neural-network path (train_model,
   tune_model, model, save_model, TextVectorizer), which is NOT ported
   (status "blocked" in docs/wbs_model_mcp_parity.md).
2. Source globals read from environment variables (INPUTS_DIR, OUTPUT_DIR,
   PROJECT_PATH) and the hard-coded Windows log path are replaced by the
   globals below, which the caller sets with configure_paths(). Functions
   read ``input_dir``, ``output_dir`` and ``duck_db`` exactly as the source does.
3. Functions that were not on any live source path are not copied (see the
   parity inventory for each excluded name and the reason).
4. Table identifiers are local names (for example silver_cleaned_concat_sample). The
   source database's legacy names differ by a suffix that is set privately through
   PARS_LEGACY_TABLE_SUFFIX. pipeline.SOURCE_TABLE_NAMES maps the legacy names of the
   source database onto these local names. Only identifier
   strings changed; no statement logic changed.
"""

# Verbatim copies of WBS Modeling source: long lines are kept as-is (E501 off).
# ruff: noqa: E501

import os
import re

import duckdb
import hiclass
import joblib
import polars as pl
from hiclass.metrics import f1
from sklearn.preprocessing import LabelEncoder
from skmultilearn.model_selection import IterativeStratification

# Source: functions.py L52 (``seed = 1337``). Not referenced by any live function.
seed = 1337

# Set by configure_paths(); the source reads these from environment variables.
input_dir = None
output_dir = None
duck_db = "mock_pars_full.duckdb"


def configure_paths(input_path, output_path, duck_db_name):
    """Bind the globals the source functions read.

    input_path  : directory that holds the database and receives stratify()/encode_labels() CSV/pickle side outputs
    output_path : directory that receives encode_labels() label_encoder.joblib and save_results_to_db()
    duck_db_name: database file name looked up inside input_path by load_tables()
    """
    global input_dir, output_dir, duck_db
    input_dir = str(input_path)
    output_dir = str(output_path)
    duck_db = str(duck_db_name)


# Source: functions.py L62-78 (verbatim)
def load_tables(input_dir=input_dir, duck_db=duck_db):
    db_path = os.path.abspath(os.path.join(input_dir, duck_db))
    dataframes = {}  # Dictionary to store DataFrames by table name
    conn = duckdb.connect(db_path)
    print(f"Connecting to database at: {db_path}")
    table_names = {
        "silver_cleaned_concat_sample",
        "silver_cleaned_concat_spae",
        "silver_corrections",
        "bronze_abbreviations",
        "bronze_stop_phrases",
        "silver_stop_words",
        "silver_project_descriptions",
    }
    for table in table_names:
        # # Convert to Polars DataFrame
        polars_df = conn.execute(f"SELECT * FROM {table}").pl()
        # Store the DataFrame in the dictionary
        dataframes[table] = polars_df
    conn.close()
    print("Tables loaded")
    return dataframes


# Source: functions.py L166-195 (verbatim)
def transform(df: pl.DataFrame) -> pl.DataFrame:
    lf = df.lazy()
    cols = lf.columns
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


# Source: functions.py L197-320 (verbatim)
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
    # Deviation from source: keep each project's rows contiguous. The sort is stable,
    # so each project's own row order (its tree order) is unchanged.
    if "parsid" in text_data.columns:
        text_data = text_data.sort("parsid", maintain_order=True)
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
        print(cur_col)
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
    print(new_cols)
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


# Source: functions.py L323-455 (verbatim)
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


# Source: functions.py L459-487 (verbatim)
def clean_data(
    dataframes,
    text_field="wbs_title",
    file_type="uploaded",
    level_field="wbs_level",
    starting_level=2,
    with_dates=False,
):
    """
    This function cleans a dataframe containing both the training labels if included, and the WBS descriptions (denoted by "level_").
    The input of this function is a set of polars dataframes.
    The output of this function is a polars dataframe.
    """

    # Load supporting files
    # project_descriptions, stop_phrases, stop_words, abbreviatons = clean_supporting_files(dataframes) # reconcile this

    # Set data to clean
    if file_type == "training":  # be careful with this in production
        df = dataframes["silver_cleaned_concat_sample"]
        # maintain_order: stable row order across runs (deviation from source)
        df = df.unique(subset=[text_field, "parsid"], maintain_order=True)
    elif file_type == "inference":
        df = dataframes["silver_cleaned_concat_spae"]
        df = df.unique(maintain_order=True)
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
            df = df.unique(subset=[text_field, "period_date"], maintain_order=True)
        else:
            df = df.unique(subset=[text_field], maintain_order=True)
    return df


# Source: functions.py L489-524 (verbatim)
class MultiColumnLabelEncoder:
    def __init__(self, columns=None):
        self.columns = columns  # array of column names to encode

    def fit(self, X, y=None):
        self.encoders = {}
        columns = X.columns if self.columns is None else self.columns
        for col in columns:
            self.encoders[col] = LabelEncoder().fit(X.get_column(col))
        return self

    def transform(self, X):
        output = X.clone()
        columns = X.columns if self.columns is None else self.columns
        for col in columns:
            transformed = pl.Series(self.encoders[col].transform(X.get_column(col)))
            output = output.with_columns(transformed.alias(col))
        return output

    def fit_transform(self, X, y=None):
        return self.fit(X, y).transform(X)

    def inverse_transform(self, X):
        output = X.clone()
        columns = X.columns if self.columns is None else self.columns
        for col in columns:
            # print(f"Level: {col}")
            transformed = pl.Series(
                self.encoders[col].inverse_transform(X.get_column(col)).astype(str)
            )
            # print(f"Column: {col}, Transformed: {transformed}")
            output = output.with_columns(transformed.alias(col))
        return output


# Source: functions.py L528-535 (verbatim)
def encode_labels(input_dir, training_data, hierarchies):
    label_encoder = MultiColumnLabelEncoder(columns=hierarchies)
    hiclass_labels = label_encoder.fit_transform(training_data.select(hierarchies))
    joblib.dump(label_encoder, output_dir + "/label_encoder.joblib")
    hiclass_target_names = label_encoder.inverse_transform(hiclass_labels)
    hiclass_labels.write_csv(input_dir + "/hiclass_labels_caef2.csv")
    hiclass_target_names.write_csv(input_dir + "/hiclass_target_names_caef2.csv")
    return (hiclass_labels, hiclass_target_names)


# Source: functions.py L539-556 (verbatim)
def stratify(cleaned_data, hiclass_labels, text_field, test_size=0.2):
    stratifier = IterativeStratification(
        n_splits=2, order=2, sample_distribution_per_fold=[test_size, 1.0 - test_size]
    )
    train_indices, test_indices = next(
        stratifier.split(cleaned_data.get_column(text_field), hiclass_labels)
    )
    hiclass_labels = hiclass_labels.to_numpy()
    word_array = cleaned_data.get_column(text_field).to_numpy()

    # get train and test data tests
    X_train_is = word_array[train_indices]  # 1819
    X_test_is = word_array[test_indices]

    y_train_is = hiclass_labels[train_indices]  # 1819
    y_test_is = hiclass_labels[test_indices]
    joblib.dump(X_train_is, input_dir + "/X_train.pkl")
    joblib.dump(y_train_is, input_dir + "/y_train.pkl")
    joblib.dump(X_test_is, input_dir + "/X_test.pkl")
    joblib.dump(y_test_is, input_dir + "/y_test.pkl")

    return (X_train_is, X_test_is, y_train_is, y_test_is)


# Source: functions.py L677-684 (verbatim)
def f1_scorer(clf, X_train, y_train):
    y_pred = clf.predict(X_train)
    y_pred = y_pred.astype(int)
    precision = hiclass.metrics.precision(y_train, y_pred)
    if precision > 0:
        f1 = hiclass.metrics.f1(y_train, y_pred)
    else:
        f1 = 0
    return f1


# Source: functions.py L852-855 (verbatim)
def safe_f1(y_true, y_pred):
    score = f1(y_true, y_pred)
    # Handle None or NaN (NaN != NaN)
    return 0.0 if score is None or score != score else score


# Source: functions.py L857-873 (verbatim)
def batch_predict(data, model, batch_size=5000):
    predictions = []

    # Loop through your data and process in batches
    for i in range(0, len(data), batch_size):
        batch = data[i : i + batch_size]
        try:
            # Make predictions for the current batch
            preds = model.predict(batch)
            preds_int = preds.astype(int)
            predictions.extend(preds_int)  # Add predictions to the list
        except Exception as e:
            # Record or handle the error
            error_message = (
                f"Error during prediction for batch starting at index {i}: {str(e)}"
            )
            predictions.append(
                error_message
            )  # Append error message instead of predictions

    return predictions


# Source: functions.py L876-896 (verbatim)
def save_results_to_db(results, duck_db=duck_db):
    db_path = os.path.abspath(os.path.join(output_dir, duck_db))
    con = duckdb.connect(db_path)
    # Create dynamic list of columns if sample data changes over time
    col_defs = ",\n    ".join([f"{col} varchar" for col in results.columns])

    # Write to duckdb
    con.execute(
        f"""
        CREATE OR REPLACE TABLE results (
        {col_defs}
        )
        TRUNCATE TABLE results;
        INSERT INTO results
        SELECT *
        FROM results;
        """
    )

    con.close()
    print(f"Saved results to database at {db_path}")
