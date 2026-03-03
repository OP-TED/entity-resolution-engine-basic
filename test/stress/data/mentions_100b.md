I# mentions_100b.csv — Expected Clusters

**Ground-truth cluster assignments for mentions_100b.csv dataset.**

## Summary Statistics

- **Total mentions**: 100
- **Total clusters**: 42
- **Singleton clusters** (1 member): 10
- **Multi-member clusters** (2-5 members): 32
- **Distribution**:
  - 1-member clusters: 10
  - 2-member clusters: 18
  - 3-member clusters: 4
  - 4-member clusters: 8
  - 5-member clusters: 2

## Clustering Criteria

All clusters are derived using **Jaro-Winkler similarity >= 0.8** on the `legal_name` field.
Mentions in the same cluster represent **plausible variations of the same organization**:

- **Exact match**: `Pepsi` vs `Pepsi` (JW = 1.0000)
- **Suffix variation**: `Pepsi` vs `Pepsi Inc` (JW = 0.9111)
- **Minor typo**: `Pepsi` vs `Pespi Inc` (JW = 0.8281)
- **Character variation**: `Coca Cola` vs `Coca-Cola` (JW = 0.9556)

**Important**: Country-based blocking applies. Only mentions within the same `country_code` can cluster.

## All Clusters (42 total)

### AUT

**m00000001** (4 members)
```
m00000001 | Pepsi                          | JW=1.0000
m00000002 | Pepsi Inc                      | JW=0.9111
m00000003 | Pespi Inc                      | JW=0.8281
m00000004 | Pepsi Limited                  | JW=0.8769
```

**m00000005** (singleton)
```
m00000005 | Bridgestone
```

### BEL

**m00000006** (5 members)
```
m00000006 | Coca Cola                      | JW=1.0000
m00000007 | Coca-Cola                      | JW=0.9556
m00000008 | Coca Cola Inc                  | JW=0.9385
m00000009 | CocaCola                       | JW=0.9778
m00000010 | Coca-Cola Inc                  | JW=0.8829
```

**m00000011** (singleton)
```
m00000011 | Cornerstone
```

### BGR

**m00000012** (4 members)
```
m00000012 | Microsoft                      | JW=1.0000
m00000013 | Microsft Inc                   | JW=0.9111
m00000014 | Microsoft Corp                 | JW=0.9286
m00000015 | Microsoft Corporation          | JW=0.8857
```

**m00000016** (singleton)
```
m00000016 | Norton
```

### HRV

**m00000017** (4 members)
```
m00000017 | Apple                          | JW=1.0000
m00000018 | Apple Inc                      | JW=0.9111
m00000019 | Appl Inc                       | JW=0.8600
m00000020 | Apple Computer                 | JW=0.8714
```

**m00000021** (singleton)
```
m00000021 | Noton
```

### CYP

**m00000022** (4 members)
```
m00000022 | Samsung                        | JW=1.0000
m00000023 | Samsun Inc                     | JW=0.8914
m00000024 | Samsung Ltd                    | JW=0.9273
m00000025 | Samsung Electronics            | JW=0.8737
```

**m00000026** (singleton)
```
m00000026 | Bridgestone
```

### CZE

**m00000027** (4 members)
```
m00000027 | Nestle                         | JW=1.0000
m00000028 | Nestlé                         | JW=0.9333
m00000029 | Nestle Inc                     | JW=0.9200
m00000030 | Nestle Ltd                     | JW=0.9200
```

**m00000031** (singleton)
```
m00000031 | Cornerstone
```

### DNK

**m00000032** (4 members)
```
m00000032 | Siemens                        | JW=1.0000
m00000033 | Siemns AG                      | JW=0.9048
m00000034 | Siemens Inc                    | JW=0.9273
m00000035 | Siemens Ltd                    | JW=0.9273
```

**m00000036** (singleton)
```
m00000036 | Norton
```

### EST

**m00000037** (5 members)
```
m00000037 | Pepsi                          | JW=1.0000
m00000038 | Pepsi Inc                      | JW=0.9111
m00000039 | Pespi Inc                      | JW=0.8281
m00000040 | Pepsi Limited                  | JW=0.8769
m00000041 | PepsiCo                        | JW=0.9429
```

**m00000042** (singleton)
```
m00000042 | Noton
```

### FIN

**m00000043** (4 members)
```
m00000043 | Coca Cola                      | JW=1.0000
m00000044 | Coca-Cola                      | JW=0.9556
m00000045 | Coca Cola Inc                  | JW=0.9385
m00000046 | CocaCola                       | JW=0.9778
```

**m00000047** (singleton)
```
m00000047 | Bridgestone
```

