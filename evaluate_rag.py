import os
import csv
import traceback
import time
import pandas as pd
from datasets import Dataset
from ragas import evaluate, EvaluationDataset
from ragas.metrics import faithfulness, answer_relevancy
from ragas.llms import llm_factory
from ragas.embeddings import embedding_factory
from openai import OpenAI
from dotenv import load_dotenv
from app.rag_service import get_answer
from app.retrieval import retrieve_context_with_vector, embed_query
from app.config import OPENAI_API_KEY

# ── Environment Setup ─────────────────────────────────────────────────────────
load_dotenv()

if not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

_ragas_llm = llm_factory("gpt-4o-mini", client=client)


_ragas_embeddings = embedding_factory(
    "openai", 
    model="text-embedding-3-small", 
    client=client
)

# ── Test Questions ────────────────────────────────────────────────────────────
# TEST_QUESTIONS = [
#     # --- Category 1: Direct Factual Retrieval (Easy) ---
#     "What is the full address of the Digital Brolly headquarters?",
#     "Who is the founder of Digital Brolly?",
#     "How many years of experience does Ravi Varma have?",
#     "What is the total fee for the BDLP program?",
#     "Who is Ambika Kiran and what is her role?",
#     "Does Digital Brolly offer live online training?",

#     # --- Category 2: Hybrid Search & Keyword Precision (Testing Sparse/BM25) ---
#     # These test if the bot finds specific tools and award titles exactly.
#     "Who exactly received the Business Icon Award?",
#     "Do you teach WP Hide and Wordfence Security?",
#     "What is the total fee for the BDDP?",  # Harder to distinguish from BDCP/BDLP
#     "Does the Brolly Agency offer services, or is it just a training institute?",
#     "Is there a program that involves a Deemed University?",

#     # --- Category 3: Multi-Query Expansion (Testing Vague/Short Queries) ---
#     # These test if your expansion logic understands "lazy" student typing.
#     "cost of career prog",
#     "internship diffs",
#     "tools for ai",
#     "JNTU metro branch details",
#     "ambika placements",

#     # --- Category 4: Multi-Hop & Comparative (Medium) ---
#     "What is the exact difference in internship duration and placement support between BDLP and BDCP?",
#     "If I want a University Diploma Certificate, which course should I take and how much does it cost?",
#     "Compare the teaching philosophy of Ravi Varma with the teaching methodology of Ambika Kiran.",
#     "Which courses guarantee placement versus just offering placement assistance?",
#     "What are the specific differences in the final outcomes of the BDDP versus the BDMP programs?",

#     # --- Category 5: Formatting & System Prompt Compliance (Hard) ---
#     "List all the core modules covered in the curriculum.",
#     "Name at least 5 AI tools and 3 SEO tools taught in the courses.",
#     "What are the 6 steps in Ambika Kiran's placement support workflow?",
#     "Which universities does Digital Brolly collaborate with?",
#     "Tell me about the BDCP course.",

#     # --- Category 6: Multilingual & Transliteration (Stress Test) ---
#     "BDCP course duration entha?",
#     "Mujhe BDMP course ki details batao, fee kitna hai?",
#     "డిజిటల్ బ్రోల్లీ ఎక్కడ ఉంది?",
#     "डिजिटल ब्रोली में कौन से कोर्स उपलब्ध हैं?",
#     "hi hello",

#     # --- Category 7: Out-of-Bounds & Fallback Triggers ---
#     "Do you offer training in Python Data Science or Full Stack Web Development?",
#     "What are the exact timings for the weekend offline batches?",
#     "Can I get a refund if I drop out after 1 month?",
#     "Who is the CEO of Google?",
#     "Does Ravi Varma have a degree from IIT?",

#     # --- Category 8: Trick Questions & Logic Traps ---
#     "Since BDLP has an internship, does it come with a 100% placement guarantee?",
#     "Is it true that Digital Brolly focuses 80% on theory and 20% on practical implementation?",
#     "I am looking for a 6-month course that costs ₹50,000 total, which one is that?",
#     "Does the institute teach advanced coding languages like Java and C++?",

#     # --- Category 9: Semantic Cache Tests (Fresh API calls, no history) ---
#     # These should be run to check if the 2nd and 3rd return identical answers to the 1st.
#     "What is the price of the Brolly Digital Marketing Launchpad?",
#     "How much do I have to pay for the BDLP?",
#     "BDLP course fee details"
# ]

