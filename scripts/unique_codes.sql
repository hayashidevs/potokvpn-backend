-- Create the 'codes' table if it does not exist
CREATE TABLE IF NOT EXISTS codes (
    id SERIAL PRIMARY KEY,
    code VARCHAR(255),
    used_code BOOLEAN DEFAULT FALSE
);

-- Ensure that the 'code' column allows NULL values
ALTER TABLE codes
ALTER COLUMN code DROP NOT NULL;

-- Set the default value for the 'used_code' column to FALSE explicitly (if needed)
ALTER TABLE codes
ALTER COLUMN used_code SET DEFAULT FALSE;

-- Update the table comment to match the Django verbose name
COMMENT ON TABLE codes IS 'Уникальный код';

-- Update the comment on the 'code' column if you want to add more description
COMMENT ON COLUMN codes.code IS 'A unique code, which can be blank or null';

-- Update the comment on the 'used_code' column if needed
COMMENT ON COLUMN codes.used_code IS 'Indicates if the code has been used (true/false)';
