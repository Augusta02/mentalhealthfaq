import uuid
from flask import Flask, render_template, request, jsonify
from rag import rag
import db

app = Flask(__name__)
db.init_db()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")
 
 
@app.route("/dashboard/data")
def dashboard_data():
    return jsonify({
        "recent_conversations": db.get_recent_conversations(limit=5),
        "feedback_stats": db.get_feedback_stats(),
        "relevance_distribution": db.get_relevance_distribution(),
        "model_usage": db.get_model_usage(),
        "cost_over_time": db.get_timeseries("openai_cost"),
        "tokens_over_time": db.get_timeseries("total_tokens"),
        "response_time_over_time": db.get_timeseries("response_time"),
    })

@app.route("/question", methods=["POST"])
def handle_question():
    data = request.json
    question = data["question"]

    if not question:
        return jsonify({"error": "No question provided"}), 400

    conversation_id = str(uuid.uuid4())

    answer_data = rag(question)

    result = {
        "conversation_id": conversation_id,
        "question": question,
        "answer": answer_data["answer"],
    }

    db.save_conversation(
        conversation_id=conversation_id,
        question=question,
        answer_data=answer_data,
    )

    return jsonify(result)


@app.route("/feedback", methods=["POST"])
def handle_feedback():
    data = request.json
    conversation_id = data["conversation_id"]
    feedback = data["feedback"]

    if not conversation_id or feedback not in [1, -1]:
        return jsonify({"error": "Invalid input"}), 400

    db.save_feedback(
        conversation_id=conversation_id,
        feedback=feedback,
    )

    result = {
        "message": f"Feedback received for conversation {conversation_id}: {feedback}"
    }
    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True)