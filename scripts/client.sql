-- Table: public.client

-- DROP TABLE IF EXISTS public.client;

CREATE TABLE IF NOT EXISTS public.client
(
    id uuid NOT NULL DEFAULT uuid_generate_v4(),
    telegramid BIGINT NOT NULL,
    username text COLLATE pg_catalog."default",
    firstname text COLLATE pg_catalog."default",
    lastname text COLLATE pg_catalog."default",
    CONSTRAINT client_pkey PRIMARY KEY (id)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.client
    OWNER to postgres;
