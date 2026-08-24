-- Step 3: allow multiple rows per fingerprint when apply_url differs.
-- Step 1 created a UNIQUE index named ix_jobs_fingerprint; drop that too.
ALTER TABLE jobs DROP CONSTRAINT IF EXISTS jobs_fingerprint_key;
DROP INDEX IF EXISTS ix_jobs_fingerprint;
ALTER TABLE jobs DROP CONSTRAINT IF EXISTS uq_jobs_fingerprint_apply_url;
ALTER TABLE jobs ADD CONSTRAINT uq_jobs_fingerprint_apply_url UNIQUE (fingerprint, apply_url);
CREATE INDEX IF NOT EXISTS ix_jobs_fingerprint ON jobs (fingerprint);
ALTER TABLE jobs ALTER COLUMN source_job_id TYPE text;
