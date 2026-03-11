"""
AIService — AI-powered text tools.

Primary: Groq API (Llama 3.3 70B) for context-aware generation.
Fallback: YAKE keyword extraction for offline / no-key usage.
"""

import logging
import re
from typing import Callable

import yake
from groq import AsyncGroq
from app.core.config import settings

logger = logging.getLogger(__name__)

_MODEL = "llama-3.3-70b-versatile"


# ── Groq helpers ──────────────────────────────────────────────────────────────

def _get_groq_client() -> AsyncGroq:
    """Return a cached AsyncGroq client (created once, reused across requests)."""
    if not hasattr(_get_groq_client, "_client") or _get_groq_client._client is None:
        _get_groq_client._client = AsyncGroq(
            api_key=settings.GROQ_API_KEY,
            timeout=30.0,
        )
    return _get_groq_client._client


async def _groq_chat(system_prompt: str, user_text: str, temperature: float = 0.7, max_tokens: int = 200) -> str:
    """Shared Groq chat helper."""
    client = _get_groq_client()
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
            return await _groq_chat(system_prompt, text, temperature, max_tokens)
        except Exception:
            logger.exception("Groq API call failed, using fallback")
    return fallback_fn(text, *fallback_args)


# ── YAKE helper ───────────────────────────────────────────────────────────────

_yake_extractor = None


def _get_yake():
    """Return a cached YAKE KeywordExtractor (created once, reused)."""
    global _yake_extractor
    if _yake_extractor is None:
        _yake_extractor = yake.KeywordExtractor(lan="en", n=2, top=20, dedupLim=0.7)
    return _yake_extractor


def _yake_keywords(text: str, top: int = 10) -> list[str]:
    """Extract top keywords via YAKE."""
    return [kw for kw, _score in _get_yake().extract_keywords(text)][:top]


# ── Fallback functions ────────────────────────────────────────────────────────

def _hashtag_fallback(text: str) -> str:
    keywords = _yake_keywords(text)
    return " ".join(f"#{kw.replace(' ', '').capitalize()}" for kw in keywords[:10])


def _seo_title_fallback(text: str) -> str:
    keywords = _yake_keywords(text, top=5)
    return "\n".join(f"{i}. {kw.title()} — A Complete Guide" for i, kw in enumerate(keywords[:5], 1))


def _meta_description_fallback(text: str) -> str:
    keywords = _yake_keywords(text, top=3)
    return "\n".join(
        f"{i}. Discover everything about {kw}. Read our comprehensive guide and learn key insights today."
        for i, kw in enumerate(keywords[:3], 1)
    )


def _blog_outline_fallback(text: str) -> str:
    keywords = _yake_keywords(text, top=5)
    topic = keywords[0].title() if keywords else "Your Topic"
    sections = [f"# Blog Post: {topic}", "", "## Introduction", f"- Hook: Why {topic} matters", "- Brief overview of key points", ""]
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
    lines = text.strip().split('\n')
    subject = lines[0][:60] if lines else "Follow-up"
    body = text.strip()
    return f"Subject: {subject}\n\nDear recipient,\n\n{body}\n\nBest regards"



def _keyword_fallback(text: str) -> str:
    keywords = _yake_keywords(text, top=15)
    return "\n".join(keywords)


def _translate_fallback(text: str, target_language: str) -> str:
    return f"[Translation requires Groq API key. Set GROQ_API_KEY in .env to enable translation to {target_language}.]"


def _transliterate_fallback(text: str, target_language: str) -> str:
    return f"[Transliteration requires Groq API key. Set GROQ_API_KEY in .env to enable transliteration to {target_language}.]"



def _summarize_fallback(text: str) -> str:
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text.strip()) if s.strip()]
    return " ".join(sentences[:3]) + ("..." if len(sentences) > 3 else "")


def _grammar_fallback(text: str) -> str:
    result = re.sub(r'([.!?]\s+)([a-z])', lambda m: m.group(1) + m.group(2).upper(), text)
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


def _generate_title_fallback(text: str) -> str:
    keywords = _yake_keywords(text, top=5)
    return "\n".join(f"{i}. {kw.title()}" for i, kw in enumerate(keywords[:5], 1))


