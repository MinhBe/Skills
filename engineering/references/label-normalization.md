# Label Normalization — Mapping Rules

Tài liệu này định nghĩa cách normalize các labels lỗi trong
`combined_labeled_data.csv` về 14-category taxonomy chuẩn.

Có 2 loại normalization:

| Loại | Mô tả | Cách xử lý |
|------|-------|-------------|
| **Rename** | Cùng ý nghĩa, khác tên | Đổi tên trực tiếp, không cần review payload |
| **Re-classify** | Sai category thật sự | Cần review payload để chọn category đúng |

---

## Loại 1: Rename (tự động — không mất thông tin)

### 1.1 `boolean_based` (1,820 rows) → `boolean_blind`

**Lý do:** `boolean_based` và `boolean_blind` là cùng một kỹ thuật
(Boolean-Based Blind SQLi), chỉ khác tên gọi. AI labeling không nhất quán.

**Cách xử lý:** Rename trực tiếp, không cần review.

**Confidence của các rows này:**
- 0.5: 1,210 rows (67%)
- 0.6: 610 rows (33%)

→ Sau khi rename, 1,820 rows này sẽ nằm trong danh sách low-confidence cần review.

### 1.2 `stacked_query` (2 rows) → `stacked_queries`

**Lý do:** Typo thiếu "s" ở cuối.

**Cách xử lý:** Rename trực tiếp.

**Payload mẫu:**
```
select name from syscolumns where id = ( select id from sysobjects where name = tablename' ) --
```

---

## Loại 2: Re-classify (cần review payload)

### 2.1 `generic` (sqli_type) — 19 rows

**Vấn đề:** `generic` là DB engine, không phải SQLi type.
Cần xem payload để xác định type thật.

**Hướng dẫn từng bước:**

```
Bước 1: Xem payload_norm
Bước 2: Check các signals theo thứ tự ưu tiên:

1. Có rce signal (xp_cmdshell, certutil)?              → rce
2. Có out_of_band signal (LOAD_FILE, UTL_HTTP)?         → out_of_band
3. Có stacked signal (; + new statement)?                → stacked_queries
4. Có error signal (EXTRACTVALUE, updatexml)?            → error_based
5. Có time signal (SLEEP, pg_sleep, WAITFOR)?            → time_blind
6. Có heavy signal (COUNT(*) cross-join)?                → heavy_query
7. Có UNION?                                              → union_based
8. Có boolean comparison (AND/OR + so sánh)?             → boolean_blind
9. Có auth bypass pattern (admin' OR)?                   → auth_bypass
10. Không có gì?                                          → benign hoặc unknown
```

**Chú ý:** Dùng priority table trong taxonomy.md để xử lý overlap.

### 2.2 `comment_based` — 10 rows

**Vấn đề:** Comment injection (`/**/`, `#`, `--`) là kỹ thuật bypass,
không phải attack type. Hầu hết các payload này thực chất là boolean_blind
có thêm comment để bypass WAF.

**Cách xử lý:**

Kiểm tra payload:
- Nếu có `AND/OR` + so sánh + comment → `boolean_blind`
- Nếu có UNION + comment → `union_based`
- Nếu ONLY comment, không có attack logic gì khác → `boolean_blind` (default)

**Ví dụ:**
```
select * from users where id = 1/**/or/**/1=1  → boolean_blind
select * from users/**/union/**/select/**/1,2  → union_based
/**/                                               → unknown (default)
```

**Cần review từng row**, không auto-rename.

### 2.3 `inline_query` — 8 rows

**Vấn đề:** `inline_query` không phải category chuẩn. Cần xác định đây là
union-based hay boolean-based.

**Cách xử lý:**

- Nếu payload có `UNION SELECT` hoặc `UNION ALL SELECT` → `union_based`
- Nếu không có UNION → kiểm tra các signals khác theo priority

**Ví dụ:**
```
select * from users where id = 1 union (select 1,2,3)  → union_based
```

### 2.4 `ldap_injection` — 2 rows

**Vấn đề:** LDAP injection không phải SQL injection.
Đây có thể là mis-classification từ AI.

**Cách xử lý:** Chuyển về `unknown`.
Hoặc nếu payload không có SQL context gì → `benign`.

**Payload mẫu (cần verify):**
Kiểm tra xem payload có thực sự là LDAP syntax không.
Nếu không có SQL keywords nào → `unknown`.
Nếu có SQL keywords → classify bình thường.

### 2.5 `command_injection` — 1 row

**Vấn đề:** Command injection có thể là `rce` (nếu qua DB)
hoặc `unknown` (nếu không liên quan đến DB).

**Cách xử lý:**
- Nếu có `xp_cmdshell` hoặc DB-to-OS functions → `rce`
- Nếu không liên quan đến DB → `unknown`

---

## Lưu ý quan trọng

### Không auto-apply re-classify

Các re-classify (Loại 2) cần được review bởi human hoặc AI.
Skill chỉ đề xuất, không tự động sửa.

### Backup trước khi sửa

Trước mọi thay đổi, skill ghi log vào `label_corrections_report.csv`:

```csv
row_index,field,old_value,new_value,reason,rule
0,sqli_type,boolean_based,boolean_blind,"Normalize: duplicate type boolean_based → boolean_blind",R2
```

### Confidence impact

Sau normalize:
- `boolean_based` (1,820 rows) sẽ có sqli_type đúng là `boolean_blind`
- Nhưng confidence của chúng (0.5-0.6) vẫn thấp → sẽ bị flag bởi R3
- Cần review riêng 1,820 rows này để re-label với confidence cao hơn

### DB engine giữ nguyên

Các normalization trên CHỈ tác động đến `sqli_type`.
`db_engine` không bị thay đổi.

---

## Summary Table

| Current Label | Target Label | Type | Count | Auto? |
|---------------|-------------|------|-------|-------|
| `boolean_based` | `boolean_blind` | Rename | 1,820 | ✅ Auto |
| `stacked_query` | `stacked_queries` | Rename | 2 | ✅ Auto |
| `comment_based` | `boolean_blind` (likely) | Re-classify | 10 | ❌ Review |
| `inline_query` | `union_based` (likely) | Re-classify | 8 | ❌ Review |
| `ldap_injection` | `unknown` | Re-classify | 2 | ❌ Review |
| `command_injection` | `rce` (if DB) | Re-classify | 1 | ❌ Review |
| `generic` | Tra cứu theo payload | Re-classify | 19 | ❌ Review |
