-- Step 3: allow multiple rows per fingerprint when apply_url differs.
ALTER TABLE jobs DROP CONSTRAINT IF EXISTS jobs_fingerprint_key;
ALTER TABLE jobs DROP CONSTRAINT IF EXISTS uq_jobs_fingerprint_apply_url;
ALTER TABLE jobs ADD CONSTRAINT uq_jobs_fingerprint_apply_url UNIQUE (fingerprint, apply_url);
