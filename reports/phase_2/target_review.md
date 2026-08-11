# Phase 2 Target Review

Both targets are complete constructed indicators in the Eswatini file. The World Bank DDI groups negative, don't-know, and refused responses under the constructed zero category (`No/DK/Ref`), so zero must not be described as a separately observed, pure refusal-free 'No' category.

## Financial inclusion - `account_fin`

- Official label: Has an account at a financial institution
- Observed distribution: `{"0": 514, "1": 537}`
- Missing: 0 (0.00%)
- Codebook definition: = 1 if the respondent had an account at a bank or at another type of financial institution, such as a credit union, a microfinance institution, a cooperative, or the post office (if applicable), or has a debit card = 0 if the respondent did not have an account Note: The data also includes an additional 2 percent of respondents in 2024 who reported receiving wages, government transfers, a public sector pension, or payments for agricultural products into an account (excluding mobile money) in the past year; or paying utility bills from a financial institution account in the past year; or receiving wages, government transfers, or agricultural payments to a card in the past year. The definition does not include non-bank financial institutions such as pension funds, retirement accounts, insurance companies, or equity holdings such as stocks. Questions screened for account ownership in the questionnaire do not include these additional 2 percent of respondents.
- Source: https://microdata.worldbank.org/catalog/7900/variable/F1/V14?name=account_fin

## Mobile-money adoption - `account_mob`

- Official label: Has a mobile money account
- Observed distribution: `{"0": 440, "1": 611}`
- Missing: 0 (0.00%)
- Codebook definition: = 1 if the respondent used mobile money services to pay bills or to send or receive money in the past year = 0 if the respondent did not use them Note: Mobile money service providers are those included in the GSM Association's Mobile Money for the Unbanked (GSMA MMU) database. The data also includes an additional 2 percent of respondents in 2024 who received wages, government transfers, a public sector pension, or payments for agricultural products through a mobile phone in the past year. Unlike the definition of account at a financial institution, the definition of mobile money account does not include the payment of utility bills through a mobile phone. The reason is that the phrasing of the possible answers leaves it open as to whether those payments were made using a mobile money account or an over-the-counter service. Questions screened for account ownership in the questionnaire do not include these additional 2 percent of respondents.
- Source: https://microdata.worldbank.org/catalog/7900/variable/F1/V15?name=account_mob

## Consequences for modelling

- The targets answer different questions and require separate pipelines and evaluations.
- The combined `account` variable and `dig_account` are excluded from both models because they encode one or both outcomes.
- Payment-receipt and utility-payment variables mentioned in the constructed definitions are excluded as direct reconstruction risks.
- Account-owner and mobile-money-owner questionnaire branches are excluded because their availability itself reveals outcome status.
- Reported rates at this phase are unweighted file distributions, not population estimates.
