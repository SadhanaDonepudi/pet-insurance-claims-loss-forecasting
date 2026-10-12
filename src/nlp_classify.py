"""NLP classification of synthetic claim notes into 12 condition categories.

Pipeline: TF-IDF (word 1-2 grams) -> multinomial logistic regression.
Evaluated on a stratified 80/20 holdout; accuracy is the MEASURED test
accuracy reported in the README.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from . import config as C


def build_pipeline() -> Pipeline:
    return Pipeline([
        ("tfidf", TfidfVectorizer(
            max_features=C.NLP_MAX_FEATURES,
            ngram_range=C.NLP_NGRAMS,
            min_df=3,
            sublinear_tf=True,
            stop_words="english",
        )),
        ("clf", LogisticRegression(
            max_iter=1000,
            C=1.0,
            solver="lbfgs",  # multinomial by default on modern sklearn
            random_state=C.SEED,
        )),
    ])


def train_and_evaluate(notes: pd.DataFrame) -> dict:
    X = notes["note_text"].to_numpy()
    y = notes["category"].to_numpy()
    assert set(np.unique(y)) == set(C.CONDITION_NAMES), "category set mismatch"

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=C.NLP_TEST_SIZE, random_state=C.SEED, stratify=y)

    pipe = build_pipeline()
    pipe.fit(X_train, y_train)
    y_pred = pipe.predict(X_test)
    acc = accuracy_score(y_test, y_pred)

    labels = sorted(C.CONDITION_NAMES)
    return {
        "model": "TF-IDF (1-2 grams) + multinomial logistic regression",
        "n_notes": int(len(notes)),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "n_categories": int(len(labels)),
        "categories": labels,
        "accuracy": float(acc),
        "confusion_matrix": confusion_matrix(y_test, y_pred,
                                             labels=labels).tolist(),
        "classification_report": classification_report(
            y_test, y_pred, labels=labels, output_dict=True, zero_division=0),
    }
