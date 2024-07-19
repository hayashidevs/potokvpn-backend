-- Table: public.subscription

-- DROP TABLE IF EXISTS public.subscription;

CREATE TABLE IF NOT EXISTS public.subscription
(
    id uuid NOT NULL DEFAULT uuid_generate_v4(),
    clientid uuid NOT NULL,
    rateid uuid NOT NULL,
    datestart timestamp without time zone NOT NULL,
    dateend timestamp without time zone NOT NULL,
    CONSTRAINT subscription_pkey PRIMARY KEY (id),
    CONSTRAINT subscription_clientid_fkey FOREIGN KEY (clientid)
        REFERENCES public.client (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT subscription_rateid_fkey FOREIGN KEY (rateid)
        REFERENCES public.rate (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.subscription
    OWNER to postgres;