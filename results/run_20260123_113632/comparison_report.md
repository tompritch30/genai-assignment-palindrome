# Extraction Run Report

**Run Timestamp**: 20260123_113632

**Total Cases Processed**: 15

## Summary Statistics

- **Successful Extractions**: 15/15
- **Average Extraction Time**: 21.8s
- **Average Sources Found**: 3.0
- **Average Completeness**: 92%

_Completeness is the fraction of required fields (from the knowledge base) that have a non-empty value. A lower completeness score often indicates the narrative did not state certain required details, not necessarily that the model made a mistake._

## Aggregate Accuracy

- **Field Accuracy**: 93.9% (229/244 fields)
  - _String matching alone: 79.9% (195/244)_
  - _LLM semantic corrections: +34 fields_
- **Source Matching Rate**: 97.7% (43/44 sources)
- **Fields Missing (null when expected)**: 12
- **Fields Incorrect (wrong value)**: 3
- **Unmatched Expected Sources**: 1 (no matching actual source found)

### Accuracy by Source Type

_Note: Accuracy percentages reflect final results after LLM semantic evaluation._

| Source Type | Sources | Accuracy | Matched | Missing | Incorrect |
|-------------|---------|----------|---------|---------|-----------|
| business_dividends | 2 | 90% | 9/10 | 0 | 1 |
| business_income | 2 | 67% | 6/9 | 3 | 0 |
| divorce_settlement | 1 | 100% | 5/5 | 0 | 0 |
| employment_income | 14 | 88% | 59/67 | 6 | 2 |
| gift | 4 | 91% | 21/23 | 2 | 0 |
| inheritance | 7 | 100% | 40/40 | 0 | 0 |
| insurance_payout | 1 | 100% | 5/5 | 0 | 0 |
| sale_of_asset | 1 | 100% | 4/4 | 0 | 0 |
| sale_of_business | 4 | 100% | 28/28 | 0 | 0 |
| sale_of_property | 8 | 98% | 52/53 | 1 | 0 |

### Missing Sources (Not Extracted)

- `business_income`: 1 instances

### Extra Sources (Hallucinated)

- `employment_income`: 1 instances
- `sale_of_business`: 1 instances

## Case-by-Case Results

### case_01_employment_simple

**Status**: ✅ SUCCESS
**Extraction Time**: 9.7s
**Sources Found**: 2
**Completeness Score**: 100%

**Comparison vs Expected Output**:

- Metadata Accuracy: 100% (4/4 fields)
- Sources: 2/2 matched
  - Field Accuracy by Source:
    - `employment_income`: 100% (6/6 fields)
    - `employment_income`: 100% (5/5 fields)

### case_02_property_sale

**Status**: ✅ SUCCESS
**Extraction Time**: 20.5s
**Sources Found**: 2
**Completeness Score**: 67%

**Comparison vs Expected Output**:

- Metadata Accuracy: 100% (4/4 fields)
- Sources: 2/2 matched
  - Field Accuracy by Source:
    - `sale_of_property`: 100% (7/7 fields)
    - `employment_income`: 100% (1/1 fields)
      - Extra (unexpected):
        - `country_of_employment`: Extracted `United Kingdom (London)` (expected null)

### case_03_employment_property

**Status**: ✅ SUCCESS
**Extraction Time**: 14.8s
**Sources Found**: 3
**Completeness Score**: 100%

**Comparison vs Expected Output**:

- Metadata Accuracy: 100% (4/4 fields)
- Sources: 3/3 matched
  - Field Accuracy by Source:
    - `sale_of_property`: 100% (7/7 fields)
    - `employment_income`: 83% (5/6 fields)
      - Missing:
        - `country_of_employment`: Expected `United Kingdom (London office)`, Got `None`
    - `employment_income`: 83% (5/6 fields)
      - Missing:
        - `country_of_employment`: Expected `United Kingdom`, Got `None`

### case_04_inheritance_partial

**Status**: ✅ SUCCESS
**Extraction Time**: 5.0s
**Sources Found**: 1
**Completeness Score**: 100%

