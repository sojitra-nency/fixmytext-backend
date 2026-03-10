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


class PunctuationFixerService:

    @staticmethod
    async def fix_punctuation(text: str) -> str:
        """Fix punctuation and special characters based on sentence formation. Uses Groq if API key is set."""
        if settings.GROQ_API_KEY:
            try:
                return await _groq_chat(
                    "You are a punctuation and grammar fixer. Given the user's text, "
                    "fix all punctuation and special characters based on proper sentence formation. "
                    "Add missing periods, commas, question marks, exclamation marks, apostrophes, "
                    "quotation marks, colons, semicolons, and hyphens where needed. "
                    "Remove unnecessary or misplaced special characters. "
                    "Fix spacing around punctuation. Capitalize after periods. "
                    "Preserve the original words and meaning — only fix punctuation and formatting. "
                    "Return ONLY the corrected text, nothing else.",
                    text,
                    temperature=0.3,
                    max_tokens=1500,
                )
            except Exception:
                pass
        # Fallback: basic punctuation fixes
        import re
        result = text.strip()
        # Fix multiple spaces
        result = re.sub(r' +', ' ', result)
        # Fix spacing before punctuation
        result = re.sub(r' ([.,!?;:])', r'\1', result)
        # Add space after punctuation if missing
        result = re.sub(r'([.,!?;:])([A-Za-z])', r'\1 \2', result)
        # Capitalize first letter of sentences
        result = re.sub(r'([.!?]\s+)([a-z])', lambda m: m.group(1) + m.group(2).upper(), result)
        # Capitalize first character
        if result and result[0].islower():
            result = result[0].upper() + result[1:]
        # Ensure ends with period if no ending punctuation
        if result and result[-1] not in '.!?':
            result += '.'
        return result


class SummarizerService:

    @staticmethod
    async def summarize(text: str) -> str:
        """Summarize text. Uses Groq if API key is set, else naive truncation."""
        if settings.GROQ_API_KEY:
            try:
                return await _groq_chat(
                    "You are a text summarizer. Given the user's text, "
                    "produce a clear, concise summary that captures all key points. "
                    "The summary should be significantly shorter than the original. "
                    "Return ONLY the summary, nothing else.",
                    text,
                    temperature=0.5,
                    max_tokens=500,
                )
            except Exception:
                pass
        # Fallback: return first 3 sentences
        import re
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text.strip()) if s.strip()]
        return " ".join(sentences[:3]) + ("..." if len(sentences) > 3 else "")


class GrammarFixerService:

    @staticmethod
    async def fix_grammar(text: str) -> str:
        """Fix grammar in text. Uses Groq if API key is set, else returns basic fixes."""
        if settings.GROQ_API_KEY:
            try:
                return await _groq_chat(
                    "You are a grammar fixer. Given the user's text, "
                    "fix all grammatical errors including subject-verb agreement, "
                    "tense consistency, article usage, pronoun references, "
                    "sentence fragments, and run-on sentences. "
                    "Preserve the original meaning and tone. "
                    "Return ONLY the corrected text, nothing else.",
                    text,
                    temperature=0.3,
                    max_tokens=1500,
                )
            except Exception:
                pass
        # Fallback: basic capitalization fix
        import re
        result = re.sub(r'([.!?]\s+)([a-z])', lambda m: m.group(1) + m.group(2).upper(), text)
        if result and result[0].islower():
            result = result[0].upper() + result[1:]
        return result


class ParaphraserService:

    @staticmethod
    async def paraphrase(text: str) -> str:
        """Paraphrase text. Uses Groq if API key is set, else returns original."""
        if settings.GROQ_API_KEY:
            try:
                return await _groq_chat(
                    "You are a paraphraser. Given the user's text, "
                    "rewrite it using different words and sentence structures "
                    "while preserving the original meaning completely. "
                    "Make it sound natural and fluent. "
                    "Return ONLY the paraphrased text, nothing else.",
                    text,
                    temperature=0.8,
                    max_tokens=1500,
                )
            except Exception:
                pass
        return "[Paraphrasing requires Groq API key. Set GROQ_API_KEY in .env to enable.]"


