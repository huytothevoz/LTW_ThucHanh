-- Store password-reset OTPs as hashes rather than plaintext.
ALTER TABLE password_reset_tokens ADD COLUMN otp_hash TEXT;
