import pytest

from explainer.compose.subtitles import build_cues, wrap_korean, write_ass, write_srt
from explainer.narration.timeline import SegmentTiming, Timeline
from explainer.narration.tts import NarrationClip, Sentence, _sentences_from_marks, _sentences_from_words, split_sentences


def _clip(text, sentences, duration):
    return NarrationClip(text=text, audio_path="x.mp3", duration=duration, sentences=sentences)


def test_split_sentences_korean():
    s = split_sentences("첫 문장입니다. 두 번째 문장! 세 번째?")
    assert s == ["첫 문장입니다.", "두 번째 문장!", "세 번째?"]


def test_sentences_from_marks_uses_tts_boundaries():
    marks = [
        {"text": "첫 문장입니다.", "start": 0.1, "end": 2.0},
        {"text": "두 번째 문장.", "start": 2.3, "end": 4.0},
    ]
    sents = _sentences_from_marks("첫 문장입니다. 두 번째 문장.", marks, 4.5)
    assert [s.text for s in sents] == ["첫 문장입니다.", "두 번째 문장."]
    assert sents[0].start == 0.0 and sents[0].end == 2.3  # 다음 문장 시작까지 이어짐
    assert sents[-1].end == 4.5


def test_sentences_fallback_even_split():
    sents = _sentences_from_words("가. 나. 다.", [], 3.0)
    assert len(sents) == 3
    assert sents[1].start == pytest.approx(1.0)


def test_resolve_at_numeric_and_sentence_index():
    clip = _clip("a. b. c.", [Sentence("a.", 0, 1.5), Sentence("b.", 1.5, 3.0), Sentence("c.", 3.0, 4.0)], 4.0)
    seg = SegmentTiming(id="s", narration="a. b. c.", clip=clip, pad=0.5)
    assert seg.resolve_at(None) == 0.0
    assert seg.resolve_at(2.25) == 2.25
    assert seg.resolve_at("s2") == 1.5
    assert seg.resolve_at("s99") == 3.0  # 범위를 넘으면 마지막 문장
    with pytest.raises(ValueError):
        seg.resolve_at("nonsense")


def test_wrap_korean_balances_two_lines():
    text = "이것은 자막 줄바꿈 테스트를 위한 상당히 긴 한국어 문장입니다 정말로"
    wrapped = wrap_korean(text, max_chars=20)
    lines = wrapped.split("\n")
    assert len(lines) == 2
    assert abs(len(lines[0]) - len(lines[1])) <= 8
    assert wrap_korean("짧은 문장", 20) == "짧은 문장"


def test_build_cues_offsets_by_segment_start_and_no_overlap(tmp_path):
    tl = Timeline(
        segments=[
            SegmentTiming("a", "x", _clip("x", [Sentence("첫째.", 0, 2.0), Sentence("둘째.", 2.0, 4.0)], 4.0), 0.5, start=1.0, end=5.5),
            SegmentTiming("b", "y", _clip("y", [Sentence("셋째.", 0, 3.0)], 3.0), 0.5, start=5.5, end=9.0),
        ]
    )
    cues = build_cues(tl)
    assert [c.text for c in cues] == ["첫째.", "둘째.", "셋째."]
    assert cues[0].start == 1.0 and cues[1].start == 3.0 and cues[2].start == 5.5
    for prev, nxt in zip(cues, cues[1:]):
        assert nxt.start >= prev.end - 1e-9

    srt = write_srt(cues, tmp_path / "s.srt").read_text(encoding="utf-8")
    assert "00:00:01,000 --> 00:00:02,950" in srt  # 다음 큐와 min_gap(0.05s) 만큼 띄움
    ass = write_ass(cues, tmp_path / "s.ass").read_text(encoding="utf-8")
    assert "Dialogue: 0,0:00:01.00,0:00:02.95" in ass
    assert "Noto Sans CJK KR" in ass
