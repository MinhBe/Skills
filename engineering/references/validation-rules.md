# Validation Rules — 7 Rules cho Quality Check

Tài liệu này định nghĩa 7 rules để kiểm tra chất lượng labeling
trong `combined_labeled_data.csv`. Mỗi rule có:
- Mục đích
- Cách detect
- Threshold / tiêu chí
- Cách xử lý khi vi phạm

---

## R1 — Out-of-Taxonomy Check

**Mục đích:** Phát hiện `sqli_type` không nằm trong 14-category taxonomy.

**Cách detect:**

```
CHUẨN = {union_based, error_based, boolean_blind, time_blind, heavy_query,
          stacked_queries, out_of_band, auth_bypass, second_order, rce,
          polyglot, lateral, benign, unknown}

NẾU sqli_type NOT IN CHUẨN → FLAG
```

**Kết quả hiện tại (40,860 rows):**

| Type | Count | Vi phạm? |
|------|-------|----------|
| `boolean_based` | 1,820 | ❌ — nên là `boolean_blind` |
| `generic` | 19 | ❌ — generic là DB engine |
| `comment_based` | 10 | ❌ — không phải category |
| `inline_query` | 8 | ❌ — không phải category |
| `ldap_injection` | 2 | ❌ — không phải SQLi |
| `stacked_query` | 2 | ❌ — typo |
| `command_injection` | 1 | ❌ — không phải category |
| **Total** | **1,862** | |

**Xử lý:**
- `boolean_based` + `stacked_query`: rename tự động (R2)
- Còn lại: re-classify theo references/label-normalization.md

---

## R2 — Label Inconsistency (Duplicate Types)

**Mục đích:** Phát hiện 2 labels khác nhau mô tả cùng 1 attack type.

**Cách detect:**

```
SO SÁNH payload pattern giữa các type khác tên
NẾU pattern giống nhau → FLAG là duplicate
```

**Duplicate pairs đã xác định:**

| Type A | Type B | Same? | Action |
|--------|--------|-------|--------|
| `boolean_blind` (2,711) | `boolean_based` (1,820) | ✅ Cùng 1 type | Merge → `boolean_blind` |
| `stacked_queries` (41) | `stacked_query` (2) | ✅ Cùng 1 type | Merge → `stacked_queries` |

**Lưu ý:**
- `boolean_blind` và `boolean_based` có phân bố confidence khác nhau
  - `boolean_blind`: chủ yếu 0.8-0.95
  - `boolean_based`: chủ yếu 0.5-0.6
  → Có thể AI labeling không chắc chắn nên dùng tên khác
- Sau merge, cần review 1,820 rows `boolean_based` cũ (R3 sẽ bắt)

---

## R3 — Low Confidence Check

**Mục đích:** Phát hiện rows có confidence thấp (< 0.7).
Đây là các rows cần được review lại vì AI không chắc chắn.

**Cách detect:**

```
NẾU confidence < 0.7 → FLAG
```

**Threshold:** `0.7`

**Kết quả hiện tại:** 2,373 rows (5.8%)

**Phân bố low confidence theo type:**

| Type | Count | % của type |
|------|-------|------------|
| `boolean_based` | 1,210 | 66.5% |
| `auth_bypass` | 920 | 77.1% |
| `boolean_blind` | 140 | 5.2% |
| `unknown` | 64 | 51.6% |
| `benign` | 38 | 0.2% |
| `error_based` | 1 | 0.01% |

**Xử lý:**
- Flag tất cả rows có confidence < 0.7
- Recommendation: review lại bằng AI với prompt cải thiện
- Hoặc dùng rule-based classifier để cross-validate

---

## R4 — Benign với SQL Keywords Mạnh

**Mục đích:** Phát hiện rows labeled `benign` nhưng chứa SQL keywords
mạnh (có thể là false negative — AI mislabel).

**Cách detect:**

```
NẾU sqli_type = 'benign'
VÀ payload_norm chứa 1 trong các keywords sau:
  - "UNION", "SLEEP", "pg_sleep", "WAITFOR", "BENCHMARK"
  - "EXTRACTVALUE", "UPDATEXML", "xp_cmdshell"
  - "LOAD_FILE", "utl_inaddr", "ctxsys"
  - "AND 1=1", "OR 1=1", "' OR '"
→ FLAG
```

**Kết quả hiện tại:** 19,669 benign rows cần kiểm tra.

**Gợi ý:**
- Verify random sample 500 rows
- Đo accuracy của benign label
- Nếu accuracy < 95%, cần re-label toàn bộ benign rows
- Đặc biệt chú ý: `benign` + `mysql` (2,501 rows) — có thể là legitimate MySQL queries
  hoặc attack payloads bị mislabel

---

## R5 — DB Engine Không Chuẩn