### FRA

**m00000048** (4 members)
```
m00000048 | Microsoft                      | JW=1.0000
m00000049 | Microsft Inc                   | JW=0.9111
m00000050 | Microsoft Corp                 | JW=0.9286
m00000051 | Microsoft Corporation          | JW=0.8857
```

**m00000052** (singleton)
```
m00000052 | Cornerstone
```

### DEU

**m00000053** (2 members)
```
m00000053 | Pepsi                          | JW=1.0000
m00000054 | Pepsi Inc                      | JW=0.9111
```

**m00000055** (3 members)
```
m00000055 | Coca Cola                      | JW=1.0000
m00000056 | Coca-Cola                      | JW=0.9556
m00000057 | Coca Cola Inc                  | JW=0.9385
```

### GRC

**m00000058** (2 members)
```
m00000058 | Microsoft                      | JW=1.0000
m00000059 | Microsft Inc                   | JW=0.9111
```

**m00000060** (2 members)
```
m00000060 | Apple                          | JW=1.0000
m00000061 | Apple Inc                      | JW=0.9111
```

### HUN

**m00000062** (2 members)
```
m00000062 | Samsung                        | JW=1.0000
m00000063 | Samsun Inc                     | JW=0.8914
```

**m00000064** (2 members)
```
m00000064 | Nestle                         | JW=1.0000
m00000065 | Nestlé                         | JW=0.9333
```

### IRL

**m00000066** (2 members)
```
m00000066 | Siemens                        | JW=1.0000
m00000067 | Siemns AG                      | JW=0.9048
```

**m00000068** (3 members)
```
m00000068 | Pepsi                          | JW=1.0000
m00000069 | Pepsi Inc                      | JW=0.9111
m00000070 | Pespi Inc                      | JW=0.8281
```

### ITA

**m00000071** (2 members)
```
m00000071 | Coca Cola                      | JW=1.0000
m00000072 | Coca-Cola                      | JW=0.9556
```

**m00000073** (2 members)
```
m00000073 | Microsoft                      | JW=1.0000
m00000074 | Microsft Inc                   | JW=0.9111
```

### LVA

**m00000075** (2 members)
```
m00000075 | Apple                          | JW=1.0000
m00000076 | Apple Inc                      | JW=0.9111
```

**m00000077** (2 members)
```
m00000077 | Samsung                        | JW=1.0000
m00000078 | Samsun Inc                     | JW=0.8914
```

### LTU

**m00000079** (2 members)
```
m00000079 | Nestle                         | JW=1.0000
m00000080 | Nestlé                         | JW=0.9333
```

**m00000081** (3 members)
```
m00000081 | Siemens                        | JW=1.0000
m00000082 | Siemns AG                      | JW=0.9048
m00000083 | Siemens Inc                    | JW=0.9273
```

### LUX

**m00000084** (2 members)
```
m00000084 | Pepsi                          | JW=1.0000
m00000085 | Pepsi Inc                      | JW=0.9111
```

**m00000086** (2 members)
```
m00000086 | Coca Cola                      | JW=1.0000
m00000087 | Coca-Cola                      | JW=0.9556
```

**m00000097** (2 members)
```
m00000097 | Unilever                       | JW=1.0000
m00000098 | Unilever Inc                   | JW=0.9333
```

### MLT

**m00000088** (2 members)
```
m00000088 | Microsoft                      | JW=1.0000
m00000089 | Microsft Inc                   | JW=0.9111
```

**m00000090** (2 members)
```
m00000090 | Apple                          | JW=1.0000
m00000091 | Apple Inc                      | JW=0.9111
```

**m00000099** (2 members)
```
m00000099 | Volvo                          | JW=1.0000
m00000100 | Volva                          | JW=0.9200
```

### NLD

**m00000092** (2 members)
```
m00000092 | Samsung                        | JW=1.0000
m00000093 | Samsun Inc                     | JW=0.8914
```

**m00000094** (3 members)
```
m00000094 | Nestle                         | JW=1.0000
m00000095 | Nestlé                         | JW=0.9333
m00000096 | Nestle Inc                     | JW=0.9200
```

## Notes for Testing

- Use this file as the **ground truth** for entity resolution quality metrics
- **Similarity threshold**: JW >= 0.8 defines cluster membership
- All variations within a cluster are plausible real-world name variations
- Singletons represent unique organizations with no similar matches in their country
- Look-alike names (e.g., `Bridgestone` vs `Cornerstone`) are intentionally kept separate
- Expected precision: 70-85% (most matches are valid)
- Expected recall: Dependent on algorithm's training; aim for 40%+ on true matches