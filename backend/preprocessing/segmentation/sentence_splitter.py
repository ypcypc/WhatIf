import spacy

from core.models import Sentence, SentenceData


_nlp = None


def _get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("zh_core_web_sm")
    return _nlp


def split_sentences(text: str) -> SentenceData:
    nlp = _get_nlp()
    doc = nlp(text)

    sentences = []
    for sent in doc.sents:
        sentence_text = sent.text.strip()
        if sentence_text:
            sentences.append(
                Sentence(
                    index=len(sentences) + 1,
                    text=sentence_text,
                    start=sent.start_char,
                    end=sent.end_char,
                )
            )

    return SentenceData(
        total_sentences=len(sentences),
        total_characters=len(text),
        sentences=sentences,
    )
