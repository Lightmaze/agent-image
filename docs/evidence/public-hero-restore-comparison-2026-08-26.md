# Public hero image — fresh restore comparison

Result: **PASS**

This bounded comparison asks one release question: does the public, freshly restored Agent exhibit the mission-specific capability associated with its trained lineage? It does not claim real-world procurement competence.

| Arm | Mean score | Reservation-price leaks |
|---|---:|---:|
| `fresh` | 0.481521 | 0 |
| `public_restored` | 1.000000 | 0 |

- Public-restored gain over fresh: `0.518479`

The two arms used Hermes 0.20.5, DeepSeek `deepseek-v4-flash`, reasoning `none`, no tools, 12 new synthetic held-out scenarios, and two repetitions per scenario. The 48 calls were globally interleaved from a frozen seed.

Raw model responses and credentials remain local and private. The public evidence contains aggregate scores, content digests, the frozen preregistration digest, and the release verdict.
