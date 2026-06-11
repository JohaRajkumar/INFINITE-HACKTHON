def add_indexes():
    """Create indexes to improve query performance for the RUNBOOK schema.
    
    - idx_runbook_status on RUNBOOK(status)
    - idx_step_run_id on runbook_steps(run_id)
    - idx_step_type on runbook_steps(step_type)
    """
    try:
        # Import engine lazily to avoid circular import
        from database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_runbook_status ON RUNBOOK (status);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_step_run_id ON runbook_steps (run_id);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_step_type ON runbook_steps (step_type);"))
            conn.commit()
    except Exception as e:
        print(f"[MIGRATIONS] Error creating indexes: {e}")

if __name__ == '__main__':
    add_indexes()
