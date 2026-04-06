"""
AIService — AI-powered text tools.

Primary: Groq API (Llama 3.3 70B) for context-aware generation.
Fallback: YAKE keyword extraction for offline / no-key usage.
"""

import asyncio
import logging
import re
from collections.abc import Callable

import yake
from groq import APIError, APITimeoutError, AsyncGroq

from app.core.config import settings

logger = logging.getLogger(__name__)

_MODEL = "llama-3.3-70b-versatile"


# ── Groq helpers ──────────────────────────────────────────────────────────────

_groq_client: AsyncGroq | None = None


def init_groq_client() -> None:
    """Initialize the Groq client (called from FastAPI lifespan)."""
    global _groq_client
    if settings.GROQ_API_KEY:
        _groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY, timeout=30.0)


async def close_groq_client() -> None:
    """Close the Groq client (called from FastAPI lifespan)."""
    global _groq_client
    if _groq_client is not None:
        await _groq_client.close()
        _groq_client = None


async def _groq_chat(
    system_prompt: str,
    user_text: str,
    temperature: float = 0.7,
    max_tokens: int = 200,
) -> str:
    """Shared Groq chat helper."""
    client = _groq_client
    response = await client.chat.completions.create(
        model=_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()


async def _ai_transform(
    system_prompt: str,
    text: str,
    fallback_fn: Callable[..., str],
    *fallback_args,
    temperature: float = 0.7,
    max_tokens: int = 200,
) -> str:
    """Unified AI transform: try Groq, fall back to local function."""
    if settings.GROQ_API_KEY:
        try:
            async with asyncio.timeout(35):
                return await _groq_chat(system_prompt, text, temperature, max_tokens)
        except (TimeoutError, APIError, APITimeoutError):
            logger.exception("Groq API call failed, using fallback")
    return await asyncio.to_thread(fallback_fn, text, *fallback_args)


# ── YAKE helper ───────────────────────────────────────────────────────────────

_yake_extractor = None


def _get_yake():
    """Return a cached YAKE KeywordExtractor (created once, reused)."""
    global _yake_extractor
    if _yake_extractor is None:
        _yake_extractor = yake.KeywordExtractor(lan="en", n=2, top=20, dedupLim=0.7)
    return _yake_extractor


def _yake_keywords_sync(text: str, top: int = 10) -> list[str]:
    """Extract top keywords via YAKE (synchronous)."""
    return [kw for kw, _score in _get_yake().extract_keywords(text)][:top]


# ── Fallback functions ────────────────────────────────────────────────────────


def _hashtag_fallback(text: str) -> str:
    keywords = _yake_keywords_sync(text)
    return " ".join(f"#{kw.replace(' ', '').capitalize()}" for kw in keywords[:10])


def _seo_title_fallback(text: str) -> str:
    keywords = _yake_keywords_sync(text, top=5)
    return "\n".join(f"{i}. {kw.title()} — A Complete Guide" for i, kw in enumerate(keywords[:5], 1))


def _meta_description_fallback(text: str) -> str:
    keywords = _yake_keywords_sync(text, top=3)
    return "\n".join(
        f"{i}. Discover everything about {kw}. Read our comprehensive guide and learn key insights today."
        for i, kw in enumerate(keywords[:3], 1)
    )


def _blog_outline_fallback(text: str) -> str:
    keywords = _yake_keywords_sync(text, top=5)
    topic = keywords[0].title() if keywords else "Your Topic"
    sections = [
        f"# Blog Post: {topic}",
        "",
        "## Introduction",
        f"- Hook: Why {topic} matters",
        "- Brief overview of key points",
        "",
    ]
    for i, kw in enumerate(keywords[1:5], 1):
        sections.append(f"## {i}. {kw.title()}")
        sections.append(f"- Key insight about {kw}")
        sections.append("- Practical tips and examples")
        sections.append("")
    sections.extend(["## Conclusion", "- Summary of key takeaways", "- Call to action"])
    return "\n".join(sections)


def _tweet_fallback(text: str) -> str:
    truncated = text[:277]
    last_space = truncated.rfind(" ")
    if last_space > 0:
        truncated = truncated[:last_space]
    return truncated + "..."


def _email_fallback(text: str) -> str:
    lines = text.strip().split("\n")
    subject = lines[0][:60] if lines else "Follow-up"
    body = text.strip()
    return f"Subject: {subject}\n\nDear recipient,\n\n{body}\n\nBest regards"


def _keyword_fallback(text: str) -> str:
    keywords = _yake_keywords_sync(text, top=15)
    return "\n".join(keywords)


def _translate_fallback(text: str, target_language: str) -> str:
    return f"[Translation requires Groq API key. Set GROQ_API_KEY in .env to enable translation to {target_language}.]"


def _transliterate_fallback(text: str, target_language: str) -> str:
    return (
        "[Transliteration requires Groq API key. "
        f"Set GROQ_API_KEY in .env to enable transliteration to {target_language}.]"
    )


def _emojify_fallback(text: str) -> str:
    return text + " 😊"


def _detect_lang_fallback(text: str) -> str:
    return "Unknown"


def _summarize_fallback(text: str) -> str:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
    return " ".join(sentences[:3]) + ("..." if len(sentences) > 3 else "")


def _grammar_fallback(text: str) -> str:
    result = re.sub(r"([.!?]\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), text)
    if result and result[0].islower():
        result = result[0].upper() + result[1:]
    return result


def _paraphrase_fallback(text: str) -> str:
    return "[Paraphrasing requires Groq API key. Set GROQ_API_KEY in .env to enable.]"


def _tone_fallback(text: str, tone: str) -> str:
    return f"[Tone changing requires Groq API key. Set GROQ_API_KEY in .env to enable {tone} tone.]"


def _lengthen_fallback(text: str) -> str:
    return "[Text lengthening requires Groq API key. Set GROQ_API_KEY in .env to enable.]"


def _eli5_fallback(text: str) -> str:
    return "[ELI5 simplification requires Groq API key. Set GROQ_API_KEY in .env to enable.]"


def _proofread_fallback(text: str) -> str:
    return "[Proofreading requires Groq API key. Set GROQ_API_KEY in .env to enable.]"


def _refactor_prompt_fallback(text: str) -> str:
    return "[Prompt refactoring requires Groq API key. Set GROQ_API_KEY in .env to enable.]"


def _generate_title_fallback(text: str) -> str:
    keywords = _yake_keywords_sync(text, top=5)
    return "\n".join(f"{i}. {kw.title()}" for i, kw in enumerate(keywords[:5], 1))


_EMOTION_KEYWORDS = {
    "happy": {
        "happy",
        "glad",
        "joy",
        "joyful",
        "cheerful",
        "delighted",
        "excited",
        "thrilled",
        "elated",
        "ecstatic",
        "pleased",
        "wonderful",
        "fantastic",
    },
    "sad": {
        "sad",
        "unhappy",
        "depressed",
        "miserable",
        "heartbroken",
        "grief",
        "sorrow",
        "gloomy",
        "melancholy",
        "lonely",
        "crying",
        "tears",
    },
    "angry": {
        "angry",
        "furious",
        "rage",
        "mad",
        "annoyed",
        "frustrated",
        "irritated",
        "outraged",
        "hostile",
        "livid",
        "infuriated",
        "hate",
    },
    "fearful": {
        "afraid",
        "scared",
        "fear",
        "terrified",
        "anxious",
        "worried",
        "nervous",
        "panic",
        "dread",
        "frightened",
        "alarmed",
        "uneasy",
    },
    "surprised": {
        "surprised",
        "shocked",
        "amazed",
        "astonished",
        "stunned",
        "unexpected",
        "unbelievable",
        "wow",
        "whoa",
        "incredible",
    },
    "disgusted": {
        "disgusted",
        "gross",
        "revolting",
        "repulsive",
        "sickening",
        "vile",
        "nasty",
        "horrible",
        "appalling",
        "dreadful",
    },
    "hopeful": {
        "hope",
        "hopeful",
        "optimistic",
        "promising",
        "encouraged",
        "looking forward",
        "bright",
        "positive",
        "confident",
        "inspired",
    },
    "loving": {
        "love",
        "adore",
        "cherish",
        "affection",
        "caring",
        "devoted",
        "passionate",
        "romantic",
        "warm",
        "tender",
        "fond",
    },
    "grateful": {"grateful", "thankful", "appreciate", "blessed", "thank", "thanks", "gratitude", "indebted"},
    "confused": {"confused", "puzzled", "baffled", "bewildered", "perplexed", "unclear", "lost", "uncertain", "unsure"},
}


def _sentiment_fallback(text: str) -> str:
    words = set(text.lower().split())
    detected = {}
    for emotion, keywords in _EMOTION_KEYWORDS.items():
        count = len(words & keywords)
        if count > 0:
            detected[emotion] = count
    pos_emotions = {"happy", "hopeful", "loving", "grateful", "surprised"}
    neg_emotions = {"sad", "angry", "fearful", "disgusted"}
    pos_score = sum(v for k, v in detected.items() if k in pos_emotions)
    neg_score = sum(v for k, v in detected.items() if k in neg_emotions)
    if pos_score > neg_score:
        sentiment = "Positive"
    elif neg_score > pos_score:
        sentiment = "Negative"
    else:
        sentiment = "Neutral"
    sorted_emotions = sorted(detected.items(), key=lambda x: x[1], reverse=True)
    primary = sorted_emotions[0][0].title() if sorted_emotions else "Neutral"
    secondary = ", ".join(e.title() for e, _ in sorted_emotions[1:3]) if len(sorted_emotions) > 1 else "None detected"
    return "\n".join(
        [
            f"**Overall Sentiment:** {sentiment}",
            "**Confidence:** Low (keyword-based fallback)",
            f"**Primary Emotion:** {primary}",
            f"**Secondary Emotions:** {secondary}",
            "**Sarcasm Detected:** Cannot detect (requires AI)",
            "**Tone:** Cannot detect (requires AI)",
            "",
            "Note: Set GROQ_API_KEY for full AI-powered analysis with sarcasm detection and tone analysis.",
        ]
    )


_FORMAT_PROMPTS = {
    "paragraph": (
        "Rewrite the user's text as well-structured flowing paragraphs. "
        "Merge bullet points, lists, and fragmented sentences into cohesive paragraphs. "
        "Each paragraph should cover one main idea."
    ),
    "bullets": (
        "Rewrite the user's text as a clear bullet point list. "
        "Each bullet should start with '•'. One key point per bullet. "
        "Be concise — no long paragraphs within bullets."
    ),
    "paragraph-bullets": (
        "Rewrite the user's text with a brief introductory paragraph "
        "followed by the key points as bullet points (using '•'). "
        "The intro should be 2-3 sentences summarizing the content, "
        "then list the details as concise bullets."
    ),
    "numbered": (
        "Rewrite the user's text as a numbered list (1. 2. 3. etc). "
        "Each item should be a clear, concise step or point. "
        "Order them logically."
    ),
    "qna": (
        "Rewrite the user's text in Q&A (Question and Answer) format. "
        "Identify the key topics and create relevant questions with clear answers. "
        "Format as:\nQ: [question]\nA: [answer]\n\nFor each point."
    ),
    "table": (
        "Rewrite the user's text in a markdown table format. "
        "Identify key categories/columns from the content and organize the information "
        "into rows and columns. Use | for column separators and --- for the header row."
    ),
    "tldr": (
        "Rewrite the user's text in TL;DR + Detail format. "
        "Start with 'TL;DR: ' followed by a 1-2 sentence summary, "
        "then add a blank line and the full detailed version below."
    ),
    "headings": (
        "Rewrite the user's text with clear section headings. "
        "Group related content under descriptive headings using markdown ## format. "
        "Add brief content under each heading."
    ),
}


def _format_fallback(text: str, fmt: str) -> str:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
    if fmt == "bullets":
        return "\n".join(f"• {s}" for s in sentences)
    elif fmt == "numbered":
        return "\n".join(f"{i}. {s}" for i, s in enumerate(sentences, 1))
    elif fmt == "paragraph-bullets":
        if len(sentences) > 1:
            return sentences[0] + "\n\n" + "\n".join(f"• {s}" for s in sentences[1:])
        return text
    elif fmt == "tldr":
        summary = sentences[0] if sentences else text[:100]
        return f"TL;DR: {summary}\n\n{text}"
    elif fmt == "headings":
        chunks, chunk = [], []
        for s in sentences:
            chunk.append(s)
            if len(chunk) >= 3:
                chunks.append(chunk)
                chunk = []
        if chunk:
            chunks.append(chunk)
        result = []
        for i, c in enumerate(chunks, 1):
            result.append(f"## Section {i}")
            result.append(" ".join(c))
            result.append("")
        return "\n".join(result)
    else:
        return " ".join(sentences)


# ── Prompts ───────────────────────────────────────────────────────────────────

_PROMPTS = {
    "hashtags": (
        "You are a hashtag generator. Given the user's text, "
        "return 5-15 relevant, trending-style hashtags. "
        "Return ONLY the hashtags separated by spaces, "
        "each starting with #. No explanations, no numbering."
    ),
    "seo_titles": (
        "You are an SEO title generator. Given the user's text, "
        "generate 5 compelling, SEO-optimized title suggestions. "
        "Each title should be 50-60 characters, include a primary keyword, "
        "and be click-worthy. Return ONLY the titles, one per line, "
        "numbered 1-5. No explanations."
    ),
    "meta_descriptions": (
        "You are a meta description generator for SEO. Given the user's text, "
        "generate 3 compelling meta descriptions. Each must be 150-160 characters, "
        "include a primary keyword, have a clear call-to-action, and entice clicks. "
        "Return ONLY the descriptions, one per line, numbered 1-3. No explanations."
    ),
    "blog_outline": (
        "You are a blog outline generator. Given the user's text or topic, "
        "generate a well-structured blog post outline with: "
        "a compelling title, an introduction section, 4-6 main sections "
        "each with 2-3 sub-points, and a conclusion. "
        "Use markdown-style formatting with # for title, ## for sections, "
        "and - for sub-points. No explanations outside the outline."
    ),
    "tweet": (
        "You are a tweet shortener. Given the user's text, "
        "rewrite it to fit within 280 characters while preserving "
        "the core message and meaning. Make it punchy and tweet-worthy. "
        "Return ONLY the shortened text, nothing else. "
        "Do NOT exceed 280 characters."
    ),
    "email": (
        "You are a professional email rewriter. Given the user's rough text or notes, "
        "rewrite it as a clear, polished, professional email. "
        "Include an appropriate greeting and sign-off. "
        "Keep the tone professional yet friendly. Preserve all key information. "
        "Return ONLY the rewritten email, nothing else."
    ),
    "keywords": (
        "You are a keyword extractor. Given the user's text, "
        "identify 10-15 of the most important keywords and key phrases. "
        "Return ONLY the keywords, one per line, ordered by relevance. "
        "No numbering, no explanations."
    ),
    "summarize": (
        "You are a text summarizer. Given the user's text, "
        "produce a clear, concise summary that captures all key points. "
        "The summary should be significantly shorter than the original. "
        "Return ONLY the summary, nothing else."
    ),
    "grammar": (
        "You are a grammar fixer. Given the user's text, "
        "fix all grammatical errors including subject-verb agreement, "
        "tense consistency, article usage, pronoun references, "
        "sentence fragments, and run-on sentences. "
        "Preserve the original meaning and tone. "
        "Return ONLY the corrected text, nothing else."
    ),
    "paraphrase": (
        "You are a paraphraser. Given the user's text, "
        "rewrite it using different words and sentence structures "
        "while preserving the original meaning completely. "
        "Make it sound natural and fluent. "
        "Return ONLY the paraphrased text, nothing else."
    ),
    "sentiment": (
        "You are an expert sentiment and emotion analyzer. Given the user's text, "
        "perform a thorough analysis and provide:\n\n"
        "**Overall Sentiment:** Positive / Negative / Neutral / Mixed\n"
        "**Confidence:** High / Medium / Low\n"
        "**Primary Emotion:** The strongest emotion detected (one of: "
        "Happy, Sad, Angry, Fearful, Surprised, Disgusted, Sarcastic, "
        "Hopeful, Loving, Grateful, Confused, Nostalgic, Humorous, "
        "Anxious, Proud, Jealous, Empathetic, Bored, Determined)\n"
        "**Secondary Emotions:** Other emotions present (list 1-3)\n"
        "**Sarcasm Detected:** Yes / No / Possibly — with brief reason\n"
        "**Tone:** Formal / Casual / Aggressive / Passive-aggressive / Warm / Cold / Neutral\n"
        "**Explanation:** 2-3 sentences explaining the emotional nuances.\n\n"
        "Be precise. For sarcasm, look for contradictions between literal meaning "
        "and intended meaning, exaggeration, and contextual cues. "
        "Format the output clearly with the bold labels above."
    ),
    "lengthen": (
        "You are a text expander. Given the user's text, "
        "expand and elaborate on it to make it longer and more detailed. "
        "Add relevant explanations, examples, and supporting details. "
        "Maintain the original meaning, tone, and style. "
        "Do not add unrelated information. "
        "Return ONLY the expanded text, nothing else."
    ),
    "eli5": (
        "You are an ELI5 (Explain Like I'm 5) expert. Given the user's text, "
        "rewrite it in the simplest possible language that a 5-year-old could understand. "
        "Use short sentences, everyday words, and fun analogies. "
        "Avoid jargon, technical terms, and complex sentence structures. "
        "If the text contains technical concepts, explain them with simple comparisons. "
        "Return ONLY the simplified text, nothing else."
    ),
    "proofread": (
        "You are a professional proofreader. Given the user's text, "
        "identify and fix all errors (spelling, grammar, punctuation, style). "
        "Return a tracked-changes style markup showing what was changed and why. "
        "Format each change as:\n"
        "- ~~original~~ → **corrected** (reason)\n\n"
        "Then provide the fully corrected text at the end under a '---' separator. "
        "If the text has no errors, say 'No issues found.' and return the original text."
    ),
    "generate_title": (
        "You are a headline generator. Given the user's text, "
        "generate 5 concise, compelling titles/headlines that capture the essence of the content. "
        "Each title should be under 80 characters, clear, and engaging. "
        "Return ONLY the titles, one per line, numbered 1-5. No explanations."
    ),
    "refactor_prompt": (
        "You are a prompt engineer specializing in token optimization. "
        "Rewrite the user's prompt to use minimum tokens while preserving "
        "all instructions, constraints, and intent. Techniques:\n"
        "- Remove filler words, redundancy, and verbose phrasing\n"
        "- Use concise directives instead of polite requests\n"
        "- Merge overlapping instructions\n"
        "- Use symbols/shorthand where clear (e.g. → for 'convert to')\n"
        "- Keep all technical constraints and output format requirements\n\n"
        "Return ONLY the optimized prompt. After the prompt, add two blank lines, "
        "then on a separate line: "
        "'[Original: ~N tokens → Optimized: ~N tokens, Saved: ~N%]' "
        "(estimate token counts)."
    ),
}

_TONE_INSTRUCTIONS = {
    "formal": "Rewrite in a formal, professional tone. Use proper language, avoid contractions and slang.",
    "casual": "Rewrite in a casual, relaxed tone. Use everyday language, contractions, and a conversational style.",
    "friendly": "Rewrite in a warm, friendly tone. Be approachable, positive, and personable.",
}


# ── Service classes (thin wrappers for import compatibility) ──────────────────


class HashtagService:
    @staticmethod
    async def generate_hashtags(text: str) -> str:
        return await _ai_transform(_PROMPTS["hashtags"], text, _hashtag_fallback)


class SEOTitleService:
    @staticmethod
    async def generate_seo_titles(text: str) -> str:
        return await _ai_transform(
            _PROMPTS["seo_titles"],
            text,
            _seo_title_fallback,
            temperature=0.8,
            max_tokens=300,
        )


class MetaDescriptionService:
    @staticmethod
    async def generate_meta_descriptions(text: str) -> str:
        return await _ai_transform(
            _PROMPTS["meta_descriptions"],
            text,
            _meta_description_fallback,
            temperature=0.8,
            max_tokens=400,
        )


class BlogOutlineService:
    @staticmethod
    async def generate_blog_outline(text: str) -> str:
        return await _ai_transform(
            _PROMPTS["blog_outline"],
            text,
            _blog_outline_fallback,
            temperature=0.8,
            max_tokens=600,
        )


class TweetShortenerService:
    @staticmethod
    async def shorten_for_tweet(text: str) -> str:
        return await _ai_transform(_PROMPTS["tweet"], text, _tweet_fallback, max_tokens=100)


class EmailRewriterService:
    @staticmethod
    async def rewrite_email(text: str) -> str:
        return await _ai_transform(_PROMPTS["email"], text, _email_fallback, max_tokens=500)


class KeywordExtractorService:
    @staticmethod
    async def extract_keywords(text: str) -> str:
        return await _ai_transform(_PROMPTS["keywords"], text, _keyword_fallback, temperature=0.3)


class TranslatorService:
    @staticmethod
    async def translate(text: str, target_language: str) -> str:
        prompt = (
            f"You are a translator. Translate the user's text into {target_language}. "
            "Preserve the original meaning, tone, and formatting as closely as possible. "
            "Return ONLY the translated text, nothing else. "
            "Do not include any notes or explanations."
        )
        return await _ai_transform(
            prompt,
            text,
            _translate_fallback,
            target_language,
            temperature=0.3,
            max_tokens=1000,
        )


class TransliterationService:
    @staticmethod
    async def transliterate(text: str, target_language: str) -> str:
        prompt = (
            f"You are a transliterator. Convert the user's text into {target_language} script "
            "(transliteration, NOT translation). Keep the original words and sounds — "
            f"just write them using the {target_language} writing system. "
            "For example, English 'hello' in Hindi script becomes 'हेलो'. "
            "Return ONLY the transliterated text, nothing else."
        )
        return await _ai_transform(
            prompt,
            text,
            _transliterate_fallback,
            target_language,
            temperature=0.2,
            max_tokens=1000,
        )


class SummarizerService:
    @staticmethod
    async def summarize(text: str) -> str:
        return await _ai_transform(
            _PROMPTS["summarize"],
            text,
            _summarize_fallback,
            temperature=0.5,
            max_tokens=500,
        )


class GrammarFixerService:
    @staticmethod
    async def fix_grammar(text: str) -> str:
        return await _ai_transform(
            _PROMPTS["grammar"],
            text,
            _grammar_fallback,
            temperature=0.3,
            max_tokens=1500,
        )


class ParaphraserService:
    @staticmethod
    async def paraphrase(text: str) -> str:
        return await _ai_transform(
            _PROMPTS["paraphrase"],
            text,
            _paraphrase_fallback,
            temperature=0.8,
            max_tokens=1500,
        )


class ToneChangerService:
    @staticmethod
    async def change_tone(text: str, tone: str) -> str:
        instruction = _TONE_INSTRUCTIONS.get(tone.lower(), _TONE_INSTRUCTIONS["formal"])
        prompt = (
            f"You are a tone changer. Given the user's text, {instruction} "
            "Preserve the original meaning completely. "
            "Return ONLY the rewritten text, nothing else."
        )
        return await _ai_transform(prompt, text, _tone_fallback, tone, max_tokens=1500)


class SentimentAnalyzerService:
    @staticmethod
    async def analyze_sentiment(text: str) -> str:
        return await _ai_transform(
            _PROMPTS["sentiment"],
            text,
            _sentiment_fallback,
            temperature=0.2,
            max_tokens=400,
        )


class TextLengthenerService:
    @staticmethod
    async def lengthen(text: str) -> str:
        return await _ai_transform(_PROMPTS["lengthen"], text, _lengthen_fallback, max_tokens=2000)


class ELI5Service:
    @staticmethod
    async def eli5(text: str) -> str:
        return await _ai_transform(_PROMPTS["eli5"], text, _eli5_fallback, temperature=0.7, max_tokens=1500)


class ProofreadService:
    @staticmethod
    async def proofread(text: str) -> str:
        return await _ai_transform(
            _PROMPTS["proofread"],
            text,
            _proofread_fallback,
            temperature=0.3,
            max_tokens=2000,
        )


class PromptRefactorService:
    @staticmethod
    async def refactor_prompt(text: str) -> str:
        return await _ai_transform(
            _PROMPTS["refactor_prompt"],
            text,
            _refactor_prompt_fallback,
            temperature=0.4,
            max_tokens=1500,
        )


class TitleGeneratorService:
    @staticmethod
    async def generate_title(text: str) -> str:
        return await _ai_transform(
            _PROMPTS["generate_title"],
            text,
            _generate_title_fallback,
            temperature=0.8,
            max_tokens=300,
        )


class FormatChangerService:
    @staticmethod
    async def change_format(text: str, fmt: str) -> str:
        base_prompt = _FORMAT_PROMPTS.get(fmt.lower(), _FORMAT_PROMPTS["paragraph"])
        prompt = (
            f"You are a text formatter. {base_prompt} "
            "Preserve ALL original information — only change the structure/format. "
            "Return ONLY the reformatted text, nothing else."
        )
        return await _ai_transform(
            prompt,
            text,
            _format_fallback,
            fmt,
            temperature=0.5,
            max_tokens=2000,
        )


class EmojifyService:
    @staticmethod
    async def emojify(text: str) -> str:
        prompt = (
            "You are an emoji translator. Replace words and phrases in the user's text "
            "with matching emojis wherever possible. "
            "For example: 'I am crying' → 'I am 😭', 'boom' → '💥', "
            "'I love pizza' → 'I ❤️ 🍕', 'happy birthday' → '🎂🎉'. "
            "Replace the word/phrase itself with the emoji — do NOT keep both. "
            "Keep words that have no good emoji match. Preserve sentence structure "
            "and grammar words (I, am, the, is, etc.). "
            "Work with ANY language — understand the meaning and replace with emojis "
            "regardless of input language. "
            "Return ONLY the emojified text, nothing else."
        )
        return await _ai_transform(prompt, text, _emojify_fallback, temperature=0.7, max_tokens=1000)


class LanguageDetector:
    @staticmethod
    async def detect(text: str) -> str:
        prompt = (
            "Detect the language of the following text. "
            "Return ONLY the language name in English (e.g., 'English', 'Hindi', 'Spanish', 'French'). "
            "Nothing else."
        )
        return await _ai_transform(prompt, text, _detect_lang_fallback, temperature=0.1, max_tokens=20)


# ── New AI Writing Services ──────────────────────────────────────────────────


def _passthrough_fallback(text: str, *args) -> str:
    return text


class AcademicStyleService:
    @staticmethod
    async def transform(text: str) -> str:
        prompt = (
            "You are an academic writing expert. Rewrite the user's text in formal academic style. "
            "Use third person, formal vocabulary, hedging language (e.g., 'suggests', 'indicates'), "
            "and appropriate academic register. Do not add citations but use citation-ready phrasing. "
            "Return ONLY the rewritten text, nothing else."
        )
        return await _ai_transform(prompt, text, _passthrough_fallback, temperature=0.5, max_tokens=1500)


class CreativeStyleService:
    @staticmethod
    async def transform(text: str) -> str:
        prompt = (
            "You are a creative writer. Rewrite the user's text with vivid, literary flair. "
            "Use figurative language, sensory details, varied sentence structure, and engaging prose. "
            "Make it more expressive and evocative while preserving the core meaning. "
            "Return ONLY the rewritten text, nothing else."
        )
        return await _ai_transform(prompt, text, _passthrough_fallback, temperature=0.9, max_tokens=1500)


class TechnicalStyleService:
    @staticmethod
    async def transform(text: str) -> str:
        prompt = (
            "You are a technical documentation writer. Rewrite the user's text in precise, "
            "technical documentation style. Use clear, unambiguous language, active voice, "
            "step-by-step structure where applicable, and technical precision. "
            "Return ONLY the rewritten text, nothing else."
        )
        return await _ai_transform(prompt, text, _passthrough_fallback, temperature=0.3, max_tokens=1500)


class ActiveVoiceService:
    @staticmethod
    async def transform(text: str) -> str:
        prompt = (
            "You are a writing editor. Convert all passive voice sentences in the user's text to active voice. "
            "Keep sentences that are already in active voice unchanged. "
            "Preserve the original meaning completely. "
            "Return ONLY the rewritten text, nothing else."
        )
        return await _ai_transform(prompt, text, _passthrough_fallback, temperature=0.3, max_tokens=1500)


class RedundancyRemoverService:
    @staticmethod
    async def transform(text: str) -> str:
        prompt = (
            "You are a concise writing editor. Remove redundant words and phrases from the user's text. "
            "Examples: 'free gift' → 'gift', 'advance planning' → 'planning', 'past history' → 'history'. "
            "Also remove unnecessary qualifiers and filler words. Preserve the original meaning. "
            "Return ONLY the cleaned text, nothing else."
        )
        return await _ai_transform(prompt, text, _passthrough_fallback, temperature=0.3, max_tokens=1500)


class SentenceSplitterService:
    @staticmethod
    async def transform(text: str) -> str:
        prompt = (
            "You are a writing clarity editor. Break overly complex, compound, or run-on sentences "
            "into shorter, clearer sentences. Keep simple sentences unchanged. "
            "Preserve the original meaning and all information. "
            "Return ONLY the rewritten text, nothing else."
        )
        return await _ai_transform(prompt, text, _passthrough_fallback, temperature=0.3, max_tokens=1500)


class ConcisenessService:
    @staticmethod
    async def transform(text: str) -> str:
        prompt = (
            "You are a conciseness editor. Remove filler words, unnecessary qualifiers, "
            "wordy constructions, and tighten the prose without losing any meaning. "
            "Examples: 'in order to' → 'to', 'at this point in time' → 'now', "
            "'due to the fact that' → 'because'. "
            "Return ONLY the tightened text, nothing else."
        )
        return await _ai_transform(prompt, text, _passthrough_fallback, temperature=0.3, max_tokens=1500)


class ResumeBulletsService:
    @staticmethod
    async def transform(text: str) -> str:
        prompt = (
            "You are a resume writing expert. Transform the user's text into 3-5 impactful resume bullet points. "
            "Start each with a strong action verb (Led, Developed, Implemented, etc.). "
            "Quantify achievements where possible. Use past tense. "
            "Return ONLY the bullet points (prefixed with •), nothing else."
        )
        return await _ai_transform(prompt, text, _passthrough_fallback, temperature=0.6, max_tokens=500)


class MeetingNotesService:
    @staticmethod
    async def transform(text: str) -> str:
        prompt = (
            "You are a meeting notes organizer. Summarize the user's text into structured meeting notes. "
            "Include: ## Key Decisions, ## Discussion Points, ## Action Items (with owners if mentioned), "
            "## Next Steps. Use concise bullet points. "
            "Return ONLY the structured notes, nothing else."
        )
        return await _ai_transform(prompt, text, _passthrough_fallback, temperature=0.4, max_tokens=800)


class CoverLetterService:
    @staticmethod
    async def transform(text: str) -> str:
        prompt = (
            "You are a career coach. Generate a professional cover letter based on the user's text "
            "(which may contain job requirements, experience, or rough notes). "
            "Include: greeting, opening hook, 2-3 body paragraphs connecting experience to requirements, "
            "closing with call to action, sign-off. Keep it under 400 words. "
            "Return ONLY the cover letter, nothing else."
        )
        return await _ai_transform(prompt, text, _passthrough_fallback, temperature=0.7, max_tokens=800)


class OutlineToDraftService:
    @staticmethod
    async def transform(text: str) -> str:
        prompt = (
            "You are a writer. Expand the user's bullet-point outline into full prose paragraphs. "
            "Each bullet point should become a well-developed paragraph. "
            "Add transitions between sections. Maintain the outline's structure and order. "
            "Return ONLY the expanded prose, nothing else."
        )
        return await _ai_transform(prompt, text, _passthrough_fallback, temperature=0.7, max_tokens=1500)


class ContinueWritingService:
    @staticmethod
    async def transform(text: str) -> str:
        prompt = (
            "You are a writing assistant. Continue writing from where the user's text ends. "
            "Match the existing style, tone, and voice perfectly. "
            "Write 2-3 additional paragraphs that naturally follow from the content. "
            "Return ONLY the continuation (do NOT repeat the original text), nothing else."
        )
        return await _ai_transform(prompt, text, _passthrough_fallback, temperature=0.8, max_tokens=800)


class RewriteUniqueService:
    @staticmethod
    async def transform(text: str) -> str:
        prompt = (
            "You are a deep rewriter. Completely rewrite the user's text with entirely original "
            "phrasing, sentence structure, and organization. Change the word order, use different "
            "vocabulary, restructure paragraphs, but preserve ALL the original meaning and information. "
            "The result should read as a completely different text saying the same thing. "
            "Return ONLY the rewritten text, nothing else."
        )
        return await _ai_transform(prompt, text, _passthrough_fallback, temperature=0.9, max_tokens=1500)


class ToneAnalyzerService:
    @staticmethod
    async def transform(text: str) -> str:
        prompt = (
            "You are a tone analyzer. Analyze the emotional tone and formality of the user's text. "
            "Provide: Tone (e.g., Professional, Casual, Urgent, Friendly), "
            "Sentiment (Positive/Negative/Neutral with percentage), "
            "Formality (High/Medium/Low with percentage), "
            "Key emotional words found. "
            "Format as a brief analysis report. Return ONLY the analysis, nothing else."
        )
        return await _ai_transform(prompt, text, _passthrough_fallback, temperature=0.3, max_tokens=400)


# ── New AI Content Services ──────────────────────────────────────────────────


class LinkedinPostService:
    @staticmethod
    async def transform(text: str) -> str:
        prompt = (
            "You are a LinkedIn content creator. Transform the user's text into an engaging LinkedIn post. "
            "Include: attention-grabbing opening line, short paragraphs (1-2 sentences each), "
            "line breaks for readability, a clear takeaway, and a call-to-action at the end. "
            "Do NOT include hashtags. Keep under 1300 characters. "
            "Return ONLY the LinkedIn post, nothing else."
        )
        return await _ai_transform(prompt, text, _passthrough_fallback, temperature=0.7, max_tokens=600)


class TwitterThreadService:
    @staticmethod
    async def transform(text: str) -> str:
        prompt = (
            "You are a Twitter/X thread creator. Break the user's content into a numbered thread. "
            "Format: '1/ [hook tweet]\\n\\n2/ [point]\\n\\n3/ [point]...' "
            "First tweet must be a strong hook. Each tweet under 280 characters. "
            "End with a summary or CTA tweet. Aim for 4-8 tweets. "
            "Return ONLY the thread, nothing else."
        )
        return await _ai_transform(prompt, text, _passthrough_fallback, temperature=0.7, max_tokens=800)


class InstagramCaptionService:
    @staticmethod
    async def transform(text: str) -> str:
        prompt = (
            "You are an Instagram content creator. Create an engaging Instagram caption from the user's text. "
            "Include: attention-grabbing first line, engaging story or value, "
            "relevant emojis sprinkled naturally, a call-to-action question at the end, "
            "and 10-15 relevant hashtags on a separate line. "
            "Return ONLY the caption, nothing else."
        )
        return await _ai_transform(prompt, text, _passthrough_fallback, temperature=0.8, max_tokens=600)


class YoutubeDescService:
    @staticmethod
    async def transform(text: str) -> str:
        prompt = (
            "You are a YouTube content strategist. Generate a structured YouTube video description. "
            "Include: 2-3 sentence intro summary, '📌 In this video:' section with bullet points, "
            "placeholder timestamps (00:00 Intro, etc.), 'LINKS' section with placeholders, "
            "and a brief bio placeholder. "
            "Return ONLY the description, nothing else."
        )
        return await _ai_transform(prompt, text, _passthrough_fallback, temperature=0.6, max_tokens=600)


class SocialBioService:
    @staticmethod
    async def transform(text: str) -> str:
        prompt = (
            "You are a social media branding expert. Generate 5 concise social media bio options "
            "from the user's text or self-description. Each bio should be under 160 characters, "
            "punchy, and use pipe separators or emojis for structure. "
            "Return ONLY the 5 bios, numbered 1-5, one per line."
        )
        return await _ai_transform(prompt, text, _passthrough_fallback, temperature=0.8, max_tokens=400)


class ProductDescService:
    @staticmethod
    async def transform(text: str) -> str:
        prompt = (
            "You are a copywriter. Write a compelling product description from the user's text "
            "(features, specs, or rough notes). Include: attention-grabbing headline, "
            "benefit-focused body copy, key features as bullet points, "
            "and a persuasive closing line. "
            "Return ONLY the product description, nothing else."
        )
        return await _ai_transform(prompt, text, _passthrough_fallback, temperature=0.7, max_tokens=600)


class CtaGeneratorService:
    @staticmethod
    async def transform(text: str) -> str:
        prompt = (
            "You are a conversion copywriter. Generate 10 call-to-action variations for the user's text. "
            "Include a mix of: button text (2-5 words), banner copy (one sentence), "
            "and urgency-driven CTAs. Number them 1-10. "
            "Return ONLY the CTAs, nothing else."
        )
        return await _ai_transform(prompt, text, _passthrough_fallback, temperature=0.8, max_tokens=400)


class AdCopyService:
    @staticmethod
    async def transform(text: str) -> str:
        prompt = (
            "You are an advertising copywriter. Generate ad copy from the user's text. "
            "Create 3 variations, each with: Headline (max 30 chars), "
            "Description (max 90 chars), Display URL suggestion. "
            "Format for Google Ads style. Number them 1-3. "
            "Return ONLY the ad copies, nothing else."
        )
        return await _ai_transform(prompt, text, _passthrough_fallback, temperature=0.8, max_tokens=500)


class LandingHeadlineService:
    @staticmethod
    async def transform(text: str) -> str:
        prompt = (
            "You are a landing page copywriter. Generate 5 attention-grabbing headlines "
            "from the user's value proposition or product text. Mix styles: "
            "benefit-driven, curiosity-driven, social proof, urgency, and question-based. "
            "Number them 1-5. Return ONLY the headlines, nothing else."
        )
        return await _ai_transform(prompt, text, _passthrough_fallback, temperature=0.8, max_tokens=300)


class EmailSubjectService:
    @staticmethod
    async def transform(text: str) -> str:
        prompt = (
            "You are an email marketing expert. Generate 8 compelling email subject lines "
            "from the user's text/topic. Mix: curiosity, urgency, personalization, benefit, "
            "question, and number-based approaches. Keep each under 60 characters. "
            "Number them 1-8. Return ONLY the subject lines, nothing else."
        )
        return await _ai_transform(prompt, text, _passthrough_fallback, temperature=0.8, max_tokens=400)


class ContentIdeasService:
    @staticmethod
    async def transform(text: str) -> str:
        prompt = (
            "You are a content strategist. Generate 10 content ideas from the user's topic or niche. "
            "For each idea, include: title, format (blog/video/thread/infographic), "
            "and a one-line angle. Number them 1-10. "
            "Return ONLY the ideas, nothing else."
        )
        return await _ai_transform(prompt, text, _passthrough_fallback, temperature=0.9, max_tokens=600)


class HookGeneratorService:
    @staticmethod
    async def transform(text: str) -> str:
        prompt = (
            "You are a copywriting expert. Create 5 attention-grabbing opening lines (hooks) "
            "for the user's topic. Include diverse styles: startling statistic, provocative question, "
            "bold statement, story opener, and contrarian take. Number them 1-5. "
            "Return ONLY the hooks, nothing else."
        )
        return await _ai_transform(prompt, text, _passthrough_fallback, temperature=0.8, max_tokens=400)


class AngleGeneratorService:
    @staticmethod
    async def transform(text: str) -> str:
        prompt = (
            "You are a content strategist. Find 5 unique angles or perspectives for the user's topic. "
            "For each angle: a catchy title and a 1-2 sentence description of the approach. "
            "Think: contrarian, data-driven, personal story, industry insider, beginner-friendly. "
            "Number them 1-5. Return ONLY the angles, nothing else."
        )
        return await _ai_transform(prompt, text, _passthrough_fallback, temperature=0.9, max_tokens=500)


class FaqSchemaService:
    @staticmethod
    async def transform(text: str) -> str:
        prompt = (
            "You are an SEO expert. Convert the user's text into FAQ Schema markup (JSON-LD format). "
            "Extract Q&A pairs from the text (or generate FAQs if the text is a topic). "
            "Return valid JSON-LD with @context, @type: FAQPage, and mainEntity array. "
            "Return ONLY the JSON-LD code, nothing else."
        )
        return await _ai_transform(prompt, text, _passthrough_fallback, temperature=0.3, max_tokens=800)


# ── New Language Services ────────────────────────────────────────────────────


class PosTaggerService:
    @staticmethod
    async def transform(text: str) -> str:
        prompt = (
            "You are a linguistics expert. Tag each word in the user's text with its part of speech. "
            "Format: word/TAG (e.g., The/DET quick/ADJ brown/ADJ fox/NOUN jumps/VERB). "
            "Use standard POS tags: NOUN, VERB, ADJ, ADV, DET, PRON, PREP, CONJ, INTJ. "
            "Return ONLY the tagged text, nothing else."
        )
        return await _ai_transform(prompt, text, _passthrough_fallback, temperature=0.2, max_tokens=1500)


class SentenceTypeService:
    @staticmethod
    async def transform(text: str) -> str:
        prompt = (
            "You are a grammar expert. Classify each sentence in the user's text as: "
            "Declarative (statement), Interrogative (question), Imperative (command), "
            "or Exclamatory (exclamation). Format: 'sentence' → Type. "
            "Return ONLY the classifications, nothing else."
        )
        return await _ai_transform(prompt, text, _passthrough_fallback, temperature=0.2, max_tokens=800)


class GrammarExplainService:
    @staticmethod
    async def transform(text: str) -> str:
        prompt = (
            "You are an English grammar teacher. Find grammar errors in the user's text, "
            "correct them, and explain the grammar rule behind each correction. "
            "Format: ❌ Original → ✅ Corrected\n📖 Rule: [explanation]\n\n "
            "If no errors found, say 'No grammar errors found!' "
            "Return ONLY the corrections and explanations, nothing else."
        )
        return await _ai_transform(prompt, text, _passthrough_fallback, temperature=0.3, max_tokens=800)


class SynonymFinderService:
    @staticmethod
    async def transform(text: str) -> str:
        prompt = (
            "You are a thesaurus. For each significant word in the user's text, "
            "provide 3-5 synonyms. Format: word → synonym1, synonym2, synonym3. "
            "Skip common words (the, is, a, and, etc.). "
            "Return ONLY the synonym list, nothing else."
        )
        return await _ai_transform(prompt, text, _passthrough_fallback, temperature=0.5, max_tokens=800)


class AntonymFinderService:
    @staticmethod
    async def transform(text: str) -> str:
        prompt = (
            "You are a thesaurus. For each significant word in the user's text, "
            "provide 2-3 antonyms. Format: word → antonym1, antonym2. "
            "Skip words that don't have clear antonyms. "
            "Return ONLY the antonym list, nothing else."
        )
        return await _ai_transform(prompt, text, _passthrough_fallback, temperature=0.5, max_tokens=800)


class DefineWordsService:
    @staticmethod
    async def transform(text: str) -> str:
        prompt = (
            "You are a dictionary. Define each significant or uncommon word in the user's text. "
            "Format: word (part of speech) — definition. "
            "Skip very common words. Include pronunciation hints for difficult words. "
            "Return ONLY the definitions, nothing else."
        )
        return await _ai_transform(prompt, text, _passthrough_fallback, temperature=0.3, max_tokens=800)


class WordPowerService:
    @staticmethod
    async def transform(text: str) -> str:
        prompt = (
            "You are a writing power editor. Replace weak, generic words in the user's text "
            "with stronger, more impactful alternatives. Examples: 'good' → 'exceptional', "
            "'bad' → 'devastating', 'said' → 'declared', 'went' → 'strode'. "
            "Return the full text with replacements made. "
            "Return ONLY the improved text, nothing else."
        )
        return await _ai_transform(prompt, text, _passthrough_fallback, temperature=0.6, max_tokens=1500)


class VocabComplexityService:
    @staticmethod
    async def transform(text: str) -> str:
        prompt = (
            "You are a vocabulary analyst. Analyze the vocabulary sophistication of the user's text. "
            "Provide: Overall Complexity Score (1-10), "
            "Complex words found with simpler alternatives, "
            "Vocabulary diversity ratio, Suggested reading level. "
            "Return ONLY the analysis, nothing else."
        )
        return await _ai_transform(prompt, text, _passthrough_fallback, temperature=0.3, max_tokens=600)


class JargonSimplifierService:
    @staticmethod
    async def transform(text: str) -> str:
        prompt = (
            "You are a plain language editor. Identify and replace technical jargon, "
            "acronyms, and specialized terms in the user's text with plain, everyday language. "
            "Make the text accessible to a general audience with no specialized knowledge. "
            "Return ONLY the simplified text, nothing else."
        )
        return await _ai_transform(prompt, text, _passthrough_fallback, temperature=0.4, max_tokens=1500)


class FormalityDetectorService:
    @staticmethod
    async def transform(text: str) -> str:
        prompt = (
            "You are a register analyst. Analyze the formality level of the user's text. "
            "Provide: Overall Register (Formal/Semi-formal/Informal/Casual), "
            "Formality Score (1-10), Key indicators found (contractions, slang, passive voice, etc.), "
            "Suggestions to adjust formality if needed. "
            "Return ONLY the analysis, nothing else."
        )
        return await _ai_transform(prompt, text, _passthrough_fallback, temperature=0.3, max_tokens=400)


class ClicheDetectorService:
    @staticmethod
    async def transform(text: str) -> str:
        prompt = (
            "You are a writing freshness editor. Find all cliched, overused phrases in the user's text. "
            "For each cliche found: quote the cliche → suggest a fresher alternative. "
            "Common cliches: 'at the end of the day', 'think outside the box', 'low-hanging fruit', etc. "
            "If no cliches found, say 'No cliches detected — your writing is fresh!' "
            "Return ONLY the findings, nothing else."
        )
        return await _ai_transform(prompt, text, _passthrough_fallback, temperature=0.5, max_tokens=600)


# ── New Generator AI Services ───────────────────────────────────────────────


class RegexGenService:
    @staticmethod
    async def transform(text: str) -> str:
        prompt = (
            "You are a regex expert. The user describes what they want to match. "
            "Generate the regex pattern and explain it. Format:\n"
            "Pattern: /regex_here/flags\n"
            "Explanation: Brief description of each part\n"
            "Examples: 2-3 example matches\n"
            "Return ONLY the pattern, explanation, and examples."
        )
        return await _ai_transform(prompt, text, _passthrough_fallback, temperature=0.3, max_tokens=400)


class WritingPromptService:
    @staticmethod
    async def transform(text: str) -> str:
        prompt = (
            "You are a creative writing instructor. Generate 5 unique, inspiring writing prompts "
            "related to the user's topic or genre (or random if no topic given). "
            "Each prompt should be 1-2 sentences and spark imagination. "
            "Mix genres: fiction, creative nonfiction, poetry, flash fiction, dialogue. "
            "Number them 1-5. Return ONLY the prompts, nothing else."
        )
        return await _ai_transform(prompt, text, _passthrough_fallback, temperature=0.9, max_tokens=400)


class TeamNameGenService:
    @staticmethod
    async def transform(text: str) -> str:
        prompt = (
            "You are a creative naming expert. Generate 10 creative team or project names "
            "based on the user's keywords or description. Mix: professional, playful, techy, "
            "and memorable options. Number them 1-10. "
            "Return ONLY the names, nothing else."
        )
        return await _ai_transform(prompt, text, _passthrough_fallback, temperature=0.9, max_tokens=300)


class MockApiResponseService:
    @staticmethod
    async def transform(text: str) -> str:
        prompt = (
            "You are an API designer. Generate a realistic mock REST API JSON response "
            "based on the user's description (endpoint, data type, etc.). "
            "Include realistic field names, data types, and sample values. "
            "Add pagination metadata if appropriate. Return valid, properly formatted JSON. "
            "Return ONLY the JSON response, nothing else."
        )
        return await _ai_transform(prompt, text, _passthrough_fallback, temperature=0.6, max_tokens=800)
