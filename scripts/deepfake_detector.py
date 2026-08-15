import re

class DeepfakeDetector:
    """
    Deepfake Text Detection Module (Chong et al., 2023 / MemoryBridge Section III-H-1).
    Analyzes machine-generated text using sentiment polarity, perplexity proxies, POS patterns,
    and linguistic feature ratios to calculate AI-generation confidence and enforce AI disclosure indicators.
    """
    def __init__(self):
        pass

    def analyze_text(self, text, emotion_label="neutral"):
        """
        Analyze generated text to determine AI-generation confidence based on linguistic signals.
        Key detection signals from Section III-H-1:
        1. Neutral Sentiment: Machine text exhibits higher neutral sentiment proportions.
        2. POS Ratios: AI text uses higher NOUN, PRON, DET, ADP ratios; lower PROPN and ADV ratios.
        3. Perplexity Proxy: Low variance in transitions and repetitive syntactic structures.
        """
        score = 0
        signals = []
        text_lower = text.lower()
        words = text.split()
        total_words = max(1, len(words))

        # 1. Sentiment feature: AI text leans neutral
        if emotion_label.lower() == "neutral":
            score += 25
            signals.append("neutral_sentiment_bias")

        # 2. Pronoun & Determiner ratio (PRON, DET)
        pronouns = len(re.findall(r'\b(i|you|he|she|it|we|they|me|him|us|them|my|your|his|her|its|our|their)\b', text_lower))
        determiners = len(re.findall(r'\b(a|an|the|this|that|these|those)\b', text_lower))
        pron_det_ratio = (pronouns + determiners) / total_words
        if pron_det_ratio > 0.20:
            score += 20
            signals.append("high_pronoun_determiner_ratio")

        # 3. Transitions & Connectives (Perplexity / predictability proxy)
        transitions = ["however", "furthermore", "therefore", "additionally", "in conclusion", "indeed", "always", "never"]
        found_trans = [t for t in transitions if t in text_lower]
        if found_trans:
            score += 25
            signals.append(f"predictable_transitions({','.join(found_trans)})")

        # 4. Sentence length uniformity (low variance in AI output)
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
        if len(sentences) > 1:
            lengths = [len(s.split()) for s in sentences]
            mean_len = sum(lengths) / len(lengths)
            variance = sum((x - mean_len) ** 2 for x in lengths) / len(lengths)
            if variance < 6.0:
                score += 20
                signals.append("uniform_sentence_structure")

        # Calculate final AI confidence (Base score 50% for LLM outputs)
        confidence_score = min(99, 50 + score)

        # Enforce Section III-H-1: "All responses are labelled with a visible AI disclosure indicator"
        return {
            "is_ai_generated": True,
            "confidence_score": confidence_score,
            "signals": signals,
            "heuristics_triggered": len(signals) > 0,
            "disclosure_label": "AI GENERATED (MemoryBridge Digital Imitation)"
        }

# Global singleton instance
detector = DeepfakeDetector()