**Comparison vs Expected Output**:

- Metadata Accuracy: 100% (4/4 fields)
- Sources: 1/1 matched
  - Field Accuracy by Source:
    - `inheritance`: 100% (6/6 fields)

### case_05_business_income_dividends

**Status**: ✅ SUCCESS
**Extraction Time**: 23.1s
**Sources Found**: 3
**Completeness Score**: 83%

**Comparison vs Expected Output**:

- Metadata Accuracy: 100% (4/4 fields)
- Sources: 3/3 matched
  - Field Accuracy by Source:
    - `business_income`: 100% (6/6 fields)
    - `employment_income`: 100% (2/2 fields)
      - Extra (unexpected):
        - `job_title`: Extracted `Managing Director` (expected null)
        - `annual_compensation`: Extracted `£360,000` (expected null)
        - `country_of_employment`: Extracted `United Kingdom` (expected null)
    - `business_dividends`: 80% (4/5 fields)
      - Incorrect:
        - `period_received`: Expected `Ongoing since founding; last 5 years specifically mentioned`, Got `Over the past five years`

### case_06_multigenerational_gift

**Status**: ✅ SUCCESS
**Extraction Time**: 4.8s
**Sources Found**: 1
**Completeness Score**: 100%

**Comparison vs Expected Output**:

- Metadata Accuracy: 100% (4/4 fields)
- Sources: 1/1 matched
  - Field Accuracy by Source:
    - `gift`: 100% (6/6 fields)

### case_07_multiple_sources_hnw

**Status**: ✅ SUCCESS
**Extraction Time**: 24.9s
**Sources Found**: 7
**Completeness Score**: 91%

**Comparison vs Expected Output**:

- Metadata Accuracy: 100% (4/4 fields)
- Sources: 6/6 matched
  - Extra sources: employment_income
  - Field Accuracy by Source:
    - `sale_of_property`: 100% (7/7 fields)
    - `sale_of_property`: 100% (7/7 fields)
    - `sale_of_property`: 100% (4/4 fields)
    - `sale_of_business`: 100% (7/7 fields)
    - `employment_income`: 80% (4/5 fields)
      - Missing:
        - `employment_start_date`: Expected `1985 (joined as Associate)`, Got `None`
    - `inheritance`: 100% (6/6 fields)

### case_08_joint_account

**Status**: ✅ SUCCESS
**Extraction Time**: 15.7s
**Sources Found**: 3
**Completeness Score**: 100%

**Comparison vs Expected Output**:

- Metadata Accuracy: 100% (4/4 fields)
- Sources: 3/4 matched
  - Missing sources: business_income
  - Field Accuracy by Source:
    - `business_income`: 0% (0/3 fields)
      - Source missing: Expected `Private practice income` but no matching extracted source was found
      - Missing:
        - `business_name`: Expected `London Heart Clinic`, Got `None`
        - `nature_of_business`: Expected `Private medical practice (cardiology)`, Got `None`
        - `annual_income_from_business`: Expected `£80,000`, Got `None`
    - `sale_of_property`: 100% (7/7 fields)
    - `employment_income`: 100% (6/6 fields)
    - `inheritance`: 100% (6/6 fields)

### case_09_nested_inheritance_dividends

**Status**: ✅ SUCCESS
**Extraction Time**: 22.0s
**Sources Found**: 2
**Completeness Score**: 100%

**Comparison vs Expected Output**:

- Metadata Accuracy: 100% (4/4 fields)
- Sources: 2/2 matched
  - Field Accuracy by Source:
    - `inheritance`: 100% (6/6 fields)
    - `business_dividends`: 100% (5/5 fields)

### case_10_international_complexity

**Status**: ✅ SUCCESS
**Extraction Time**: 46.1s
**Sources Found**: 3
**Completeness Score**: 100%

**Comparison vs Expected Output**:

