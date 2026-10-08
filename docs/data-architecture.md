# MENYA NEZA AI — Data Architecture

## Data Flow

RAW DATA
↓
DATA VALIDATION
↓
CLEANING
↓
STANDARDIZATION
↓
PROCESSED DATA
↓
FEATURE ENGINEERING
↓
ANALYSIS / MACHINE LEARNING
↓
RISK SIGNAL
↓
WARNING
↓
EXPLANATION
↓
USER INTERFACE

## Raw Data

Original datasets are stored in:

data/raw/

Raw data should be preserved as closely as possible to the original
source.

Raw datasets should not be silently modified.

## Data Validation

Before analysis, the pipeline should check:

- Missing values
- Duplicate records
- Invalid values
- Incorrect data types
- Geographic inconsistencies
- Date inconsistencies
- Unexpected ranges
- Unit inconsistencies

## Cleaning and Standardization

Validated data is cleaned and standardized before being used for
analysis.

Important standardization areas include:

- Geographic identifiers
- Dates
- Units
- Variable names
- Missing-value representation
- Categorical values

## Processed Data

Cleaned datasets are stored in:

data/processed/

Processed data should remain traceable to its original source.

## Feature Engineering

Features may be created from processed data for statistical analysis
and machine-learning models.

Examples include:

- Historical averages
- Moving averages
- Percentage changes
- Seasonal deviations
- Z-scores
- Rainfall anomalies
- Production anomalies
- Historical loss rates

## Analysis and Machine Learning

Analytical methods may include:

- Descriptive statistics
- Historical baselines
- Anomaly detection
- Regression
- Classification
- Time-series analysis
- Forecasting where justified
- Machine-learning models where appropriate

The selected method must depend on the available data and the
specific problem being analyzed.

## Risk Signals

Analytical results are converted into structured risk or early-warning
signals.

A signal should contain enough information to explain:

- Location
- Indicator
- Observation period
- Baseline
- Change or anomaly
- Signal level
- Confidence
- Supporting evidence

## Warning

Warnings communicate elevated signals in understandable language.

The system must distinguish between:

- Normal conditions
- Watch conditions
- High-concern conditions

Warnings are indicators and do not replace official government
warnings or emergency authorities.

## Explanation

Every important warning should provide a "WHY THIS WARNING?" explanation.

The explanation must be generated from verified analytical results.

An explanation must not invent evidence, statistics, events, or causes.

## Traceability

The project should be able to trace an important warning back through:

WARNING
→ RISK SIGNAL
→ MODEL / ANALYSIS
→ FEATURES
→ PROCESSED DATA
→ ORIGINAL DATASET
→ SOURCE

## Data Integrity Rule

Synthetic, fabricated, or unverified data must never be presented as
actual Rwanda observations.

Synthetic data may only be used for clearly labelled software testing
or development purposes.