**Mục đích:** Phát hiện DB engines nằm ngoài 7-category taxonomy gốc.

**Cách detect:**

```
CHUẨN = {mysql, mssql, oracle, postgresql, sqlite, nosql, generic, unknown}
NẾU db_engine NOT IN CHUẨN → FLAG
```

**Kết quả hiện tại:**

| DB Engine | Count | Action |
|-----------|-------|--------|
| `firebird` | 396 | Giữ nguyên — update taxonomy |
| `db2` | 204 | Giữ nguyên — update taxonomy |
| `unknown` | 3 | Kiểm tra — có thể map về `generic` |

**Xử lý:**
- `firebird` và `db2` là valid DB engines. Cập nhật taxonomy từ 7 → 9 categories.
- `unknown` (3 rows): review payload, nếu không có DB signature → đổi thành `generic`.

**Cập nhật taxonomy:**
```
Taxonomy mới (9 categories):
mysql, mssql, oracle, postgresql, sqlite, firebird, db2, generic, unknown
```

---

## R6 — Reasoning Quality

**Mục đích:** Phát hiện reasoning quá ngắn hoặc chung chung.
Reasoning tốt rất quan trọng cho việc debug GAN training sau này.

**Cách detect:**

```
NẾU độ dài reasoning < 30 ký tự → FLAG (quá ngắn)
NẾU reasoning CHỈ là 1 từ đơn → FLAG (quá sơ sài)
NẾU reasoning chứa pattern chung chung:
  - "not_sql_injection"
  - "generic_..._sqli"
  - "sql_injection"
  → FLAG (generic reasoning)
```

**Threshold:** `30 characters`

**Kết quả hiện tại:** 27,997 rows (68.5%) — rất cao!

**Các loại reasoning kém chất lượng:**

| Pattern | Ví dụ | Vấn đề |
|---------|-------|--------|
| 1 word | `"sql_injection"`, `"boolean"` | Không giải thích gì |
| Generic | `"not_sql_injection"` | Không nói rõ tại sao |
| Repeat type | `"boolean_blind"` | Chỉ lặp lại type |
| Too short | `"or 1=1"` | Thiếu context |

**Cách xử lý:**
- Flag rows với reasoning kém
- Recommendation: re-generate reasoning bằng AI (có thể batch)
- Không block GAN training (reasoning là informational, không ảnh hưởng đến model)

---

## R7 — Duplicate Payloads

**Mục đích:** Phát hiện các payload trùng lặp (theo `payload_norm`).

**Cách detect:**

```
NẾU cùng payload_norm xuất hiện > 1 lần → FLAG
SO SÁNH cả sqli_type và db_engine giữa các bản duplicate
NẾU khác nhau → conflict duplicate (cần resolve)
NẾU giống nhau → simple duplicate (có thể dedup)
```

**Xử lý:**

| Loại | Số lượng | Hành động |
|------|----------|-----------|
| Exact duplicate (cùng cả payload + type + DB) | TBD | Giữ 1 row |
| Conflict duplicate (cùng payload, khác type) | TBD | Cần resolve: chọn type đúng |
| Near duplicate (payload tương tự) | TBD | Có thể giữ (diversity cho GAN) |

**Conflict duplicate cần được ưu tiên xử lý:**
- Nếu 2 rows có cùng `payload_norm` nhưng khác `sqli_type` → AI labeling không nhất quán
- Cần re-label cả 2 rows

---

## Summary: Priority và Impact

| Rule | Priority | Target | Tự động? | Impact |
|------|----------|--------|----------|--------|
| R1 — Out-of-taxonomy | **P0** | 40 rows | ❌ Semi-auto | Block GAN training |
| R2 — Label inconsistency | **P0** | 1,822 rows | ✅ Auto rename | Block GAN training |
| R3 — Low confidence | **P1** | 2,373 rows | ❌ Flag only | Quality risk |
| R4 — Benign with SQL keywords | **P2** | 19,669 rows sample | ❌ Flag only | Cần verify |
| R5 — DB engine mở rộng | **P2** | 600 rows | ✅ Update taxonomy | Nhẹ |
| R6 — Reasoning quality | **P2** | 27,997 rows | ❌ Flag only | Informational |
| R7 — Duplicates | **P2** | TBD | ❌ Flag only | Data quality |

### Execution Order

```
Bước 1: R2 → Normalize (rename) boolean_based → boolean_blind, stacked_query → stacked_queries
Bước 2: R1 → Re-classify 40 out-of-taxonomy rows (cần human/AI review)
Bước 3: R3 → Review 2,373 low-confidence rows (có thể batch AI)
Bước 4: R5 → Update DB taxonomy (thêm firebird, db2)
Bước 5: R4 → Verify benign sample
Bước 6: R7 → Dedup nếu cần
Bước 7: R6 → Improve reasoning (nice-to-have)
```