TEST_QUESTIONS = [
    "address?",
    "Tell me the location",
    "location?",
    "What is the address of the location?",
    "what is the address?"
]
# ── Intermediate Results CSV ──────────────────────────────────────────────────
INTERMEDIATE_CSV = "rag_intermediate_results.csv"
FINAL_CSV        = "rag_evaluation_report.csv"
FAILED_CSV       = "rag_failed_questions.csv"


def _init_intermediate_csv():
    """Create the intermediate CSV with headers if it does not exist yet."""
    if not os.path.exists(INTERMEDIATE_CSV):
        with open(INTERMEDIATE_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=["question", "answer", "contexts", "ground_truth"]
            )
            writer.writeheader()


def _append_intermediate_row(row: dict):
    """Append a single processed row so progress is not lost on crash."""
    with open(INTERMEDIATE_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["question", "answer", "contexts", "ground_truth"]
        )
        writer.writerow(row)


def _split_context(raw_context: str) -> list[str]:
    """
    Split raw context into chunks for RAGAS.
    Falls back gracefully if the expected delimiter is absent.
    """
    if not raw_context:
        return [""]
    chunks = [c.strip() for c in raw_context.split("\n\n") if c.strip()]
    return chunks if chunks else [raw_context]


# ── Main Evaluation ───────────────────────────────────────────────────────────
def run_evaluation():
    print("🚀 Starting RAGAS Evaluation for Brolly Microservice...")

    _init_intermediate_csv()

    data_samples = {
        "question":     [],
        "answer":       [],
        "contexts":     [],
        # ground_truth is not required by Faithfulness / AnswerRelevancy;
        # kept as empty strings so the Dataset schema stays consistent and
        # can be extended with AnswerCorrectness later without restructuring.
        "ground_truth": [],
    }

    failed_questions = []

    for idx, question in enumerate(TEST_QUESTIONS, start=1):
        print(f"[{idx}/{len(TEST_QUESTIONS)}] Processing: '{question}'")
        try:
            # 1. Embed the query
            query_vector = embed_query(question)

            # 2. Retrieve context — safely unpack regardless of return type
            retrieval_result = retrieve_context_with_vector(query_vector)
            if isinstance(retrieval_result, tuple):
                raw_context = retrieval_result[0]
            else:
                raw_context = retrieval_result  # handle plain-string return

            contexts_list = _split_context(raw_context)

            # 3. Get RAG answer — fresh history list each iteration
            answer = get_answer(question, history=[])

            time.sleep(2)

            # 4. Store result
            row = {
                "question":     question,
                "answer":       answer,
                "contexts":     str(contexts_list),  
                "ground_truth": "",
            }
            _append_intermediate_row(row)

            data_samples["question"].append(question)
            data_samples["answer"].append(answer)
            data_samples["contexts"].append(contexts_list)
            data_samples["ground_truth"].append("")

        except Exception as e:
            print(f"  ⚠️  Failed for question: '{question}'\n  Reason: {e}")
            traceback.print_exc()
            failed_questions.append({"question": question, "error": str(e)})
            # Skip this question — do not let one failure abort the full run
            continue

    if not data_samples["question"]:
        print("❌ No questions were processed successfully. Aborting evaluation.")
        return

    # ── Save failed questions ─────────────────────────────────────────────────
    if failed_questions:
        pd.DataFrame(failed_questions).to_csv(FAILED_CSV, index=False)
        print(f"\n⚠️  {len(failed_questions)} question(s) failed. See '{FAILED_CSV}'.")

    # ── RAGAS Evaluation ──────────────────────────────────────────────────────
    print(f"\n📊 Running LLM-as-a-judge evaluation on "
          f"{len(data_samples['question'])} questions...")

    dataset = Dataset.from_dict(data_samples)

    # llm     → GPT-4o-mini judges faithfulness and relevancy
    # embeddings → app's own MiniLM model computes semantic similarity
    faithfulness.llm = _ragas_llm
    answer_relevancy.llm = _ragas_llm
    answer_relevancy.embeddings = _ragas_embeddings

    results = evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy],
    )

    # ── Export Results ────────────────────────────────────────────────────────
    # Guard against API changes in RAGAS versions
    if hasattr(results, "to_pandas"):
        df = results.to_pandas()
    else:
        df = pd.DataFrame(results)

    df.to_csv(FINAL_CSV, index=False)

    print("\n✅ Evaluation Complete!")
    print("─" * 40)
    print(results)
    print(f"\n📁 Detailed report   → '{FINAL_CSV}'")
    print(f"📁 Intermediate data → '{INTERMEDIATE_CSV}'")
    if failed_questions:
        print(f"📁 Failed questions  → '{FAILED_CSV}'")


if __name__ == "__main__":
    run_evaluation()