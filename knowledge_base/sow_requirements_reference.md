# Source of Wealth - Required Fields Reference

This document provides a quick reference for required fields per source of wealth type.

---

## 1. Employment Income

| Field | Description | Examples |
|-------|-------------|----------|
| employer_name | Name of employing organization | Barclays PLC, NHS Trust |
| job_title | Official job title or role | CFO, Senior Engineer |
| employment_start_date | When employment began | March 2015, Q1 2018 |
| employment_end_date | When ended, or 'Present' | December 2023, Present |
| annual_compensation | Annual salary/package in GBP | £150,000, £85,000 base + £30,000 bonus |
| country_of_employment | Country where based | United Kingdom, UAE |

---

## 2. Business Income

| Field | Description | Examples |
|-------|-------------|----------|
| business_name | Legal name of business | ABC Trading Ltd |
| nature_of_business | Industry and activity | Financial consulting, Retail |
| ownership_percentage | Percentage stake | 100%, 51% |
| annual_income_from_business | Annual income drawn | £200,000, £50,000-£80,000 |
| ownership_start_date | When ownership began | Founded in 2005 |
| how_business_acquired | How obtained | Founded, Inherited, Purchased |

---

## 3. Business Dividends

| Field | Description | Examples |
|-------|-------------|----------|
| company_name | Company paying dividends | XYZ Holdings Ltd |
| shareholding_percentage | Percentage of shares | 25%, 100% |
| dividend_amount | Amount received | £100,000 annually |
| period_received | Time period | 2018-Present |
| how_shares_acquired | Method of acquiring | Founded, Inherited, Purchased |

---

## 4. Sale of Business

| Field | Description | Examples |
|-------|-------------|----------|
| business_name | Name of business sold | ABC Manufacturing Ltd |
| nature_of_business | Industry and activity | Manufacturing, IT consulting |
| ownership_percentage_sold | Percentage sold | 100%, 51% |
| sale_date | Date of transaction | March 2022 |
| sale_proceeds | Net proceeds received | £2,500,000 |
| buyer_identity | Who purchased | Private equity firm, Trade buyer |
| how_business_originally_acquired | Original acquisition | Founded in 1995, Inherited |

---

## 5. Sale of Asset

| Field | Description | Examples |
|-------|-------------|----------|
| asset_description | Description of asset | Share portfolio, Classic cars |
| original_acquisition_method | How acquired | Purchased, Inherited |
| original_acquisition_date | When acquired | 2018, Various dates |
| sale_date | Date of sale | June 2023 |
| sale_proceeds | Amount received | £500,000 |
| buyer_identity | Who purchased | Auction house, Private collector |

---

## 6. Sale of Property

| Field | Description | Examples |
|-------|-------------|----------|
| property_address | Address or location | 123 High Street, London SW1 |
| property_type | Type of property | Residential, Buy-to-let, Commercial |
| original_acquisition_method | How acquired | Purchased, Inherited |
| original_acquisition_date | When acquired | 2005, Inherited in 2018 |
| original_purchase_price | Original cost | £350,000 |
| sale_date | Date of sale | August 2023 |
| sale_proceeds | Net proceeds | £850,000 |

---

## 7. Inheritance

| Field | Description | Examples |
|-------|-------------|----------|
| deceased_name | Name of deceased | John Smith (father) |
| relationship_to_deceased | Relationship | Father, Grandmother |
| date_of_death | When passed away | March 2020 |
| amount_inherited | Total value | £500,000 |
| nature_of_inherited_assets | What form it took | Cash, Property, Business shares |
| original_source_of_deceased_wealth | **How deceased accumulated wealth** | Successful surgeon, Business sale |

---

## 8. Gift

| Field | Description | Examples |
|-------|-------------|----------|
| donor_name | Person giving gift | William Jones (grandfather) |
| relationship_to_donor | Relationship | Grandfather, Parent |
| gift_date | When given | December 2022 |
| gift_value | Value of gift | £100,000 |
| donor_source_of_wealth | **How donor accumulated funds** | Pension savings, Business sale |
| reason_for_gift | Purpose or occasion | Wedding gift, House deposit |

---

## 9. Divorce Settlement

| Field | Description | Examples |
|-------|-------------|----------|
| former_spouse_name | Name of ex-spouse | Jane Smith |
| settlement_date | When finalized | July 2021 |
| settlement_amount | Value received | £750,000 |
| court_jurisdiction | Where processed | England and Wales |
| duration_of_marriage | How long married | 15 years |

---

## 10. Lottery Winnings

| Field | Description | Examples |
|-------|-------------|----------|
| lottery_name | Name of lottery | National Lottery, EuroMillions |
| win_date | Date of winning | January 2023 |
| gross_amount_won | Total amount won | £500,000 |
| country_of_win | Country where held | United Kingdom |

---

## 11. Insurance Payout

| Field | Description | Examples |
|-------|-------------|----------|
| insurance_provider | Insurance company | Aviva, Legal & General |
| policy_type | Type of policy | Life insurance, Critical illness |
| claim_event_description | What triggered claim | Death of spouse, Property damage |
| payout_date | When received | October 2022 |
| payout_amount | Amount received | £250,000 |

---

## Key Considerations

### Source Chains
Some sources require tracing back the original source of funds:
- **Inheritance**: Must explain how the deceased accumulated their wealth
- **Gift**: Must explain the donor's source of wealth
- **Divorce**: May need to understand former spouse's wealth origin

### Nested Sources
Some sources can generate ongoing income:
- Inherited business → Ongoing dividends
- Divorce settlement → Property purchase → Property sale

### Deduplication
Same entity may appear multiple times:
- Business income (salary) + Business dividends from same company
- Multiple properties in a portfolio
