-- Table: public.test_rate_history

-- DROP TABLE IF EXISTS public.test_rate_history;

CREATE TABLE IF NOT EXISTS public.test_rate_history
(
    id uuid NOT NULL DEFAULT uuid_generate_v4(),
    clientid uuid,
    CONSTRAINT test_rate_history_pkey PRIMARY KEY (id),
    CONSTRAINT test_rate_history_clinet_id_fkey FOREIGN KEY (clientid)
        REFERENCES public.client (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.test_rate_history
    OWNER to postgres;