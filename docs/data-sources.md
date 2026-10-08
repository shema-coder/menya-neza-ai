# MENYA NEZA AI — Data Sources

## Purpose

This document records the verified data sources considered for
MENYA NEZA AI.

The project prioritizes official Rwanda data, especially data from
the National Institute of Statistics of Rwanda (NISR), together with
other reliable public sources where appropriate.

## Priority

### Primary

- NISR
- Official Rwanda government institutions
- Official administrative data

### Secondary

- Reputable public climate and weather sources
- Reputable disaster-related sources
- Reputable agriculture and food datasets
- Geographic and geospatial public datasets

## Data Selection Principles

A dataset should be evaluated for:

1. Reliability
2. Relevance
3. Geographic coverage
4. Time coverage
5. Frequency
6. Variables available
7. Accessibility
8. License or usage conditions
9. Data quality
10. Limitations

## Dataset Registry

All datasets used or considered by MENYA NEZA AI should be recorded
in:

`data/metadata/dataset_registry.csv`

## Important Rule

MENYA NEZA AI must not present invented data as real Rwanda data.

Every important indicator displayed to users should be traceable to
a documented source.

## Domains

The initial data architecture covers:

- Agriculture
- Food
- Disasters

## Geographic Standardization

Where possible, datasets should be aligned using common Rwanda
administrative geographic references:

- Province
- District
- Sector

Coordinates and geographic boundaries may also be used where available.

## Time Standardization

Datasets may have different frequencies:

- Daily
- Weekly
- Monthly
- Seasonal
- Annual

The preprocessing pipeline must document how observations are
aggregated or aligned across different time scales.

## Data Limitations

Missing values, different geographic boundaries, changes in collection
methods, inconsistent time periods, measurement uncertainty, and other
quality issues must be documented before using a dataset for modelling.
