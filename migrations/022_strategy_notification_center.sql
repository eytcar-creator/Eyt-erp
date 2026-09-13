-- E.Y.T Strategy Notification Center
-- Persistent in-app notifications for assigned actions and deadline events.

CREATE TABLE IF NOT EXISTS strategy_notifications (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES eyt_users(id) ON DELETE CASCADE,
    action_id BIGINT REFERENCES strategy_actions(id) ON DELETE CASCADE,
    notification_type TEXT NOT NULL CHECK (notification_type IN ('ASSIGNED','DUE_72H','DUE_24H','OVERDUE','COMPLETED')),
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    read_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id, action_id, notification_type)
);

CREATE INDEX IF NOT EXISTS idx_strategy_notifications_user_unread
    ON strategy_notifications(user_id, is_read, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_strategy_notifications_action
    ON strategy_notifications(action_id, created_at DESC);

CREATE OR REPLACE FUNCTION strategy_notification_sync()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.assigned_to IS NOT NULL AND (TG_OP = 'INSERT' OR NEW.assigned_to IS DISTINCT FROM OLD.assigned_to) THEN
        INSERT INTO strategy_notifications(user_id, action_id, notification_type, title, body)
        VALUES (NEW.assigned_to, NEW.id, 'ASSIGNED', 'اقدام جدید به شما واگذار شد', NEW.title)
        ON CONFLICT DO NOTHING;
    END IF;
    IF NEW.status = 'DONE' AND (TG_OP = 'INSERT' OR OLD.status IS DISTINCT FROM NEW.status) AND NEW.assigned_to IS NOT NULL THEN
        INSERT INTO strategy_notifications(user_id, action_id, notification_type, title, body)
        VALUES (NEW.assigned_to, NEW.id, 'COMPLETED', 'اقدام تکمیل شد', NEW.title)
        ON CONFLICT DO NOTHING;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_strategy_notification_sync ON strategy_actions;
CREATE TRIGGER trg_strategy_notification_sync
AFTER INSERT OR UPDATE OF assigned_to, status ON strategy_actions
FOR EACH ROW EXECUTE FUNCTION strategy_notification_sync();
