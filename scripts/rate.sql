-- Table: public.rate

-- DROP TABLE IF EXISTS public.rate;

CREATE TABLE IF NOT EXISTS public.rate
(
    id uuid NOT NULL DEFAULT uuid_generate_v4(),
    name text COLLATE pg_catalog."default" NOT NULL,
    dayamount integer NOT NULL,
    price integer NOT NULL,
    CONSTRAINT rate_pkey PRIMARY KEY (id)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.rate
    OWNER to postgres;