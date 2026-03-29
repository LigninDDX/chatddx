DROP TRIGGER IF EXISTS prevent_immutable_updates ON {table_name};
CREATE TRIGGER prevent_immutable_updates
BEFORE UPDATE ON {table_name}
FOR EACH ROW
EXECUTE FUNCTION enforce_partial_immutability();
