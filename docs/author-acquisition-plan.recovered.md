# Author Acquisition Plan (Recovered Draft)

This file was reconstructed from local shell history and current repository scripts after the original top-level `docs` folder was deleted.

## Evidence Used
- `rq "who is next author in author acquisition?"`
- `rq author acquisition, author downloads, scrape, beautiful soup`
- `python AugustineCorpus/scripts/download_author_works.py --author "Irenaeus of Lyons" --slug irenaeus --clean`
- `python AugustineCorpus/scripts/download_author_works.py --author "John Chrysostom"`
- `python AugustineCorpus/scripts/normalize_downloaded_texts.py ...`
- `python AugustineCorpus/scripts/generate_book_metadata.py ...`
- `python AugustineCorpus/preprocess_and_index.py --author <slug> --texts-root AugustineCorpus/texts`
- `python AugustineCorpus/scripts/index_author.py --author <slug> --texts-root AugustineCorpus/texts`
- `docker compose -f AugustineCorpus/docker-compose.corpus.yml --profile index run --rm indexer`

## Acquisition Workflow
1. Select next candidate author.
2. Download works into `AugustineCorpus/texts/<author_slug>_texts/` using `download_author_works.py`.
3. Normalize raw text files with `normalize_downloaded_texts.py` if needed.
4. Generate/update metadata with `generate_book_metadata.py`.
5. Build index for the author (`preprocess_and_index.py` or `scripts/index_author.py`).
6. Rebuild/restart corpus service and validate through `/v1/authors` and chat/context queries.

## Candidate Queue (Recovered)
- Irenaeus (`irenaeus`) was actively being onboarded.
- John Chrysostom was also targeted for download/indexing.

## Validation Checklist
- Author slug appears in `AugustineCorpus/author_index.json`.
- Text files exist and are non-empty in `AugustineCorpus/texts/<slug>_texts/`.
- Index artifacts exist for the slug.
- `curl http://localhost:8001/v1/authors` includes the slug.
- End-to-end query returns grounded citations.

## Notes
- This is a reconstructed recovery artifact, not a byte-for-byte restore of the deleted original plan.
- If remote hosts still have `~/Projects/pericopeai.com/docs`, copy those files back to replace this draft.
