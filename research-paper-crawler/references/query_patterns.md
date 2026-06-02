# Query Patterns

Start with the user's literal topic, then add conservative variants.

## General

- `"topic phrase" AND method`
- `"topic phrase" AND detection`
- `"topic phrase" AND survey`
- `"topic phrase" AND dataset`
- `"topic phrase" AND benchmark`

## Cybersecurity And SQL Injection

- `"SQL injection" AND detection`
- `"SQL injection" AND "machine learning"`
- `"SQL injection" AND GAN`
- `"web attack" AND "adversarial"`
- `"intrusion detection" AND "generative adversarial network"`

## Regional Expansion

Use affiliation-country filters before adding country names to the query. Add
country names only when the user is interested in study context, national
datasets, or local venues.

## Multilingual Hints

Use English first for international indexes. For local indexes, consider adding
native-language terms when the source supports them:

- Russian: SQL injection, cybersecurity, machine learning equivalents.
- Japanese: SQL injection and cybersecurity equivalents for J-STAGE/CiNii.
- Chinese: SQL injection, web security, machine learning equivalents.
- Korean: SQL injection and web security equivalents.

When unsure about translation quality, keep native terms as optional query
variants and label the variant in the report.
