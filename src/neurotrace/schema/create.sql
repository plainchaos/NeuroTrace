-- messages table
CREATE TABLE IF NOT EXISTS messages (
  id TEXT PRIMARY KEY,
  conversation_id TEXT,
  role TEXT,
  parent_id TEXT,
  gizmo_id TEXT DEFAULT '_orphan',
  create_time REAL,
  content_type TEXT,
  children_ids TEXT
);

-- message_contents table
CREATE TABLE IF NOT EXISTS message_contents (
  message_id TEXT,
  part_index INTEGER,
  content TEXT,
  PRIMARY KEY (message_id, part_index)
);
