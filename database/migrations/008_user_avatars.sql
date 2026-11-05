ALTER TABLE users ADD COLUMN avatar_path TEXT;

INSERT INTO schema_migrations(version,filename,applied_at)
VALUES(8,'008_user_avatars.sql','__APPLIED_AT__');
