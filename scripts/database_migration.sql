-- Изменяет таблицу client, включая новые столбцы для реферальной системы и тестовой подписки.
ALTER TABLE "client"
ADD COLUMN "referral_id" VARCHAR(255) UNIQUE,  -- Уникальный реферальный идентификатор для каждого пользователя.
ADD COLUMN "referred_by" UUID REFERENCES "client" ("id"),                 -- Указывает на пользователя, который направил этого пользователя.
ADD COLUMN "UsedTestSubscription" BOOLEAN NOT NULL DEFAULT FALSE;         -- Указывает, использовалась ли тестовая подписка.
ALTER TABLE subscription ADD COLUMN name VARCHAR(255);                    -- Название устройства пользователя
ALTER TABLE subscription ADD COLUMN public_key VARCHAR(255);
ALTER TABLE subscription ADD COLUMN config_name VARCHAR(255);
ALTER TABLE rate ADD COLUMN isreferral BOOLEAN DEFAULT FALSE;
ALTER TABLE client ADD COLUMN usedref BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE subscription ADD COLUMN is_used BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE client ADD COLUMN phonenumber VARCHAR(15);
ALTER TABLE rate ADD COLUMN bonus_days INTEGER;


-- Обновляет UsedTestSubscription на основе наличия записей клиента в test_rate_history.
UPDATE "client"
SET "UsedTestSubscription" = TRUE
WHERE "id" IN (
    SELECT DISTINCT "clientid"
    FROM "test_rate_history"
    WHERE "clientid" IS NOT NULL
);