_EMOTION_KEYWORDS = {
    'happy':      {'happy', 'glad', 'joy', 'joyful', 'cheerful', 'delighted', 'excited',
                   'thrilled', 'elated', 'ecstatic', 'pleased', 'wonderful', 'fantastic'},
    'sad':        {'sad', 'unhappy', 'depressed', 'miserable', 'heartbroken', 'grief',
                   'sorrow', 'gloomy', 'melancholy', 'lonely', 'crying', 'tears'},
    'angry':      {'angry', 'furious', 'rage', 'mad', 'annoyed', 'frustrated', 'irritated',
                   'outraged', 'hostile', 'livid', 'infuriated', 'hate'},
    'fearful':    {'afraid', 'scared', 'fear', 'terrified', 'anxious', 'worried', 'nervous',
                   'panic', 'dread', 'frightened', 'alarmed', 'uneasy'},
    'surprised':  {'surprised', 'shocked', 'amazed', 'astonished', 'stunned', 'unexpected',
                   'unbelievable', 'wow', 'whoa', 'incredible'},
    'disgusted':  {'disgusted', 'gross', 'revolting', 'repulsive', 'sickening', 'vile',
                   'nasty', 'horrible', 'appalling', 'dreadful'},
    'hopeful':    {'hope', 'hopeful', 'optimistic', 'promising', 'encouraged', 'looking forward',
                   'bright', 'positive', 'confident', 'inspired'},
    'loving':     {'love', 'adore', 'cherish', 'affection', 'caring', 'devoted', 'passionate',
                   'romantic', 'warm', 'tender', 'fond'},
    'grateful':   {'grateful', 'thankful', 'appreciate', 'blessed', 'thank', 'thanks',
                   'gratitude', 'indebted'},
    'confused':   {'confused', 'puzzled', 'baffled', 'bewildered', 'perplexed', 'unclear',
                   'lost', 'uncertain', 'unsure'},
}


def _sentiment_fallback(text: str) -> str:
    words = set(text.lower().split())
    detected = {}
    for emotion, keywords in _EMOTION_KEYWORDS.items():
        count = len(words & keywords)
        if count > 0:
            detected[emotion] = count
    pos_emotions = {'happy', 'hopeful', 'loving', 'grateful', 'surprised'}
    neg_emotions = {'sad', 'angry', 'fearful', 'disgusted'}
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
    return "\n".join([
        f"**Overall Sentiment:** {sentiment}",
        f"**Confidence:** Low (keyword-based fallback)",
        f"**Primary Emotion:** {primary}",
        f"**Secondary Emotions:** {secondary}",
        f"**Sarcasm Detected:** Cannot detect (requires AI)",
        f"**Tone:** Cannot detect (requires AI)",
        "",
        "Note: Set GROQ_API_KEY for full AI-powered analysis with sarcasm detection and tone analysis.",
    ])


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
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text.strip()) if s.strip()]
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
        return await _ai_transform(_PROMPTS["seo_titles"], text, _seo_title_fallback, temperature=0.8, max_tokens=300)


class MetaDescriptionService:
    @staticmethod
    async def generate_meta_descriptions(text: str) -> str:
        return await _ai_transform(_PROMPTS["meta_descriptions"], text, _meta_description_fallback, temperature=0.8, max_tokens=400)


class BlogOutlineService:
    @staticmethod
    async def generate_blog_outline(text: str) -> str:
        return await _ai_transform(_PROMPTS["blog_outline"], text, _blog_outline_fallback, temperature=0.8, max_tokens=600)


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
        return await _ai_transform(prompt, text, _translate_fallback, target_language, temperature=0.3, max_tokens=1000)


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
        return await _ai_transform(prompt, text, _transliterate_fallback, target_language, temperature=0.2, max_tokens=1000)



class SummarizerService:
    @staticmethod
    async def summarize(text: str) -> str:
        return await _ai_transform(_PROMPTS["summarize"], text, _summarize_fallback, temperature=0.5, max_tokens=500)


class GrammarFixerService:
    @staticmethod
    async def fix_grammar(text: str) -> str:
        return await _ai_transform(_PROMPTS["grammar"], text, _grammar_fallback, temperature=0.3, max_tokens=1500)


class ParaphraserService:
    @staticmethod
    async def paraphrase(text: str) -> str:
        return await _ai_transform(_PROMPTS["paraphrase"], text, _paraphrase_fallback, temperature=0.8, max_tokens=1500)


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
        return await _ai_transform(_PROMPTS["sentiment"], text, _sentiment_fallback, temperature=0.2, max_tokens=400)



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
        return await _ai_transform(_PROMPTS["proofread"], text, _proofread_fallback, temperature=0.3, max_tokens=2000)


class TitleGeneratorService:
    @staticmethod
    async def generate_title(text: str) -> str:
        return await _ai_transform(_PROMPTS["generate_title"], text, _generate_title_fallback, temperature=0.8, max_tokens=300)


class FormatChangerService:
    @staticmethod
    async def change_format(text: str, fmt: str) -> str:
        base_prompt = _FORMAT_PROMPTS.get(fmt.lower(), _FORMAT_PROMPTS["paragraph"])
        prompt = (
            f"You are a text formatter. {base_prompt} "
            "Preserve ALL original information — only change the structure/format. "
            "Return ONLY the reformatted text, nothing else."
        )
        return await _ai_transform(prompt, text, _format_fallback, fmt, temperature=0.5, max_tokens=2000)