class ToneChangerService:

    @staticmethod
    async def change_tone(text: str, tone: str) -> str:
        """Change the tone of text. Uses Groq if API key is set."""
        tone_instructions = {
            "formal": "Rewrite in a formal, professional tone. Use proper language, avoid contractions and slang.",
            "casual": "Rewrite in a casual, relaxed tone. Use everyday language, contractions, and a conversational style.",
            "friendly": "Rewrite in a warm, friendly tone. Be approachable, positive, and personable.",
        }
        instruction = tone_instructions.get(tone.lower(), tone_instructions["formal"])
        if settings.GROQ_API_KEY:
            try:
                return await _groq_chat(
                    f"You are a tone changer. Given the user's text, {instruction} "
                    "Preserve the original meaning completely. "
                    "Return ONLY the rewritten text, nothing else.",
                    text,
                    temperature=0.7,
                    max_tokens=1500,
                )
            except Exception:
                pass
        return f"[Tone changing requires Groq API key. Set GROQ_API_KEY in .env to enable {tone} tone.]"


class SentimentAnalyzerService:

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

    @staticmethod
    async def analyze_sentiment(text: str) -> str:
        """Analyze sentiment of text. Uses Groq if API key is set, else keyword-based guess."""
        if settings.GROQ_API_KEY:
            try:
                return await _groq_chat(
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
                    "Format the output clearly with the bold labels above.",
                    text,
                    temperature=0.2,
                    max_tokens=400,
                )
            except Exception:
                pass
        # Fallback: keyword-based emotion detection
        words = set(text.lower().split())
        detected = {}
        for emotion, keywords in SentimentAnalyzerService._EMOTION_KEYWORDS.items():
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
        lines = [
            f"**Overall Sentiment:** {sentiment}",
            f"**Confidence:** Low (keyword-based fallback)",
            f"**Primary Emotion:** {primary}",
            f"**Secondary Emotions:** {secondary}",
            f"**Sarcasm Detected:** Cannot detect (requires AI)",
            f"**Tone:** Cannot detect (requires AI)",
            "",
            "Note: Set GROQ_API_KEY for full AI-powered analysis with sarcasm detection and tone analysis.",
        ]
        return "\n".join(lines)


class TextShortenerService:

    @staticmethod
    async def shorten(text: str) -> str:
        """Shorten text while preserving meaning. Uses Groq if API key is set."""
        if settings.GROQ_API_KEY:
            try:
                return await _groq_chat(
                    "You are a text shortener. Given the user's text, "
                    "make it significantly shorter and more concise while preserving "
                    "all key information and meaning. Remove redundancy, wordiness, "
                    "and unnecessary filler. Keep the same tone and style. "
                    "Return ONLY the shortened text, nothing else.",
                    text,
                    temperature=0.5,
                    max_tokens=1000,
                )
            except Exception:
                pass
        # Fallback: keep first half of sentences
        import re
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text.strip()) if s.strip()]
        half = max(1, len(sentences) // 2)
        return " ".join(sentences[:half])


class TextLengthenerService:

    @staticmethod
    async def lengthen(text: str) -> str:
        """Lengthen text with more detail. Uses Groq if API key is set."""
        if settings.GROQ_API_KEY:
            try:
                return await _groq_chat(
                    "You are a text expander. Given the user's text, "
                    "expand and elaborate on it to make it longer and more detailed. "
                    "Add relevant explanations, examples, and supporting details. "
                    "Maintain the original meaning, tone, and style. "
                    "Do not add unrelated information. "
                    "Return ONLY the expanded text, nothing else.",
                    text,
                    temperature=0.7,
                    max_tokens=2000,
                )
            except Exception:
                pass
        return "[Text lengthening requires Groq API key. Set GROQ_API_KEY in .env to enable.]"


class FormatChangerService:

    FORMAT_PROMPTS = {
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

    @staticmethod
    async def change_format(text: str, fmt: str) -> str:
        """Change the format/structure of text. Uses Groq if API key is set."""
        prompt = FormatChangerService.FORMAT_PROMPTS.get(
            fmt.lower(),
            FormatChangerService.FORMAT_PROMPTS["paragraph"],
        )
        if settings.GROQ_API_KEY:
            try:
                return await _groq_chat(
                    f"You are a text formatter. {prompt} "
                    "Preserve ALL original information — only change the structure/format. "
                    "Return ONLY the reformatted text, nothing else.",
                    text,
                    temperature=0.5,
                    max_tokens=2000,
                )
            except Exception:
                pass
        # Fallback: basic formatting
        import re
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
            for i, s in enumerate(sentences):
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
