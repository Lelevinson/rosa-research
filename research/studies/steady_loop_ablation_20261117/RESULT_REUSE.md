# Tool-result reuse after the trimming point (fresh FULL arm; measured only; definitions in result_reuse.py)

| group | episodes | requests | results | results re-sent at age >= 3 | of those: any later use | of those: last-copy use | input tokens | re-sent tokens of results at age >= 3 | of which results never used later | of which results never used as last copy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| all | 40 | 211 | 185 | 103 | 66 | 31 | 721,646 | 94,919 (13.2%) | 46,342 | 63,332 |
| bonsai-2:4b | 10 | 64 | 56 | 37 | 19 | 11 | 261,718 | 61,828 (23.6%) | 42,125 | 51,166 |
| gpt-oss:20b | 10 | 47 | 37 | 18 | 16 | 9 | 88,386 | 1,323 (1.5%) | 0 | 36 |
| lfm3:1.7b | 10 | 62 | 59 | 37 | 21 | 8 | 269,983 | 29,943 (11.1%) | 4,175 | 10,401 |
| qwen3.5:9b | 10 | 38 | 33 | 11 | 10 | 3 | 101,559 | 1,825 (1.8%) | 42 | 1,729 |

Age of the request that uses an item of a result (r+1 = 1, r+2 = 2, ... capped at 5), counting every (result, request) use pair: {"1": 93, "2": 47, "3": 48, "4": 18, "5": 40}
