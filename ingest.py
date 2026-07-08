"""Helpers for downloading FAQ data and preparing a small search index."""

import requests
from minsearch import Index


def load_faq_data():
    """Fetch all FAQ entries from the DataTalks.Club course catalog."""

    docs_url = "https://datatalks.club/faq/json/courses.json"
    response = requests.get(docs_url)
    response.raise_for_status()
    courses_raw = response.json()

    documents = []
    url_prefix = "https://datatalks.club/faq"

    for course in courses_raw:
        # Each course entry contains a relative path to its own FAQ JSON file.
        course_url = f"{url_prefix}{course['path']}"
        course_response = requests.get(course_url)
        course_response.raise_for_status()
        course_data = course_response.json()

        # Keep one flat list so the rest of the project can search everything
        # without caring which course a document originally came from.
        documents.extend(course_data)

    return documents


def build_index(documents):
    """Build a lightweight keyword index over the FAQ documents."""

    index = Index(
        text_fields=["question", "section", "answer"],
        keyword_fields=["course"],
    )
    index.fit(documents)
    return index