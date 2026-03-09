"""
AIService — AI-powered text tools.

Primary: Groq API (Llama 3.3 70B) for context-aware generation.
Fallback: YAKE keyword extraction for offline / no-key usage.
"""

import yake
from groq import AsyncGroq
from app.core.config import settings


_MODEL = "llama-3.3-70b-versatile"


async def _groq_chat(system_prompt: str, user_text: str, temperature: float = 0.7, max_tokens: int = 200) -> str:
    """Shared Groq chat helper."""
    client = AsyncGroq(api_key=settings.GROQ_API_KEY)
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


def _yake_keywords(text: str, top: int = 10) -> list[str]:
    """Extract top keywords via YAKE."""
    extractor = yake.KeywordExtractor(lan="en", n=2, top=top, dedupLim=0.7)
    return [kw for kw, _score in extractor.extract_keywords(text)]


class HashtagService:

    @staticmethod
    async def generate_hashtags(text: str) -> str:
        """Generate hashtags. Uses Groq if API key is set, else YAKE fallback."""
        if settings.GROQ_API_KEY:
            try:
                return await _groq_chat(
                    "You are a hashtag generator. Given the user's text, "
                    "return 5-15 relevant, trending-style hashtags. "
                    "Return ONLY the hashtags separated by spaces, "
                    "each starting with #. No explanations, no numbering.",
                    text,
                )
            except Exception:
                pass
        keywords = _yake_keywords(text)
        return " ".join(f"#{kw.replace(' ', '').capitalize()}" for kw in keywords[:10])


class SEOTitleService:

    @staticmethod
    async def generate_seo_titles(text: str) -> str:
        """Generate SEO-optimized titles. Uses Groq if API key is set, else YAKE fallback."""
        if settings.GROQ_API_KEY:
            try:
                return await _groq_chat(
                    "You are an SEO title generator. Given the user's text, "
                    "generate 5 compelling, SEO-optimized title suggestions. "
                    "Each title should be 50-60 characters, include a primary keyword, "
                    "and be click-worthy. Return ONLY the titles, one per line, "
                    "numbered 1-5. No explanations.",
                    text,
                    temperature=0.8,
                    max_tokens=300,
                )
            except Exception:
                pass
        keywords = _yake_keywords(text, top=5)
        titles = []
        for i, kw in enumerate(keywords[:5], 1):
            titles.append(f"{i}. {kw.title()} — A Complete Guide")
        return "\n".join(titles)


class MetaDescriptionService:

    @staticmethod
    async def generate_meta_descriptions(text: str) -> str:
        """Generate SEO meta descriptions. Uses Groq if API key is set, else YAKE fallback."""
        if settings.GROQ_API_KEY:
            try:
                return await _groq_chat(
                    "You are a meta description generator for SEO. Given the user's text, "
                    "generate 3 compelling meta descriptions. Each must be 150-160 characters, "
                    "include a primary keyword, have a clear call-to-action, and entice clicks. "
                    "Return ONLY the descriptions, one per line, numbered 1-3. No explanations.",
                    text,
                    temperature=0.8,
                    max_tokens=400,
                )
            except Exception:
                pass
        keywords = _yake_keywords(text, top=3)
        descs = []
        for i, kw in enumerate(keywords[:3], 1):
            descs.append(f"{i}. Discover everything about {kw}. Read our comprehensive guide and learn key insights today.")
        return "\n".join(descs)


class BlogOutlineService:

    @staticmethod
    async def generate_blog_outline(text: str) -> str:
        """Generate a structured blog outline. Uses Groq if API key is set, else YAKE fallback."""
        if settings.GROQ_API_KEY:
            try:
                return await _groq_chat(
                    "You are a blog outline generator. Given the user's text or topic, "
                    "generate a well-structured blog post outline with: "
                    "a compelling title, an introduction section, 4-6 main sections "
                    "each with 2-3 sub-points, and a conclusion. "
                    "Use markdown-style formatting with # for title, ## for sections, "
                    "and - for sub-points. No explanations outside the outline.",
                    text,
                    temperature=0.8,
                    max_tokens=600,
                )
            except Exception:
                pass
        keywords = _yake_keywords(text, top=5)
        topic = keywords[0].title() if keywords else "Your Topic"
        sections = [f"# Blog Post: {topic}", "", "## Introduction", f"- Hook: Why {topic} matters", "- Brief overview of key points", ""]
        for i, kw in enumerate(keywords[1:5], 1):
            sections.append(f"## {i}. {kw.title()}")
            sections.append(f"- Key insight about {kw}")
            sections.append(f"- Practical tips and examples")
            sections.append("")
        sections.append("## Conclusion")
        sections.append("- Summary of key takeaways")
        sections.append("- Call to action")
        return "\n".join(sections)


