# LegalLens

**Private legal document triage.** Upload a contract, see the red flags instantly, ask questions, and get plain-language answers with the exact clause behind each one. The clause is checked against your PDF and highlighted in the text.

Everything runs on your own computer using a local model through [Ollama](https://ollama.com). Your contracts are never uploaded anywhere.

> ⚖️ LegalLens is an AI triage aid, **not legal advice**. Have a qualified lawyer check anything important.

<!-- Add a screenshot: save it as docs/screenshot.png and uncomment the next line -->
<!-- ![LegalLens screenshot](docs/screenshot.png) -->

## Features

- **Quick scan:** instant, rule-based highlights of risky wording (automatic renewal, penalties, non-compete, one-sided changes, and more) plus key money amounts, time periods and dates. No AI involved, so it is immediate and repeatable.
- **Ask questions:** get a Low, Medium or High risk verdict with a short explanation. Leave the question blank for a full triage.
- **Quote checking:** the clause the model quotes is searched for word for word in your PDF. If it isn't there, the answer is flagged as unverified.
- **Evidence highlighting:** verified quotes are highlighted in the contract viewer, which jumps to the right page.
- **Session history and reports:** every question you ask is kept for the session. Download everything as a Markdown file or a printable web page (save it as PDF from your browser).
- **Law library (optional):** fetch Acts, regulations and court judgments from the Open India Law dataset and open them in the app. The model is told it is reading a law or a judgment, not a contract.
- **Model picker:** choose any model you have installed in Ollama from the sidebar.
- **Sample contract:** no contract handy? Click "Try the sample" to explore the app with a fictional agreement.
- **Works on long contracts:** the document is split into chunks and the most relevant ones are sent to the model, so clauses deep in the document are not silently dropped.
- **Stays on topic:** questions that are not about the document are rejected.
- **Clear errors:** password-protected, corrupted and scanned PDFs get a helpful message instead of a crash.
- **Safer wording:** for a high-risk clause in a contract, a button drafts balanced replacement wording to discuss with a lawyer.
- **Benchmark script:** `evaluate_cuad.py` runs the app over CUAD contracts (or the law library with `--library`) and reports how many quotes were verified and how often it agrees with the expert labels.
- **Private by design:** the app makes no third-party requests, not even for fonts.

## Requirements

- Python 3.10 or newer
- [Ollama](https://ollama.com/download)
- The `gemma2:2b` model (about 1.6 GB)

## Quick start

### Option 1: one-click launcher

- **Windows:** double-click `run.bat`
- **macOS / Linux:** run `./run.sh`

The launcher creates a virtual environment, installs the packages, starts Ollama, downloads the model if needed and opens the app.

### Option 2: manual setup

```bash
# 1. Clone the repository
git clone https://github.com/YOUR-USERNAME/LegalLens.git
cd LegalLens

# 2. (Recommended) create a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

# 3. Install the Python packages
pip install -r requirements.txt

# 4. Download the model
ollama pull gemma2:2b

# 5. Start the app
streamlit run app.py
```

The app opens at `http://localhost:8501`.

> Use `streamlit run app.py`, not `python app.py`. A Streamlit app needs the Streamlit runtime to show its interface.

## Using the app

1. Upload a contract as a PDF, or click **Try the sample**.
2. Open **Quick scan** for an instant checklist of risky wording and key facts.
3. Open **Ask**, type a question or pick a quick question, then click **Answer question** (or **Run full triage** with an empty box).
4. Read the verdict and analysis, then check the quoted clause. A green badge means the wording was found in your PDF. A red badge means it was not, so treat the answer as unverified.
5. Open **Report** to review your session and download it.

## Law library (optional)

Contracts are what LegalLens reads. Laws and judgments are useful context, so you can also open them from a **Law library** list in the sidebar. This needs a one-time download, and the app works without it.

```bash
pip install -r requirements-data.txt
huggingface-cli login        # and accept the conditions on the dataset page

# 3 Acts whose title contains "Contract"
python fetch_open_india_law.py --kind legislation --title-contains "Contract" --limit 3

# 3 SEBI regulations
python fetch_open_india_law.py --kind regulations --file in_sebi_regulations.parquet --limit 3

# 3 Kerala High Court judgments
python fetch_open_india_law.py --kind judgments --file in_kerala_judgments.parquet --limit 3
```

The script streams only the rows it needs (the full dataset is about 54 GB), joins them into documents and saves PDFs to `datasets/open_india_law/<kind>/`. Reload the app and pick one under **Law library**. You can also upload any law PDF yourself and tell the app what kind of document it is.

- Data: [Open India Law](https://huggingface.co/datasets/vaquill/open-india-law) by Vaquill AI, CC BY 4.0, snapshot v2026.08. Keep credit to the source if you publish results. The `datasets/` folder is git-ignored.
- It is a point-in-time archive, **not current law**. Check the official source before relying on it.
- The fetch script has not been run against the live dataset by the author of this README, so if a column name differs it prints the columns it saw; adjust `DOC_KEYS` and `TEXT_KEYS` at the top of the script.
- The PDF font covers Latin characters only, so Hindi or other scripts inside a judgment appear as `?`.

## Evaluating on CUAD

[CUAD](https://github.com/The-Atticus-Project/cuad) has 510 commercial contracts with expert clause labels (CC BY 4.0, cite the NeurIPS 2021 paper). Unzip `data.zip` into `datasets/cuad/`, then:

```bash
python evaluate_cuad.py --pdf-dir datasets/cuad/full_contract_pdf --labels datasets/cuad/master_clauses.csv --limit 20
```

Results go to `results/cuad_results.csv` and `results/cuad_summary.md`.

To test the Open India Law documents you fetched (Acts, regulations, judgments) instead, add `--library`:

```bash
python evaluate_cuad.py --library --limit 5
```

This writes `results/law_results.csv` and `results/law_summary.md`. It passes each document's type to the model and reports quote verification and "not found" rates. These documents have no expert labels, so there is no label agreement. Start with `--limit 3`: every contract is asked six questions, which is slow on CPU. These are commercial contracts, so the numbers say nothing about rental or employment documents.

## How it works

1. `doc_parser.py` reads the PDF page by page and cleans the text.
2. `scanner.py` runs keyword rules over the text for the quick scan.
3. `ai_agent.py` splits the text into chunks, picks the ones that best match your question, and asks the local model for an analysis in a fixed format. It then checks that the quoted clause really appears in the PDF.
4. `app.py` and `ui_helpers.py` display the verdict, evidence and highlighted contract.
5. `report.py` turns the scan and your questions into a downloadable report.
6. `library.py` lists the PDFs in the law library and tells the app whether each is an Act, a regulation or a judgment. `fetch_open_india_law.py` fills that library.

## Project structure

```
LegalLens/
├── app.py                  Streamlit app: layout, tabs and flow
├── ui_helpers.py           Styling, HTML builders and answer parsing
├── ai_agent.py             Chunking, retrieval, Ollama calls, quote verification
├── doc_parser.py           PDF text extraction and error handling
├── scanner.py              Rule-based red-flag and key-fact scan
├── report.py               Markdown and HTML report builders
├── library.py              Lists the local law library (Acts, regulations, judgments)
├── fetch_open_india_law.py Streams documents from Open India Law and saves them as PDFs
├── evaluate_cuad.py        Benchmark: CUAD contracts, or the law library with --library
├── datasets/               Downloaded data (git-ignored)
├── samples/
│   ├── sample_contract.pdf Fictional contract for trying the app
│   └── sample_queries.md   Test questions and expected answers
├── tests/
│   └── test_core.py        Offline tests
├── .github/workflows/
│   └── tests.yml           Runs the tests on every push
├── .streamlit/config.toml  Light theme
├── run.bat / run.sh        One-click launchers
├── requirements.txt        App dependencies
├── requirements-dev.txt    App plus test dependencies
└── requirements-data.txt   Extra packages for fetch_open_india_law.py
```

## Running the tests

The tests need neither Ollama nor a browser.

```bash
pip install -r requirements-dev.txt
pytest
```

They also run automatically on GitHub for every push and pull request.

## Configuration

Settings live at the top of `ai_agent.py`:

| Setting | Default | Purpose |
|---|---|---|
| `MODEL` | `gemma2:2b` | Default model, also selectable in the sidebar |
| `OPTIONS` | temperature `0.0`, seed `42`, `num_ctx` 4096 | Generation settings; temperature 0 makes output repeatable |
| `CHUNK_CHARS` | `1000` | Size of each text chunk |
| `CONTEXT_BUDGET` | `7000` | Maximum characters of contract text sent to the model |

To tune the quick scan, edit the `FLAGS` list in `scanner.py`. Each entry is a topic, a priority, a plain-language reason and a pattern.

For a larger model, run `ollama pull <model>`, pick it in the sidebar, and raise `num_ctx` and `CONTEXT_BUDGET` if your hardware allows.

## Limitations

- **Scanned PDFs are not supported.** The app needs a text layer. Run scans through OCR first, for example `ocrmypdf in.pdf out.pdf`.
- **The quick scan matches wording, not meaning.** It can flag a harmless sentence or miss an unusual phrasing.
- **Retrieval is keyword-based.** A question worded very differently from the contract can miss the right passage.
- **A 2B model makes mistakes.** It can misread clauses, misjudge risk, or wrongly reject a valid question. The quote check proves a quote is real, not that the interpretation is right.
- **Long documents are partly read.** When a contract is bigger than the model's working window, the app warns you which pages were analysed.
- **Laws and judgments are not contracts.** The Quick scan looks for contract wording, and the risk level for a law means risk to the person affected. Judgments are long and will often exceed the model's window.
- **Law data is a snapshot,** not current law, and is not legal advice.
- **English documents work best.**

## Troubleshooting

| Problem | Fix |
|---|---|
| "Cannot reach Ollama" | Start Ollama with `ollama serve` |
| "No model is installed" | Run `ollama pull gemma2:2b` |
| `streamlit` is not recognised | Use `python -m streamlit run app.py` |
| "No extractable text found" | The PDF is scanned. Run OCR on it first |
| "Could not open the dataset" when fetching | Run `huggingface-cli login` and accept the conditions on the dataset page |
| Law library list is empty | Run `fetch_open_india_law.py` first, then reload the app |
| Analysis is slow | Small models on CPU can take a minute. A GPU or a smaller context helps |

## Contributing

Issues and pull requests are welcome. Please run `pytest` before opening a pull request. For larger changes, open an issue first to discuss what you would like to change.

## License

Add a license before sharing the project publicly, for example [MIT](https://choosealicense.com/licenses/mit/).

### Data credits

- [CUAD](https://www.atticusprojectai.org/cuad): Hendrycks et al., NeurIPS 2021, CC BY 4.0.
- [Open India Law](https://huggingface.co/datasets/vaquill/open-india-law): Vaquill AI, CC BY 4.0. The underlying legal text is a Government work.
