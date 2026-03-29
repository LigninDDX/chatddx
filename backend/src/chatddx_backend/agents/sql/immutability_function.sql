CREATE OR REPLACE FUNCTION enforce_partial_immutability()
RETURNS TRIGGER AS $$
DECLARE
    old_data jsonb;
    new_data jsonb;
BEGIN
    IF OLD.fingerprint IS NOT NULL AND OLD.fingerprint != '' THEN
        old_data := to_jsonb(OLD) - 'updated_at';
        new_data := to_jsonb(NEW) - 'updated_at';
    IF old_data != new_data THEN
        RAISE EXCEPTION 'Immutable Record Error: Only "updated_at" may be modified on fingerprinted records. Detected changes in: %',
        (SELECT jsonb_object_agg(key, value)
         FROM jsonb_each(new_data)
         WHERE old_data->key IS DISTINCT FROM value);
END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