- Metadata Accuracy: 100% (4/4 fields)
- Sources: 3/3 matched
  - Field Accuracy by Source:
    - `sale_of_property`: 86% (6/7 fields)
      - Missing:
        - `sale_proceeds`: Expected `N/A - Current value ~£850,000`, Got `None`
    - `employment_income`: 100% (6/6 fields)
    - `inheritance`: 100% (6/6 fields)

### case_11_vague_narrative

**Status**: ✅ SUCCESS
**Extraction Time**: 23.7s
**Sources Found**: 4
**Completeness Score**: 75%

**Comparison vs Expected Output**:

- Metadata Accuracy: 100% (4/4 fields)
- Sources: 4/4 matched
  - Field Accuracy by Source:
    - `gift`: 83% (5/6 fields)
      - Missing:
        - `donor_source_of_wealth`: Expected `Friend's business (unspecified)`, Got `None`
    - `sale_of_asset`: 100% (4/4 fields)
    - `employment_income`: 80% (4/5 fields)
      - Missing:
        - `employment_start_date`: Expected `~20 years ago (approximate career start)`, Got `None`
    - `inheritance`: 100% (4/4 fields)
      - Extra (unexpected):
        - `nature_of_inherited_assets`: Extracted `Cash` (expected null)

### case_12_divorce_chain

**Status**: ✅ SUCCESS
**Extraction Time**: 17.8s
**Sources Found**: 3
**Completeness Score**: 100%

**Comparison vs Expected Output**:

- Metadata Accuracy: 100% (4/4 fields)
- Sources: 3/3 matched
  - Field Accuracy by Source:
    - `divorce_settlement`: 100% (5/5 fields)
    - `sale_of_property`: 100% (7/7 fields)
    - `employment_income`: 83% (5/6 fields)
      - Incorrect:
        - `employer_name`: Expected `Self-employed / Consultant`, Got `Unknown employer (name not disclosed)`

### case_13_lottery_gift

**Status**: ✅ SUCCESS
**Extraction Time**: 14.2s
**Sources Found**: 2
**Completeness Score**: 92%

**Comparison vs Expected Output**:

- Metadata Accuracy: 100% (4/4 fields)
- Sources: 2/2 matched
  - Field Accuracy by Source:
    - `gift`: 100% (6/6 fields)
    - `employment_income`: 100% (4/4 fields)
      - Extra (unexpected):
        - `employer_name`: Extracted `Unknown primary school (Coventry)` (expected null)

### case_14_insurance_inheritance

**Status**: ✅ SUCCESS
**Extraction Time**: 45.2s
**Sources Found**: 3
**Completeness Score**: 78%

**Comparison vs Expected Output**:

- Metadata Accuracy: 100% (4/4 fields)
- Sources: 3/3 matched
  - Field Accuracy by Source:
    - `insurance_payout`: 100% (5/5 fields)
    - `employment_income`: 33% (1/3 fields)
      - Missing:
        - `employment_end_date`: Expected `Present (or recently retired)`, Got `None`
        - `country_of_employment`: Expected `United Kingdom (implied)`, Got `None`
      - Extra (unexpected):
        - `employer_name`: Extracted `NHS` (expected null)
        - `annual_compensation`: Extracted `£200,000 (total career savings)` (expected null)
    - `inheritance`: 100% (6/6 fields)

### case_15_business_earnout

**Status**: ✅ SUCCESS
**Extraction Time**: 39.9s
**Sources Found**: 6
**Completeness Score**: 94%

**Comparison vs Expected Output**:

- Metadata Accuracy: 100% (4/4 fields)
- Sources: 5/5 matched
  - Extra sources: sale_of_business
  - Field Accuracy by Source:
    - `gift`: 80% (4/5 fields)
      - Missing:
        - `gift_date`: Expected `2011`, Got `None`
    - `sale_of_business`: 100% (7/7 fields)
    - `sale_of_business`: 100% (7/7 fields)
    - `sale_of_business`: 100% (7/7 fields)
    - `employment_income`: 83% (5/6 fields)
      - Incorrect:
        - `country_of_employment`: Expected `United Kingdom (assumed)`, Got `United States`

