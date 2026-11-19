-- QC analytics queries (SQLite dialect; date functions need small edits for SQL Server / PostgreSQL)

-- 1. First-pass rate by inspection phase (preparatory / initial / follow-up)
SELECT phase, COUNT(*) AS inspections,
       ROUND(100.0 * SUM(result = 'Pass') / COUNT(*), 1) AS first_pass_pct,
       SUM(result = 'Fail') AS failed
FROM inspections GROUP BY phase
ORDER BY CASE phase WHEN 'Preparatory' THEN 1 WHEN 'Initial' THEN 2 ELSE 3 END;

-- 2. Subcontractor scorecard with an escalation recommendation
WITH insp AS (
  SELECT sub_id, COUNT(*) AS n, 100.0 * SUM(result = 'Pass') / COUNT(*) AS first_pass_pct
  FROM inspections GROUP BY sub_id),
d AS (
  SELECT sub_id,
         SUM(date_closed IS NULL) AS open_defs,
         SUM(date_closed IS NULL AND due_date < '2026-10-31') AS overdue,
         AVG(julianday(date_closed) - julianday(date_found)) AS avg_days_to_close
  FROM deficiencies GROUP BY sub_id)
SELECT s.sub_name, s.trade, insp.n AS inspections,
       ROUND(insp.first_pass_pct, 1) AS first_pass_pct,
       COALESCE(d.open_defs, 0) AS open_defs, COALESCE(d.overdue, 0) AS overdue,
       ROUND(d.avg_days_to_close, 1) AS avg_days_to_close,
       CASE WHEN insp.first_pass_pct < 60 OR COALESCE(d.overdue,0) >= 3 THEN 'Escalate'
            WHEN insp.first_pass_pct < 70 OR COALESCE(d.overdue,0) >= 1 THEN 'Watch'
            ELSE 'On track' END AS action
FROM subcontractors s JOIN insp ON insp.sub_id = s.sub_id LEFT JOIN d ON d.sub_id = s.sub_id
ORDER BY insp.first_pass_pct;

-- 3. Open deficiency aging
SELECT CASE WHEN age <= 7 THEN '0-7 days' WHEN age <= 14 THEN '8-14 days'
            WHEN age <= 30 THEN '15-30 days' ELSE '31+ days' END AS age_bucket,
       COUNT(*) AS open_defs, SUM(severity = 'Critical') AS critical
FROM (SELECT severity, julianday('2026-10-31') - julianday(date_found) AS age
      FROM deficiencies WHERE date_closed IS NULL) GROUP BY age_bucket;

-- 4. Overdue corrective actions, worst first
SELECT d.deficiency_id, p.project_name, s.sub_name, d.category, d.severity, d.due_date,
       CAST(julianday('2026-10-31') - julianday(d.due_date) AS INT) AS days_overdue
FROM deficiencies d JOIN projects p USING (project_id) JOIN subcontractors s USING (sub_id)
WHERE d.date_closed IS NULL AND d.due_date < '2026-10-31'
ORDER BY CASE d.severity WHEN 'Critical' THEN 1 WHEN 'Major' THEN 2 ELSE 3 END, days_overdue DESC;

-- 5. Monthly deficiencies opened vs closed
SELECT m, SUM(opened) AS opened, SUM(closed) AS closed FROM (
  SELECT substr(date_found,1,7) AS m, 1 AS opened, 0 AS closed FROM deficiencies
  UNION ALL SELECT substr(date_closed,1,7), 0, 1 FROM deficiencies WHERE date_closed IS NOT NULL)
GROUP BY m ORDER BY m;

-- 6. Material receiving: why material was rejected
SELECT rejection_reason, COUNT(*) AS receipts FROM material_receipts
WHERE accepted = 'N' GROUP BY rejection_reason ORDER BY receipts DESC;
