import os
import sys

sys.path.append(os.path.abspath(".."))

from part_1_RAG.ingest import load_faq_data, build_index
from part_1_RAG.rag_helper import RAGBase

from metrics import RAGWithMetrics
from openai import OpenAI

from db_save import save_conversation


def create_assistant():
    
    documents = load_faq_data()
    index = build_index(documents)

    return RAGWithMetrics(
        index=index,
        llm_client=OpenAI(
            base_url="http://localhost:11434/v1",
            api_key="ollama"  # required by the SDK but ignored by Ollama
        ),
    )







if __name__ == "__main__":
    sys.path.append(os.path.abspath(".."))

    assistant = create_assistant()

    query = "How do I join the course?"
    if len(sys.argv) > 1:
        query = sys.argv[1]

    answer = assistant.rag(query)

    save_conversation(assistant.last_call, query, "llm-zoomcamp")

    print(answer)
