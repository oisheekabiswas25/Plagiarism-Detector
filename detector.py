from __future__ import annotations

import argparse
import json
import math
import random
import re
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.metrics.pairwise import cosine_similarity, linear_kernel
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


WORD_RE = re.compile(r"[A-Za-z0-9']+")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
SPACE_RE = re.compile(r"\s+")
SUPPORTED_UPLOADS = {".txt", ".md", ".csv", ".pdf", ".docx", ".doc"}
MODEL_NAMES = ("svm", "rf", "lr", "knn")
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "is", "it",
    "of", "on", "or", "that", "the", "this", "to", "was", "with",
}
FEATURE_COLUMNS = [
    "cosine_similarity",
    "token_jaccard",
    "containment",
    "length_ratio",
    "shared_ngrams",
    "char_jaccard",
    "token_overlap",
]


def normalize_text(text: str) -> str:
    return SPACE_RE.sub(" ", text).strip()


def tokenize(text: str) -> list[str]:
    return WORD_RE.findall(text.lower())


def split_into_passages(text: str, max_sentences: int = 2, min_chars: int = 35) -> list[str]:
    sentences = [normalize_text(part) for part in SENTENCE_SPLIT_RE.split(text) if normalize_text(part)]
    if not sentences:
        return []

    passages: list[str] = []
    chunk: list[str] = []
    for sentence in sentences:
        chunk.append(sentence)
        joined = " ".join(chunk)
        if len(chunk) >= max_sentences or len(joined) >= 320:
            if len(joined) >= min_chars:
                passages.append(joined)
            chunk = []

    if chunk:
        joined = " ".join(chunk)
        if len(joined) >= min_chars:
            passages.append(joined)

    return passages or sentences[: min(3, len(sentences))]


def _qualifies(line: str, min_chars: int) -> bool:
    cleaned = normalize_text(line)
    if len(cleaned) < min_chars:
        return False
    letters = sum(char.isalpha() for char in cleaned)
    return letters >= max(10, math.ceil(len(cleaned) * 0.35))


def reservoir_sample_corpus(dataset_path: Path, max_records: int, min_chars: int, seed: int) -> list[str]:
    rng = random.Random(seed)
    sample: list[str] = []
    seen = 0
    dedupe: set[str] = set()

    with dataset_path.open("r", encoding="utf-8", errors="ignore") as handle:
        for raw_line in handle:
            line = normalize_text(raw_line)
            if not _qualifies(line, min_chars):
                continue
            if line in dedupe:
                continue

            seen += 1
            if len(sample) < max_records:
                sample.append(line)
                dedupe.add(line)
                continue

            index = rng.randint(0, seen - 1)
            if index < max_records:
                dedupe.discard(sample[index])
                sample[index] = line
                dedupe.add(line)

    return sample


def char_ngram_jaccard(left: str, right: str, n: int = 5) -> float:
    left = normalize_text(left.lower())
    right = normalize_text(right.lower())
    if len(left) < n or len(right) < n:
        return 1.0 if left == right and left else 0.0

    left_ngrams = {left[i : i + n] for i in range(len(left) - n + 1)}
    right_ngrams = {right[i : i + n] for i in range(len(right) - n + 1)}
    union = left_ngrams | right_ngrams
    return len(left_ngrams & right_ngrams) / len(union) if union else 0.0


def token_jaccard(left: list[str], right: list[str]) -> float:
    left_set = set(left)
    right_set = set(right)
    union = left_set | right_set
    return len(left_set & right_set) / len(union) if union else 0.0


def token_containment(left: list[str], right: list[str]) -> float:
    left_set = set(left)
    right_set = set(right)
    denominator = min(len(left_set), len(right_set))
    return len(left_set & right_set) / denominator if denominator else 0.0


def shared_ngram_ratio(left: list[str], right: list[str], n: int = 3) -> float:
    if len(left) < n or len(right) < n:
        return 0.0
    left_ngrams = {tuple(left[i : i + n]) for i in range(len(left) - n + 1)}
    right_ngrams = {tuple(right[i : i + n]) for i in range(len(right) - n + 1)}
    union = left_ngrams | right_ngrams
    return len(left_ngrams & right_ngrams) / len(union) if union else 0.0


