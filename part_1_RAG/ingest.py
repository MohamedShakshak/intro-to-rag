import requests
from minsearch import Index
from elasticsearch import Elasticsearch


def load_faq_data():
    docs_url = "https://datatalks.club/faq/json/courses.json"
    response = requests.get(docs_url)
    courses_raw = response.json()

    documents = []
    url_prefix = "https://datatalks.club/faq"

    for course in courses_raw:
        course_url = f"""{url_prefix}{course["path"]}"""
        course_response = requests.get(course_url)
        course_response.raise_for_status()
        course_data = course_response.json()

        documents.extend(course_data)

    return documents

def build_index(documents):
    index = Index(
        text_fields=["question", "section", "answer"],
        keyword_fields=["course"]
    )
    index.fit(documents)
    return index


def build_es_index(documents):
    es = Elasticsearch("http://localhost:9200")
    INDEX_NAME = "course-faq"
    if es.indices.exists(index=INDEX_NAME):
        es.indices.delete(index=INDEX_NAME)

    mappings = {
        "properties": {
            "question": {"type": "text"},
            "answer": {"type": "text"},
            "section": {"type": "text"},
            "course": {"type": "keyword"}
        }
    }

    es.indices.create(
        index=INDEX_NAME,
        mappings=mappings
    )

    for doc in documents:
        es.index(
            index=INDEX_NAME,
            document=doc
        )

    return es
