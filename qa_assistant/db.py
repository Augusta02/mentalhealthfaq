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
        conn.execute("DROP TABLE IF EXISTS feedback")
        conn.execute("DROP TABLE IF EXISTS conversations")

        conn.execute("""
            CREATE TABLE conversations (
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
            CREATE TABLE feedback (
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