def lexical_reduction_variant(text: str, rng: random.Random) -> str:
    tokens = tokenize(text)
    kept = [token for token in tokens if token not in STOPWORDS or rng.random() > 0.65]
    if len(kept) < 8:
        kept = tokens[: max(8, len(tokens) // 2)]
    return " ".join(kept)


def partial_copy_variant(text: str, rng: random.Random) -> str:
    tokens = tokenize(text)
    if len(tokens) < 10:
        return text
    start = rng.randint(0, max(0, len(tokens) // 5))
    end = rng.randint(max(start + 8, len(tokens) // 2), len(tokens))
    return " ".join(tokens[start:end])


def compute_pair_features(left: str, right: str, vectorizer: TfidfVectorizer) -> dict[str, float]:
    left_clean = normalize_text(left)
    right_clean = normalize_text(right)
    matrix = vectorizer.transform([left_clean, right_clean])
    cosine = float(cosine_similarity(matrix[0], matrix[1])[0][0])
    left_tokens = tokenize(left_clean)
    right_tokens = tokenize(right_clean)
    overlap = len(set(left_tokens) & set(right_tokens))

    return {
        "cosine_similarity": round(cosine, 6),
        "token_jaccard": round(token_jaccard(left_tokens, right_tokens), 6),
        "containment": round(token_containment(left_tokens, right_tokens), 6),
        "length_ratio": round(min(len(left_tokens), len(right_tokens)) / max(1, max(len(left_tokens), len(right_tokens))), 6),
        "shared_ngrams": round(shared_ngram_ratio(left_tokens, right_tokens), 6),
        "char_jaccard": round(char_ngram_jaccard(left_clean, right_clean), 6),
        "token_overlap": round(overlap / max(1, min(len(set(left_tokens)), len(set(right_tokens)))), 6),
    }


def generate_training_rows(corpus: list[str], vectorizer: TfidfVectorizer, seed: int) -> pd.DataFrame:
    rng = random.Random(seed)
    rows: list[dict] = []
    upper_bound = min(len(corpus), 1400)

    for index, source in enumerate(corpus[:upper_bound]):
        rows.append({"text_a": source, "text_b": source, "label": 1})
        rows.append({"text_a": lexical_reduction_variant(source, rng), "text_b": source, "label": 1})
        rows.append({"text_a": partial_copy_variant(source, rng), "text_b": source, "label": 1})

        negative_index = rng.randrange(len(corpus))
        while negative_index == index:
            negative_index = rng.randrange(len(corpus))
        rows.append({"text_a": source, "text_b": corpus[negative_index], "label": 0})

        negative_index_2 = rng.randrange(len(corpus))
        while negative_index_2 == index:
            negative_index_2 = rng.randrange(len(corpus))
        rows.append({"text_a": lexical_reduction_variant(source, rng), "text_b": corpus[negative_index_2], "label": 0})

    dataset = pd.DataFrame(rows)
    feature_frame = dataset.apply(
        lambda row: pd.Series(compute_pair_features(row["text_a"], row["text_b"], vectorizer)),
        axis=1,
    )
    return pd.concat([dataset, feature_frame], axis=1)


def train_classifiers(training_df: pd.DataFrame, output_dir: Path, seed: int) -> dict:
    X = training_df[FEATURE_COLUMNS]
    y = training_df["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=seed,
        stratify=y,
    )

    models = {
        "svm": make_pipeline(StandardScaler(), SVC(kernel="rbf", probability=True, random_state=seed)),
        "rf": RandomForestClassifier(n_estimators=220, max_depth=12, random_state=seed),
        "lr": make_pipeline(StandardScaler(), LogisticRegression(max_iter=1200, random_state=seed)),
        "knn": make_pipeline(StandardScaler(), KNeighborsClassifier(n_neighbors=7)),
    }

    report: dict[str, dict] = {}
    for name, model in models.items():
        model.fit(X_train, y_train)
        predictions = model.predict(X_test)
        probabilities = model.predict_proba(X_test)[:, 1] if hasattr(model, "predict_proba") else predictions

        metrics = {
            "accuracy": round(float(accuracy_score(y_test, predictions)), 4),
            "precision": round(float(precision_score(y_test, predictions)), 4),
            "recall": round(float(recall_score(y_test, predictions)), 4),
            "f1": round(float(f1_score(y_test, predictions)), 4),
            "mean_probability": round(float(np.mean(probabilities)), 4),
        }
        report[name] = metrics
        joblib.dump(model, output_dir / f"{name}.pkl")

    best_model = max(report.items(), key=lambda item: item[1]["f1"])[0]
    report["best_model"] = {"name": best_model}
    return report


def build_index_bundle(corpus: list[str], output_path: Path, max_features: int) -> dict:
    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words="english",
        ngram_range=(1, 2),
        min_df=2,
        max_features=max_features,
        sublinear_tf=True,
    )
    matrix = vectorizer.fit_transform(corpus)
    bundle = {
        "vectorizer": vectorizer,
        "matrix": matrix,
        "sources": corpus,
    }
    joblib.dump(bundle, output_path)
    return bundle


def compute_writing_metrics(text: str) -> dict:
    tokens = tokenize(text)
    sentences = [part for part in SENTENCE_SPLIT_RE.split(text) if normalize_text(part)]
    word_count = len(tokens)
    sentence_count = max(1, len(sentences))
    avg_sentence_length = round(word_count / sentence_count, 1)
    unique_words = len(set(tokens))
    lexical_diversity = round(unique_words / word_count, 3) if word_count else 0.0
    return {
        "word_count": word_count,
        "sentence_count": sentence_count,
        "character_count": len(text),
        "avg_sentence_length": avg_sentence_length,
        "lexical_diversity": lexical_diversity,
    }


def risk_label(score: float) -> str:
    if score >= 70:
        return "High Risk"
    if score >= 40:
        return "Moderate Risk"
    return "Low Risk"


def generate_suggestions(score: float, metrics: dict, flagged_count: int) -> list[str]:
    suggestions: list[str] = []
    if score >= 70:
        suggestions.append("The ML classifier sees very strong overlap patterns. Rewrite the highlighted sections and add citations.")
    elif score >= 40:
        suggestions.append("The document shows moderate plagiarism signals. Review the flagged passages carefully.")
    else:
        suggestions.append("Overall plagiarism risk is low, but citation is still needed wherever outside ideas are used.")

    if metrics["avg_sentence_length"] > 26:
        suggestions.append("Sentence length is high. Shorter sentences will improve clarity and make paraphrasing easier.")
    if metrics["lexical_diversity"] < 0.3:
        suggestions.append("Vocabulary repetition is noticeable. Vary wording to sound more original.")
    if flagged_count == 0:
        suggestions.append("No passage crossed the classifier threshold in the indexed corpus.")
    return suggestions[:4]


def extract_text_from_bytes(filename: str, payload: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_UPLOADS:
        raise ValueError(f"Unsupported file type: {suffix or 'unknown'}")

    if suffix == ".pdf":
        from PyPDF2 import PdfReader
        import io
        reader = PdfReader(io.BytesIO(payload))
        return "\n".join(page.extract_text() for page in reader.pages if page.extract_text())

    if suffix == ".docx":
        from docx import Document
        import io
        doc = Document(io.BytesIO(payload))
        return "\n".join(paragraph.text for paragraph in doc.paragraphs)

    if suffix == ".doc":
        import io
        from oletools.olefile import OleFileIO
        try:
            ole = OleFileIO(io.BytesIO(payload))
            if ole.exists("WordDocument"):
                doc_stream = ole.openstream("WordDocument")
                text = ""
                data = doc_stream.read()
                # Extract text chunks from Word 97-2003 binary format
                for chunk in data.split(b"\x00"):
                    try:
                        decoded = chunk.decode("utf-8", errors="ignore").strip()
                        if decoded and len(decoded) > 3:
                            text += decoded + "\n"
                    except:
                        pass
                ole.close()
                return text.strip() if text.strip() else "Unable to extract text from .doc file"
            ole.close()
        except Exception:
            pass
        return "Unable to extract text from .doc file"

    raw_text = payload.decode("utf-8", errors="ignore")
    if suffix == ".csv":
        return "\n".join(line.replace(",", " ") for line in raw_text.splitlines())
    return raw_text


def train_pipeline(
    dataset_path: str | Path,
    models_dir: str | Path,
    corpus_path: str | Path,
    dataset_csv_path: str | Path,
    max_records: int = 4000,
    min_chars: int = 45,
    max_features: int = 30000,
    seed: int = 42,
) -> dict:
    dataset = Path(dataset_path)
    models_dir = Path(models_dir)
    corpus_path = Path(corpus_path)
    dataset_csv_path = Path(dataset_csv_path)
    models_dir.mkdir(parents=True, exist_ok=True)

    corpus = reservoir_sample_corpus(dataset, max_records=max_records, min_chars=min_chars, seed=seed)
    corpus_path.write_text("\n".join(corpus), encoding="utf-8")

    index_bundle = build_index_bundle(corpus, models_dir / "plagiarism_index.joblib", max_features=max_features)
    training_df = generate_training_rows(corpus, index_bundle["vectorizer"], seed=seed)
    training_df.to_csv(dataset_csv_path, index=False)

    report = train_classifiers(training_df, output_dir=models_dir, seed=seed)
    metadata = {
        "dataset_path": str(dataset),
        "corpus_size": len(corpus),
        "training_rows": int(len(training_df)),
        "feature_columns": FEATURE_COLUMNS,
        "best_model": report["best_model"]["name"],
    }
    (models_dir / "training_report.json").write_text(
        json.dumps({"metadata": metadata, "models": report}, indent=2),
        encoding="utf-8",
    )
    return {"metadata": metadata, "report": report}


def required_artifacts_exist(base_dir: Path) -> bool:
    required = [
        base_dir / "models" / "plagiarism_index.joblib",
        base_dir / "models" / "svm.pkl",
        base_dir / "models" / "rf.pkl",
        base_dir / "models" / "lr.pkl",
        base_dir / "models" / "knn.pkl",
        base_dir / "corpus.txt",
        base_dir / "dataset.csv",
    ]
    return all(path.exists() for path in required)


def ensure_artifacts(base_dir: str | Path, max_records: int = 4000) -> None:
    base_path = Path(base_dir)
    if required_artifacts_exist(base_path):
        return
    train_pipeline(
        dataset_path=base_path / "dataset.txt",
        models_dir=base_path / "models",
        corpus_path=base_path / "corpus.txt",
        dataset_csv_path=base_path / "dataset.csv",
        max_records=max_records,
    )


class PlagiarismDetector:
    def __init__(self, base_dir: str | Path):
        base_path = Path(base_dir)
        ensure_artifacts(base_path)
        bundle = joblib.load(base_path / "models" / "plagiarism_index.joblib")
        self.vectorizer: TfidfVectorizer = bundle["vectorizer"]
        self.matrix = bundle["matrix"]
        self.sources: list[str] = bundle["sources"]
        self.models = {name: joblib.load(base_path / "models" / f"{name}.pkl") for name in MODEL_NAMES}
        report_path = base_path / "models" / "training_report.json"
        self.training_report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
        self.best_model = self.training_report.get("metadata", {}).get("best_model", "lr")

    def available_models(self) -> list[dict]:
        models = []
        metrics = self.training_report.get("models", {})
        for name in MODEL_NAMES:
            model_metrics = metrics.get(name, {})
            models.append(
                {
                    "name": name,
                    "label": name.upper(),
                    "f1": model_metrics.get("f1"),
                    "accuracy": model_metrics.get("accuracy"),
                }
            )
        return models

    def analyze_text(self, text: str, model_name: str | None = None, top_k: int = 5) -> dict:
        clean_text = normalize_text(text)
        if len(clean_text) < 40:
            raise ValueError("Please provide at least 40 characters of text to analyze.")

        chosen_model = model_name if model_name in self.models else self.best_model
        classifier = self.models[chosen_model]
        passages = split_into_passages(clean_text)
        query_matrix = self.vectorizer.transform(passages)
        similarity_matrix = linear_kernel(query_matrix, self.matrix)

        flagged_passages: list[dict] = []
        top_sources: dict[int, dict] = {}
        all_scores: list[float] = []

        for passage_index, passage in enumerate(passages):
            row = similarity_matrix[passage_index]
            best_idx = int(np.argmax(row))
            source_text = self.sources[best_idx]
            features = compute_pair_features(passage, source_text, self.vectorizer)
            frame = pd.DataFrame([features], columns=FEATURE_COLUMNS)
            probability = float(classifier.predict_proba(frame)[0][1])
            combined_score = (probability * 0.75) + (features["cosine_similarity"] * 0.25)
            
            # Track all scores for average calculation
            all_scores.append(combined_score)

            payload = {
                "passage": passage,
                "source_text": source_text,
                "source_index": best_idx,
                "ml_probability": round(probability * 100, 2),
                "cosine_score": round(features["cosine_similarity"] * 100, 2),
                "token_overlap": round(features["token_overlap"] * 100, 2),
                "combined_score": round(combined_score * 100, 2),
            }
            
            # Flag if exceeds threshold
            if combined_score >= 0.20:
                flagged_passages.append(payload)

            # Always track best sources
            previous = top_sources.get(best_idx)
            if previous is None or payload["combined_score"] > previous["combined_score"]:
                top_sources[best_idx] = payload

        metrics = compute_writing_metrics(clean_text)
        
        # Calculate plagiarism score as average of all passage scores
        plagiarism_score = round(float(np.mean(all_scores)) * 100, 2) if all_scores else 0.0

        ranked_sources = sorted(top_sources.values(), key=lambda item: item["combined_score"], reverse=True)[:top_k]

        return {
            "selected_model": chosen_model,
            "best_model": self.best_model,
            "plagiarism_score": plagiarism_score,
            "risk_level": risk_label(plagiarism_score),
            "metrics": metrics,
            "passage_count": len(passages),
            "flagged_count": len(flagged_passages),
            "flagged_passages": flagged_passages,
            "top_sources": ranked_sources,
            "suggestions": generate_suggestions(plagiarism_score, metrics, len(flagged_passages)),
            "available_models": self.available_models(),
            "training_summary": self.training_report.get("metadata", {}),
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the plagiarism detector ML + NLP pipeline.")
    parser.add_argument("--dataset", default="dataset.txt", help="Path to the raw corpus text file.")
    parser.add_argument("--models-dir", default="models", help="Directory for trained model artifacts.")
    parser.add_argument("--corpus-out", default="corpus.txt", help="Path for the sampled corpus output.")
    parser.add_argument("--dataset-out", default="dataset.csv", help="Path for the generated training dataset.")
    parser.add_argument("--max-records", type=int, default=4000, help="How many source lines to sample from the raw dataset.")
    parser.add_argument("--min-chars", type=int, default=45, help="Minimum characters required for source lines.")
    parser.add_argument("--max-features", type=int, default=30000, help="Maximum TF-IDF features for NLP vectorization.")
    args = parser.parse_args()

    report = train_pipeline(
        dataset_path=args.dataset,
        models_dir=args.models_dir,
        corpus_path=args.corpus_out,
        dataset_csv_path=args.dataset_out,
        max_records=args.max_records,
        min_chars=args.min_chars,
        max_features=args.max_features,
    )
    best_model = report["metadata"]["best_model"]
    print(f"Training complete. Best model: {best_model.upper()}")
    print(f"Corpus size: {report['metadata']['corpus_size']}")
    print(f"Training rows: {report['metadata']['training_rows']}")


if __name__ == "__main__":
    main()
