import json
from time import time
from openai import OpenAI
import os 
import ingest
from dotenv import load_dotenv
import logging

load_dotenv()
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# search index
try:
    index= ingest.load_index()
except Exception as e:
    logger.error(f'Index Failed to Load: {e}')
    raise

if index is None:
    raise ValueError("Search Index Could Not Be Loaded")

def search(query):
    try:
        results = index.search(query=query, num_results=1)
        return results
    except Exception as e:
        logger.error(f'Error in search function: {e}')
        return []


system_template="""
You are an expert mental health assistant specialized in providing detailed and accurate answers based on the provided context.
Answer the QUESTION based on the CONTEXT from the mental health database.
Use only the facts from the CONTEXT when answering the QUESTION.

Here is the context:

Context: {context}

Please answer the following question based on the provided context:

Question: {question}

Provide a detailed and informative response. Ensure that your answer is clear, concise, and directly addresses the question while being relevant to the context provided.

Your response should be in plain text and should not include any code blocks or extra formatting.

Answer:
""".strip()

question_template= """ 
questions={questions}
answer={answers}
""".strip()

def build_prompt(query, search_results):
    context=''
    for i in search_results:
        context= context + question_template.format(
            questions=i['Questions'],
            answers=i['Answers']
        ) + "\n\n"
    prompt= system_template.format(question=query, context=context).strip()
    return prompt

def llm(prompt, model='gpt-4o-mini'):
    response=client.chat.completions.create(
        model=model, 
        messages=[{'role': 'user', 'content':prompt}]
    )
    answer = response.choices[0].message.content
    usage= {
        "prompt_tokens": response.usage.prompt_tokens, 
        "completion_tokens": response.usage.completion_tokens,
        "total_tokens": response.usage.total_tokens,
    }
    return answer, usage

def calculate_openai_cost(model, tokens):
    openai_cost = 0

    if model == "gpt-4o-mini":
        openai_cost = (
            tokens["prompt_tokens"] * 0.00015 + tokens["completion_tokens"] * 0.0006
        ) / 1000
    else:
        print("Model not recognized. OpenAI cost calculation failed.")

    return openai_cost


eval_template=  """
You are an expert evaluator for a RAG system.
Your task is to analyze the relevance of the generated answer to the given question.
Based on the relevance of the generated answer, you will classify it
as "NON_RELEVANT", "PARTLY_RELEVANT", or "RELEVANT".

Here is the data for evaluation:

Question: {question}
Generated Answer: {answer}

Please analyze the content and context of the generated answer in relation to the question
and provide your evaluation in parsable JSON without using code blocks:

{{
  "Relevance": "NON_RELEVANT" | "PARTLY_RELEVANT" | "RELEVANT",
  "Explanation": "[Provide a summary for your evaluation]"
}}
""".strip()

def evaluate_results(question, answer):
    prompt=eval_template.format(question=question, answer=answer)
    evaluation, eval_usage= llm(prompt, model='gpt-4o-mini')

    try:
        json_eval= json.loads(evaluation)
    except json.JSONDecodeError:
        json_eval = {'Relevance': 'Unknown', 'Explanation': 'Failed to parse evaluation'}
    return json_eval, eval_usage

def rag(query, model='gpt-4o-mini'):
    t0 = time()
    search_results= search(query)
    prompt = build_prompt(query, search_results)
    answer, usage= llm(prompt, model=model)
    eval_result, eval_usage= evaluate_results(query, answer)

    t1 = time()
    response_time = t1 - t0

    openai_cost_rag = calculate_openai_cost(model, usage)
    openai_cost_eval = calculate_openai_cost(model, eval_usage)

    openai_cost = openai_cost_rag + openai_cost_eval

    response = {
        'answer': answer,
        'model_used': model,
        'response_time': response_time,
        'relevance': eval_result.get('Relevance', 'UNKNOWN'),
        'relevance_explanation': eval_result.get('Explanation', ''),
        'prompt_tokens': usage['prompt_tokens'],
        'completion_tokens': usage['completion_tokens'],
        'total_tokens': usage['total_tokens'],
        'eval_prompt_tokens': eval_usage['prompt_tokens'],
        'eval_completion_tokens': eval_usage['completion_tokens'],
        'eval_total_tokens': eval_usage['total_tokens'],
        'openai_cost': openai_cost,
    }
    return response
