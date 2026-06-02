---
name: sqli-label-validator
description: >
  Validate, normalize, và kiểm tra chất lượng labels cho GAN_SQLi project.
  Chỉ hoạt động trên định dạng CSV của dự án GAN_SQLi (combined_labeled_data.csv).
  Phát hiện labeling inconsistencies, out-of-taxonomy types, low-confidence rows,
  và tạo báo cáo data quality. Tự động normalize labels về 14-category taxonomy chuẩn
  cho GAN training Phase 3.
source: GAN_SQLi internal
---

# SQLi Label Validator

Skill chuyên biệt cho dự án **GAN_SQLi** — validate và chuẩn hóa toàn bộ labels
trong `combined_labeled_data.csv` trước khi chuyển sang Phase 3 (GAN Training).

---

## Kích hoạt

Skill tự động kích hoạt khi user nói:

> "/sqli-label-validator"  
> "Validate labels"  
> "Kiểm tra chất lượng labeling"  
> "Normalize combined_labeled_data"  
> "Tạo master dataset cho GAN training"  
> "Báo cáo data quality"

Hoặc khi phát hiện file `combined_labeled_data.csv` trong workspace.

---

## Input Format

Skill CHỈ chấp nhận đúng 1 format:

```csv
payload_norm,sqli_type,db_engine,confidence,reasoning
""" or pg_sleep ( __TIME__ ) --","time_blind","postgresql","0.95","pg_sleep is PostgreSQL time-based blind SQLi"
```

| Column | Kiểu | Bắt buộc | Mô tả |
|--------|------|----------|-------|
| `payload_norm` | string | yes | Payload đã normalize (URL-decode, whitespace collapse) |
| `sqli_type` | string | yes | Loại SQLi attack (14 categories) |
| `db_engine` | string | yes | Database engine target |
| `confidence` | float | yes | 0.0 - 1.0 |
| `reasoning` | string | yes | Giải thích ngắn |

**Path mặc định:** `C:\Projects\GAN_SQLi\Asset\LabelData\combined_labeled_data.csv`

---

## Workflow

### Task 1: Validate toàn bộ dataset

Đọc CSV → chạy 7 validation rules → tạo báo cáo.

Các bước:
1. Đọc file CSV, parse headers, kiểm tra định dạng
2. Thống kê phân bố `sqli_type`, `db_engine`, `confidence`
3. Chạy 7 rules (xem references/validation-rules.md)
4. Ghi nhận mọi vi phạm vào `label_corrections_report.csv`
5. Tạo `data_quality_report.md`

### Task 2: Normalize labels

Tự động sửa các lỗi labeling có thể fix bằng rules:

| Lỗi | Số lượng | Cách sửa |
|-----|----------|----------|
| `boolean_based` | 1,820 | → `boolean_blind` |
| `stacked_query` | 2 | → `stacked_queries` |
| `comment_based` | 10 | → `boolean_blind` (kiểm tra payload trước) |
| `inline_query` | 8 | → `union_based` (nếu có UNION) |
| `ldap_injection` | 2 | → `unknown` |
| `command_injection` | 1 | → `rce` (nếu có xp_cmdshell) |
| `generic` (sqli_type) | 19 | Tra cứu theo payload pattern |

Output: `combined_labeled_data_normalized.csv`

### Task 3: Tạo master dataset cho GAN training

Từ dataset đã normalize → thêm columns phục vụ GAN training:

- `is_attack`: boolean — True nếu sqli_type != benign/unknown
- `attack_type_group`: nhóm lớn (Injection, Blind, Auth, Benign)
- `confidence_bucket`: low (<0.7) / medium (0.7-0.89) / high (>=0.9)

Output: `master_labeled_data.csv`

---

## Output Files

Tất cả output được ghi vào cùng thư mục với input CSV:

| File | Mô tả |
|------|-------|
| `combined_labeled_data_normalized.csv` | Dataset đã normalize labels, giữ đúng schema gốc |
| `label_corrections_report.csv` | Chi tiết mọi thay đổi — dùng để audit |
| `data_quality_report.md` | Báo cáo chất lượng tổng quan + từng rule |
| `master_labeled_data.csv` | Dataset cuối cùng + extra columns cho GAN training |

**QUAN TRỌNG:** File gốc `combined_labeled_data.csv` KHÔNG BAO GIỜ bị ghi đè.

---

## Label Corrections Report Format

```csv
row_index,field,old_value,new_value,reason,rule
5,sqli_type,boolean_based,boolean_blind,"Normalize: boolean_based is duplicate of boolean_blind",R2
```

| Column | Mô tả |
|--------|-------|
| `row_index` | 0-based index trong CSV gốc |
| `field` | Column bị sửa (`sqli_type` hoặc `db_engine`) |
| `old_value` | Giá trị gốc |
| `new_value` | Giá trị sau khi sửa |
| `reason` | Lý do |
| `rule` | Rule đã phát hiện (R1-R7) |

---

## 14-Category Taxonomy

Chi tiết từng category + detection signals xem `references/taxonomy.md`.

```
union_based       — UNION SELECT / UNION ALL SELECT
error_based       — EXTRACTVALUE / updatexml / utl_inaddr / ctxsys
boolean_blind     — AND/OR + so sánh (1=1, 'a'='a)
time_blind        — SLEEP / pg_sleep / WAITFOR DELAY / BENCHMARK
heavy_query       — COUNT(*) cross-join, CPU-intensive
stacked_queries   — Nhiều statements (;)
out_of_band       — LOAD_FILE / xp_cmdshell / UTL_HTTP
auth_bypass       — ' OR '1'='1 / admin'--
second_order      — Stored SQLi, INSERT → trigger
rce               — xp_cmdshell / certutil / OS command via DB
polyglot          — Cross-DBMS payloads
lateral           — JOIN-based injection
benign            — Legitimate SQL / plain text
unknown           — Không đủ thông tin
```

---

## DB Engine Taxonomy (9 categories)

Mở rộng từ 7 → 9 dựa trên phát hiện thực tế từ dữ liệu:

```
mysql          — @@VERSION, LOAD_FILE, SLEEP(), information_schema
mssql          — @@VERSION (MSSQL), WAITFOR DELAY, sysobjects, xp_cmdshell
oracle         — utl_inaddr, ctxsys.drithsx, dual, all_tables, ROWNUM
postgresql     — pg_sleep(), version()::, pg_catalog
sqlite         — sqlite_version(), sqlite_master, randomblob
firebird       — rdb$functions, rdb$ (signature từ dữ liệu thực tế)
db2            — sysibm.systables (signature từ dữ liệu thực tế)
generic        — Không có DB-specific signature
unknown        — Không đủ thông tin
```

---

## Reference Files

| File | Mô tả |
|------|-------|
| `references/taxonomy.md` | 14 SQLi types + detection signals + examples |
| `references/label-normalization.md` | Full mapping rules + lưu ý khi re-classify |
| `references/validation-rules.md` | 7 rules + thresholds + edge cases |
