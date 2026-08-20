import sqlite3
from datetime import datetime, timezone
import os
from config import DB_PATH



def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn



def init_db():
    conn = get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                model_used TEXT NOT NULL,
                response_time REAL NOT NULL,
                relevance TEXT NOT NULL,
                relevance_explanation TEXT NOT NULL,
                prompt_tokens INTEGER NOT NULL,
                completion_tokens INTEGER NOT NULL,
                total_tokens INTEGER NOT NULL,
                eval_prompt_tokens INTEGER NOT NULL,
                eval_completion_tokens INTEGER NOT NULL,
                eval_total_tokens INTEGER NOT NULL,
                openai_cost REAL NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT REFERENCES conversations(id),
                feedback INTEGER NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        conn.commit()
        print(f"Database initialized at {DB_PATH}")
    finally:
        conn.close()


def save_conversation(conversation_id: str, question: str, answer_data: dict, timestamp=None):
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    timestamp_str = timestamp.isoformat()

    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO conversations
            (id, question, answer, model_used, response_time, relevance,
             relevance_explanation, prompt_tokens, completion_tokens, total_tokens,
             eval_prompt_tokens, eval_completion_tokens, eval_total_tokens, openai_cost, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                conversation_id,
                question,
                answer_data["answer"],
                answer_data["model_used"],
                answer_data["response_time"],
                answer_data["relevance"],
                answer_data["relevance_explanation"],
                answer_data["prompt_tokens"],
                answer_data["completion_tokens"],
                answer_data["total_tokens"],
                answer_data["eval_prompt_tokens"],
                answer_data["eval_completion_tokens"],
                answer_data["eval_total_tokens"],
                answer_data["openai_cost"],
                timestamp_str,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def save_feedback(conversation_id, feedback, timestamp=None):
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    timestamp_str = timestamp.isoformat()

    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO feedback (conversation_id, feedback, timestamp) VALUES (?, ?, ?)",
            (conversation_id, feedback, timestamp_str),
        )
        conn.commit()
    finally:
        conn.close()


def get_recent_conversations(limit=5, relevance= None):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        query = """
            SELECT c.*, f.feedback
            FROM conversations c
            LEFT JOIN feedback f ON c.id = f.conversation_id
        """
        params = []
        if relevance:
            query += " WHERE c.relevance = ?"
            params.append(relevance)
        query += " ORDER BY c.timestamp DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_feedback_stats():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("""
            SELECT
                SUM(CASE WHEN feedback > 0 THEN 1 ELSE 0 END) as thumbs_up,
                SUM(CASE WHEN feedback < 0 THEN 1 ELSE 0 END) as thumbs_down
            FROM feedback
        """).fetchone()
        return dict(row)
    finally:
        conn.close()



# dashboard monitoring integration 
def get_relevance_distribution():
    """Count of conversations per relevance label, for a pie/doughnut chart."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("""
            SELECT relevance, COUNT(*) as count
            FROM conversations
            GROUP BY relevance
        """).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
 
 
def get_model_usage():
    """Count of conversations per model, for a bar chart."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("""
            SELECT model_used, COUNT(*) as count
            FROM conversations
            GROUP BY model_used
        """).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
 
 
def get_timeseries(field, limit=200):
    """Generic timestamp + numeric field pairs, for line charts (cost,
    tokens, response time). `field` is validated against an allowlist so
    this can never be used to inject an arbitrary column name into SQL."""
    allowed_fields = {"openai_cost", "total_tokens", "response_time"}
    if field not in allowed_fields:
        raise ValueError(f"field must be one of {allowed_fields}, got {field!r}")
 
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        # field is safe to interpolate directly ONLY because it was just
        # validated against the fixed allowlist above, never from raw user input
        rows = conn.execute(f"""
            SELECT timestamp, {field} as value
            FROM conversations
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,)).fetchall()
        # reverse so charts read left-to-right in chronological order
        return [dict(row) for row in reversed(rows)]
    finally:
        conn.close()