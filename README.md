## FAQ Search Playground

This repo is a small work-in-progress project for trying out search over the
DataTalks.Club FAQ data.

Right now, the project has two main pieces:

- a small ingestion helper that downloads FAQ documents and can build a simple
  text index with `minsearch`
- a notebook where the FAQ entries are turned into embeddings with
  `sentence-transformers` and searched with plain vector similarity

So this is already beyond an empty scaffold, but it is still an experiment
more than a finished app.

## What is already done

### 1. FAQ data loading

`ingest.py` fetches the course FAQ catalog from DataTalks.Club, follows each
course path, and combines all FAQ entries into one Python list of documents.

Each document is expected to contain fields such as:

- `question`
- `answer`
- `section`
- `course`

### 2. A basic searchable index

`ingest.py` also includes a `build_index(documents)` helper built on top of
`minsearch`.

The index is configured with:

- text fields: `question`, `section`, `answer`
- keyword field: `course`

That gives the project a simple non-vector search layer for the FAQ data.

### 3. Embedding experiment in the notebook

`demo.ipynb` is where most of the current exploration happens.

At the moment the notebook:

1. loads the `all-MiniLM-L6-v2` sentence-transformer model
2. encodes sample questions and answers
3. downloads the FAQ data through `load_faq_data()`
4. builds text strings from each FAQ entry
5. creates embeddings in batches
6. stores them in a NumPy array
7. scores a query against all stored vectors with a dot product
8. prints the best matching FAQ entries

In short: the vector-search idea is already being tested end to end in the
notebook.

## Project structure

```text
.
|-- demo.ipynb      # embedding and similarity-search experiments
|-- ingest.py       # FAQ download + index-building helpers
|-- main.py         # tiny placeholder entry point
|-- pyproject.toml  # project metadata and dependencies
|-- uv.lock         # locked dependency versions
```

## Dependencies in use

The project is set up for Python 3.12 and currently includes packages such as:

- `requests` for downloading FAQ data
- `minsearch` for a lightweight keyword index
- `sentence-transformers` for embeddings
- `numpy` and `jupyter` for notebook work

There are also dependencies like `openai`, `ollama`, and `python-dotenv`
already listed, but they are not wired into the Python files yet.

## How to run it

If you are using `uv`:

```bash
uv sync
uv run python main.py
uv run jupyter notebook
```

If you prefer plain `pip`, install the dependencies from `pyproject.toml` in
your usual environment and then open the notebook or run the Python files.

## Current state

This repo currently looks like an early-stage vector search lab:

- data ingestion is in place
- a basic keyword index helper exists
- embedding-based retrieval is working in the notebook
- a polished CLI or app interface has not been built yet

## Good next steps

If you continue this project, the most natural next moves would be:

- move the notebook logic into reusable Python functions
- save embeddings instead of recomputing them every session
- add a proper search function that returns the top-k results
- compare keyword search vs vector search on the same queries
- plug the retrieval step into an LLM-based Q&A flow