class TweetShortenerService:

    @staticmethod
    async def shorten_for_tweet(text: str) -> str:
        """Shorten text to fit a tweet (280 chars). Uses Groq if API key is set, else naive truncation."""
        if settings.GROQ_API_KEY:
            try:
                return await _groq_chat(
                    "You are a tweet shortener. Given the user's text, "
                    "rewrite it to fit within 280 characters while preserving "
                    "the core message and meaning. Make it punchy and tweet-worthy. "
                    "Return ONLY the shortened text, nothing else. "
                    "Do NOT exceed 280 characters.",
                    text,
                    temperature=0.7,
                    max_tokens=100,
                )
            except Exception:
                pass
        # Fallback: truncate at last word boundary before 277 chars + "..."
        truncated = text[:277]
        last_space = truncated.rfind(" ")
        if last_space > 0:
            truncated = truncated[:last_space]
        return truncated + "..."


class EmailRewriterService:

    @staticmethod
    async def rewrite_email(text: str) -> str:
        """Rewrite text as a professional email. Uses Groq if API key is set, else basic template."""
        if settings.GROQ_API_KEY:
            try:
                return await _groq_chat(
                    "You are a professional email rewriter. Given the user's rough text or notes, "
                    "rewrite it as a clear, polished, professional email. "
                    "Include an appropriate greeting and sign-off. "
                    "Keep the tone professional yet friendly. Preserve all key information. "
                    "Return ONLY the rewritten email, nothing else.",
                    text,
                    temperature=0.7,
                    max_tokens=500,
                )
            except Exception:
                pass
        # Fallback: wrap in basic email template
        lines = text.strip().split('\n')
        subject = lines[0][:60] if lines else "Follow-up"
        body = text.strip()
        return f"Subject: {subject}\n\nDear recipient,\n\n{body}\n\nBest regards"


class BulletPointService:

    @staticmethod
    async def generate_bullet_points(text: str) -> str:
        """Convert text into concise bullet points. Uses Groq if API key is set, else sentence splitting."""
        if settings.GROQ_API_KEY:
            try:
                return await _groq_chat(
                    "You are a bullet point summarizer. Given the user's text, "
                    "extract the key points and rewrite them as clear, concise bullet points. "
                    "Each bullet should start with '•'. Keep each point to one line. "
                    "Aim for 5-10 bullet points covering the main ideas. "
                    "Return ONLY the bullet points, nothing else.",
                    text,
                    temperature=0.6,
                    max_tokens=400,
                )
            except Exception:
                pass
        # Fallback: split into sentences and prefix with bullet
        import re
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text.strip()) if s.strip()]
        return "\n".join(f"• {s}" for s in sentences[:10])


class KeywordExtractorService:

    @staticmethod
    async def extract_keywords(text: str) -> str:
        """Extract keywords from text. Uses Groq if API key is set, else YAKE."""
        if settings.GROQ_API_KEY:
            try:
                return await _groq_chat(
                    "You are a keyword extractor. Given the user's text, "
                    "identify 10-15 of the most important keywords and key phrases. "
                    "Return ONLY the keywords, one per line, ordered by relevance. "
                    "No numbering, no explanations.",
                    text,
                    temperature=0.3,
                    max_tokens=200,
                )
            except Exception:
                pass
        keywords = _yake_keywords(text, top=15)
        return "\n".join(keywords)


class TranslatorService:

    @staticmethod
    async def translate(text: str, target_language: str) -> str:
        """Translate text to target language. Uses Groq if API key is set, else returns error message."""
        if settings.GROQ_API_KEY:
            try:
                return await _groq_chat(
                    f"You are a translator. Translate the user's text into {target_language}. "
                    "Preserve the original meaning, tone, and formatting as closely as possible. "
                    "Return ONLY the translated text, nothing else. "
                    "Do not include any notes or explanations.",
                    text,
                    temperature=0.3,
                    max_tokens=1000,
                )
            except Exception:
                pass
        return f"[Translation requires Groq API key. Set GROQ_API_KEY in .env to enable translation to {target_language}.]"


class TransliterationService:

    @staticmethod
    async def transliterate(text: str, target_language: str) -> str:
        """Transliterate text into the script of the target language. Uses Groq if API key is set."""
        if settings.GROQ_API_KEY:
            try:
                return await _groq_chat(
                    f"You are a transliterator. Convert the user's text into {target_language} script "
                    "(transliteration, NOT translation). Keep the original words and sounds — "
                    "just write them using the {target_language} writing system. "
                    "For example, English 'hello' in Hindi script becomes 'हेलो'. "
                    "Return ONLY the transliterated text, nothing else.",
                    text,
                    temperature=0.2,
                    max_tokens=1000,
                )
            except Exception:
                pass
        return f"[Transliteration requires Groq API key. Set GROQ_API_KEY in .env to enable transliteration to {target_language}.]"
