SELECT COUNT(1) as IndexIsThere
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind = 'i' -- index
AND c.relname = 'idx_client_username';

-- If the index does not exist, create it
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relkind = 'i' -- index
        AND c.relname = 'idx_client_username'
    ) THEN
        CREATE INDEX idx_client_username
        ON client (username);
    END IF;
END $$;