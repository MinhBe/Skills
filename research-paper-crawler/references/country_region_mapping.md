# Country And Region Mapping

Use these canonical region keys in scripts and reports.

| Key | Countries or areas |
| --- | --- |
| `europe` | EU countries plus United Kingdom, Switzerland, Norway, Iceland, Ukraine, and other European research affiliations when the user says Europe broadly |
| `eu` | European Union member states only |
| `russia` | Russian Federation |
| `india` | India |
| `canada` | Canada |
| `japan` | Japan |
| `us` | United States, USA, U.S., America when used as country |
| `uk` | United Kingdom, England, Scotland, Wales, Northern Ireland |
| `china` | China, People's Republic of China, PRC, mainland China; keep Hong Kong, Macau, and Taiwan separate if the source distinguishes them |
| `korea` | South Korea by default; ask or split if the user says North Korea or DPRK |

## OpenAlex Filters

Use affiliation country codes with OpenAlex where possible:

- `US`, `GB`, `CA`, `IN`, `JP`, `CN`, `KR`, `RU`
- For `eu` and `europe`, use multiple country-code filters or post-filter by
  authorship institutions when the API query would be too long.

## Reporting Rule

Separate:

- affiliation country: where authors or institutions are located
- publication country: where the publisher or venue is based
- study country: where the research object or dataset comes from

Do not collapse these into one field unless the user explicitly asks for a loose
regional scan.
