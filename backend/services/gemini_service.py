"""
Central Gemini API client for ShieldAI.

Provides text analysis, vision analysis, audio transcription,
and chat capabilities via Google's Gemini API.
Each method has a graceful degradation fallback.
"""

import json
import os
import re
import time
import asyncio
from typing import Optional, Any

from logging_config import get_logger

logger = get_logger("shield_ai.gemini")

# Try to import new Google GenAI SDK
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    logger.warning("google_genai_not_installed", message="pip install google-genai")

# ── Centralized System Prompts (Section 13) ─────────────────

SCAM_DETECTION_SYSTEM_PROMPT = """
You are ShieldAI, an expert fraud detection system for India's Ministry of Home Affairs.
Your task is to analyse text descriptions of phone calls or messages and determine if they 
represent a "Digital Arrest Scam" or other financial fraud targeting Indian citizens.

KNOWN SCAM PATTERNS you must detect:
1. DIGITAL ARREST: Caller claims to be from CBI, ED, Customs, TRAI, RBI, or Police.
   Accuses victim of money laundering, drug trafficking, or illegal parcels.
   Threatens immediate arrest unless "verification money" is transferred.
   Often involves multi-day video call "custody."

2. KYC FRAUD: Claims to be from a bank or TRAI. Says KYC is expired. 
   Sends OTP and asks victim to share it. Drains account.

3. CUSTOMS SEIZURE: Claims a parcel with victim's name was seized at airport 
   containing drugs/foreign currency. Demands settlement payment.

4. INVESTMENT FRAUD: Fake stock tips, WhatsApp groups, promises of 3-5x returns.
   Platforms that let you see "profits" but block withdrawals.

ENTITIES to extract: agency names, phone numbers, amounts mentioned, 
transfer methods (NEFT/UPI/crypto), duration of interaction.

You must respond ONLY with a valid JSON object in this exact structure:
{
  "is_fraud": boolean,
  "confidence": float between 0.0 and 1.0,
  "fraud_type": "digital_arrest" | "kyc_fraud" | "customs_seizure" | "investment_fraud" | "other" | null,
  "agency_impersonated": string or null,
  "risk_level": "HIGH" | "MEDIUM" | "LOW",
  "key_red_flags": [list of specific phrases or patterns that indicate fraud],
  "extracted_entities": {
    "phone_numbers": [],
    "amounts_mentioned": [],
    "transfer_methods": []
  },
  "explanation": "2-3 sentence plain-language explanation for the citizen",
  "recommended_action": "Exact step-by-step instructions for the citizen right now"
}
"""

CURRENCY_ANALYSIS_SYSTEM_PROMPT = """
You are a currency authentication expert trained by the Reserve Bank of India (RBI).
You are analysing an uploaded image of an Indian currency note to determine its authenticity.

For Indian currency notes, check for these security features:
- INTAGLIO PRINTING: Raised print on denomination numerals, RBI Governor's signature
- SECURITY THREAD: Embedded windowed thread reading "BHARAT" and "RBI" alternately
- WATERMARK: Mahatma Gandhi portrait watermark visible when held to light
- MICROPRINTING: Tiny "BHARAT" and "INDIA" text on the security thread
- NUMBER PANEL: Ascending size numerals on the left, uniform size on the right
- OPTICALLY VARIABLE INK: Bottom-right numeral shifts from green to blue when tilted
- COLOUR SHIFT INK: Present on Rs 500 note in the numeral "500"
- LATENT IMAGE: Vertical band with "RBI" visible at 45 degrees on the right of Gandhi portrait
- SERIAL NUMBER FORMAT: For Rs 500: format like "1AA 000000" or "2AB 000000"
- PAPER QUALITY: Currency paper has red and blue fibers embedded randomly

Respond ONLY with a valid JSON object:
{
  "denomination_detected": int or null,
  "verdict": "GENUINE" | "SUSPICIOUS" | "COUNTERFEIT" | "UNCLEAR_IMAGE",
  "confidence": float between 0.0 and 1.0,
  "features_checked": {
    "intaglio_printing": "PASS" | "FAIL" | "UNCLEAR",
    "security_thread": "PASS" | "FAIL" | "UNCLEAR",
    "watermark": "PASS" | "FAIL" | "UNCLEAR",
    "microprinting": "PASS" | "FAIL" | "UNCLEAR",
    "serial_number_format": "PASS" | "FAIL" | "UNCLEAR",
    "colour_shift_ink": "PASS" | "FAIL" | "UNCLEAR",
    "paper_quality": "PASS" | "FAIL" | "UNCLEAR"
  },
  "failed_features": [list of feature names that failed],
  "analysis_narrative": "Detailed description of what you observed",
  "action_recommended": "What the person holding this note should do right now"
}
"""

CITIZEN_SHIELD_SYSTEM_PROMPT = """
You are ShieldAI's Citizen Fraud Shield, a friendly and calm assistant helping Indian 
citizens determine if they are being scammed. You speak with warmth and reassurance —
many people reaching out to you are frightened, embarrassed, or mid-crisis.

Your personality: calm, clear, non-judgmental, authoritative on fraud patterns.

BEHAVIOUR RULES:
1. You must automatically detect the language of the user's message and reply in THE EXACT SAME LANGUAGE, ignoring the language hint if they conflict.
   Supported: Hindi, Telugu, Tamil, Kannada, Malayalam, Bengali, Marathi, Gujarati, 
   Punjabi, Odia, Assamese, English.
2. Never shame the citizen for falling for a scam — fraudsters are sophisticated professionals.
3. If the person seems to be in an ACTIVE SCAM right now (present tense, happening now):
   - Immediately tell them to HANG UP / CLOSE the app / disconnect
   - Tell them NOT to transfer money
   - Tell them it is definitely a scam
   - Give NCRB Cybercrime Portal: cybercrime.gov.in | Helpline: 1930
4. Always end with the NCRB reporting link and Cyber Helpline 1930.
5. Extract any phone numbers, agency names, or amounts mentioned and flag them.

NCRB Cybercrime Portal: https://cybercrime.gov.in
National Cyber Helpline: 1930
"""

EVIDENCE_PACKAGE_PROMPT = """
You are a forensic intelligence analyst at India's National Cyber Crime Reporting Portal.
Based on the fraud intelligence data provided, generate a structured, court-admissible 
intelligence package for the law enforcement agency investigating this fraud ring.

The package must be professional, factual, and suitable for submission to a magistrate.
Use formal language. Do not speculate — only report what the data shows.

Structure your output as:
1. EXECUTIVE SUMMARY (3-5 sentences)
2. FRAUD RING PROFILE (operation type, geographic reach, estimated victim count)
3. KEY ENTITIES (phone numbers, accounts, devices — with their roles in the ring)
4. VICTIM IMPACT ASSESSMENT (estimated financial damage, number of victims)
5. TRANSACTION PATTERN ANALYSIS (how money flows through the network)
6. GEOGRAPHIC INTELLIGENCE (where complaints originated, where money went)
7. RECOMMENDED LAW ENFORCEMENT ACTIONS
8. DATA SOURCES AND COLLECTION METHODOLOGY
9. CONFIDENCE ASSESSMENT (what is certain vs. inferred)

Intelligence Data:
{intelligence_data}
"""


class GeminiService:
    """
    Central Gemini API client. Initializes once, reused across requests.
    Falls back to keyword-based heuristics when API key is not configured.
    """

    def __init__(self, api_key: str = "", model_name: str = "gemini-2.0-flash"):
        self.api_key = api_key
        self.model_name = model_name
        self.client = None
        self._available = False

        if GENAI_AVAILABLE and api_key:
            try:
                self.client = genai.Client(api_key=api_key)
                self._available = True
                logger.info("gemini_initialized", model=model_name)
            except Exception as e:
                logger.error("gemini_init_failed", error=str(e))
        else:
            reason = "no API key" if GENAI_AVAILABLE else "SDK not installed"
            logger.warning("gemini_unavailable", reason=reason, message="Using fallback heuristics")

    @property
    def is_available(self) -> bool:
        return self._available

    # ── JSON Parsing Utility ─────────────────────────────────

    def safe_parse_json_response(self, response_text: str) -> Optional[dict]:
        """
        Safely parse a Gemini response that should contain JSON.

        Handles:
        - Raw JSON
        - JSON wrapped in markdown code fences (```json ... ```)
        - JSON with leading/trailing whitespace

        Returns:
            Parsed dict, or None if parsing fails.
        """
        if not response_text:
            return None

        text = response_text.strip()

        # Strip markdown code fences if present
        fence_pattern = re.compile(r'^```(?:json)?\s*\n?(.*?)\n?\s*```$', re.DOTALL)
        match = fence_pattern.match(text)
        if match:
            text = match.group(1).strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning("json_parse_failed", error=str(e), response_preview=text[:200])
            return None

    def build_model_metadata(
        self,
        latency_ms: float = 0.0,
        fallback_used: bool = False,
        prompt_version: str = "v1",
    ) -> dict:
        """Build standardized model metadata for result provenance."""
        from config import settings
        return {
            "primary_provider": "gemini",
            "primary_model": self.model_name,
            "zero_shot_enabled": settings.ENABLE_ZERO_SHOT,
            "zero_shot_model": settings.ZERO_SHOT_MODEL,
            "prompt_version": prompt_version,
            "latency_ms": round(latency_ms, 1),
            "fallback_used": fallback_used,
        }

    # ── Scam Text Analysis ───────────────────────────────────

    async def analyze_scam_text(self, text: str, language: str = "en") -> dict:
        """
        Analyze text for scam patterns using Gemini or fallback heuristics.

        Returns:
            dict with: risk_score, risk_label, classification, scam_type,
                       explanation, recommended_action
        """
        if self._available:
            try:
                return await self._gemini_scam_analysis(text, language)
            except Exception as e:
                logger.error("gemini_scam_analysis_failed", error=str(e), fallback=True)

        return self._fallback_scam_analysis(text)

    async def _gemini_scam_analysis(self, text: str, language: str) -> dict:
        """Real Gemini API call for scam analysis with retries and timeout."""
        start = time.monotonic()
        contents = f"Analyze this report (Language hint: {language}):\n\n{text}"
        
        max_retries = 3
        response = None
        for attempt in range(max_retries):
            try:
                # Assuming google-genai client supports timeout via config, if not, we use asyncio.wait_for
                task = self.client.aio.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=SCAM_DETECTION_SYSTEM_PROMPT,
                        response_mime_type="application/json",
                        temperature=0.1,
                    ),
                )
                response = await asyncio.wait_for(task, timeout=30.0)
                break
            except asyncio.TimeoutError:
                logger.warning("gemini_scam_analysis_timeout", attempt=attempt+1)
                if attempt == max_retries - 1:
                    raise
            except Exception as e:
                logger.warning("gemini_scam_analysis_error", error=str(e), attempt=attempt+1)
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
        latency_ms = (time.monotonic() - start) * 1000

        result = self.safe_parse_json_response(response.text)
        if result is None:
            logger.error("gemini_scam_json_parse_failed", response_preview=response.text[:200])
            # Fall back to heuristic on parse failure
            result = self._fallback_scam_analysis(text)
            result["model_metadata"] = self.build_model_metadata(
                latency_ms=latency_ms, fallback_used=True, prompt_version="scam_v1"
            )
            return result

        # Map Gemini response fields to internal schema
        return {
            "risk_score": max(0.0, min(1.0, float(result.get("confidence", result.get("risk_score", 0.5))))),
            "risk_label": result.get("risk_level", result.get("risk_label", "MEDIUM")),
            "classification": result.get("fraud_type", result.get("classification", "unknown")),
            "scam_type": result.get("fraud_type"),
            "explanation": result.get("explanation", "Analysis complete."),
            "recommended_action": result.get("recommended_action", "Stay vigilant."),
            "extracted_entities": result.get("extracted_entities", {}),
            "key_red_flags": result.get("key_red_flags", []),
            "model_metadata": self.build_model_metadata(
                latency_ms=latency_ms, prompt_version="scam_v1"
            )
        }

    def _fallback_scam_analysis(self, text: str) -> dict:
        """Keyword-based heuristic fallback for scam analysis."""
        text_lower = text.lower()

        # Weighted keyword groups
        high_risk_keywords = {
            "digital arrest": 0.35, "arrest warrant": 0.30, "cbi": 0.25,
            "enforcement directorate": 0.25, "ed officer": 0.25,
            "customs": 0.20, "money laundering": 0.30, "hawala": 0.30,
            "narcotics": 0.25, "drug trafficking": 0.25,
            "transfer money": 0.30, "send money immediately": 0.35,
            "your aadhaar": 0.20, "your pan card": 0.20,
            "account will be blocked": 0.25, "account frozen": 0.25,
            "police case": 0.20, "fir registered": 0.20,
            "video call verification": 0.25, "kyc expired": 0.25,
            "rbi circular": 0.20, "trai": 0.20,
            "sim will be blocked": 0.25, "legal action": 0.20,
        }

        medium_risk_keywords = {
            "verify your identity": 0.10, "otp": 0.10, "click this link": 0.15,
            "urgent": 0.10, "immediately": 0.10, "prize": 0.15,
            "lottery": 0.20, "congratulations you won": 0.20,
            "investment opportunity": 0.15, "guaranteed returns": 0.20,
            "bank manager": 0.10, "insurance claim": 0.10,
        }

        score = 0.0
        matched_keywords = []

        for keyword, weight in high_risk_keywords.items():
            if keyword in text_lower:
                score += weight
                matched_keywords.append(keyword)

        for keyword, weight in medium_risk_keywords.items():
            if keyword in text_lower:
                score += weight
                matched_keywords.append(keyword)

        score = min(1.0, score)

        # Determine classification
        if any(k in text_lower for k in ["digital arrest", "arrest warrant", "cbi", "enforcement directorate"]):
            classification = "digital_arrest_scam"
            scam_type = "Digital Arrest Scam"
        elif any(k in text_lower for k in ["kyc", "pan card", "aadhaar"]):
            classification = "kyc_fraud"
            scam_type = "KYC/Identity Fraud"
        elif any(k in text_lower for k in ["customs", "parcel", "seized"]):
            classification = "customs_scam"
            scam_type = "Customs Seizure Scam"
        elif any(k in text_lower for k in ["lottery", "prize", "won"]):
            classification = "lottery_scam"
            scam_type = "Lottery/Prize Scam"
        elif any(k in text_lower for k in ["investment", "guaranteed returns", "trading"]):
            classification = "investment_scam"
            scam_type = "Investment Fraud"
        elif score > 0.3:
            classification = "financial_fraud"
            scam_type = "General Financial Fraud"
        else:
            classification = "legitimate" if score < 0.2 else "unknown"
            scam_type = None

        if score >= 0.7:
            risk_label = "HIGH"
        elif score >= 0.4:
            risk_label = "MEDIUM"
        else:
            risk_label = "LOW"

        if matched_keywords:
            explanation = f"Analysis detected the following risk indicators: {', '.join(matched_keywords[:5])}. "
            if risk_label == "HIGH":
                explanation += "This strongly matches known scam patterns used in India."
            elif risk_label == "MEDIUM":
                explanation += "Some elements match known fraud patterns. Exercise caution."
            else:
                explanation += "Low risk indicators detected."
        else:
            explanation = "No known scam patterns detected in this text."

        actions = {
            "HIGH": "DO NOT engage further. Do NOT transfer any money. Hang up immediately. Report to cybercrime.gov.in or call 1930.",
            "MEDIUM": "Exercise caution. Verify the caller's identity independently. Do not share personal information or OTPs.",
            "LOW": "This appears to be low risk, but remain vigilant. Never share OTPs or passwords over phone.",
        }

        return {
            "risk_score": round(score, 3),
            "risk_label": risk_label,
            "classification": classification,
            "scam_type": scam_type,
            "explanation": explanation,
            "recommended_action": actions[risk_label],
        }

    # ── Currency Image Analysis ──────────────────────────────

    async def analyze_currency_image(self, image_bytes: bytes, denomination: Optional[int] = None, mime_type: str = "image/jpeg") -> dict:
        """
        Analyze a currency image for authenticity using Gemini Vision.

        Returns:
            dict with: verdict, confidence, failed_features, analysis
        """
        if self._available:
            try:
                return await self._gemini_currency_analysis(image_bytes, denomination, mime_type)
            except Exception as e:
                logger.error("gemini_currency_analysis_failed", error=str(e), fallback=True)

        return self._fallback_currency_analysis(denomination)

    async def _gemini_currency_analysis(self, image_bytes: bytes, denomination: Optional[int], mime_type: str = "image/jpeg") -> dict:
        """Real Gemini Vision API call for currency analysis with retries and timeout."""
        start = time.monotonic()
        denom_hint = f"The user believes this is a Rs {denomination} note." if denomination else ""
        contents_text = f"Analyse this Indian currency note image. {denom_hint} Check all security features carefully."

        # Convert bytes to Part for google-genai
        image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)

        max_retries = 3
        response = None
        for attempt in range(max_retries):
            try:
                task = self.client.aio.models.generate_content(
                    model=self.model_name,
                    contents=[contents_text, image_part],
                    config=types.GenerateContentConfig(
                        system_instruction=CURRENCY_ANALYSIS_SYSTEM_PROMPT,
                        response_mime_type="application/json",
                        temperature=0.1,
                    ),
                )
                response = await asyncio.wait_for(task, timeout=45.0)
                break
            except asyncio.TimeoutError:
                logger.warning("gemini_currency_analysis_timeout", attempt=attempt+1)
                if attempt == max_retries - 1:
                    raise
            except Exception as e:
                logger.warning("gemini_currency_analysis_error", error=str(e), attempt=attempt+1)
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)

        latency_ms = (time.monotonic() - start) * 1000

        result = self.safe_parse_json_response(response.text)
        if result is None:
            logger.error("gemini_currency_json_parse_failed", response_preview=response.text[:200])
            result = self._fallback_currency_analysis(denomination)
            result["model_metadata"] = self.build_model_metadata(
                latency_ms=latency_ms, fallback_used=True, prompt_version="currency_v1"
            )
            return result

        result["confidence"] = max(0.0, min(1.0, float(result.get("confidence", 0.5))))
        result["model_metadata"] = self.build_model_metadata(
            latency_ms=latency_ms, prompt_version="currency_v1"
        )
        return result

    def _fallback_currency_analysis(self, denomination: Optional[int] = None) -> dict:
        """Fallback currency analysis when Gemini is unavailable."""
        return {
            "verdict": "UNCLEAR_IMAGE",
            "confidence": 0.5,
            "failed_features": ["automated_analysis_unavailable"],
            "analysis": (
                f"Automated AI analysis is currently unavailable. "
                f"The image of the {'Rs ' + str(denomination) + ' ' if denomination else ''}"
                f"note could not be verified. Please have the note physically inspected "
                f"by a trained bank teller or use an RBI-approved detection device."
            ),
        }

    # ── Audio Transcription ──────────────────────────────────

    async def transcribe_audio(self, audio_bytes: bytes, mime_type: str = "audio/mpeg") -> str:
        """
        Transcribe audio using Gemini's native audio capabilities.

        Returns:
            Transcribed text string
        """
        if not self._available:
            raise RuntimeError("Gemini API is not available. Cannot transcribe audio.")

        try:
            audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
            prompt = (
                "Transcribe the following audio accurately. "
                "If the audio is in Hindi or another Indian language, "
                "provide the transcription in that language along with an English translation. "
                "Return ONLY the transcription text, nothing else."
            )

            max_retries = 3
            response = None
            for attempt in range(max_retries):
                try:
                    task = self.client.aio.models.generate_content(
                        model=self.model_name,
                        contents=[prompt, audio_part],
                        config=types.GenerateContentConfig(temperature=0.1),
                    )
                    response = await asyncio.wait_for(task, timeout=60.0)
                    break
                except asyncio.TimeoutError:
                    logger.warning("gemini_audio_transcription_timeout", attempt=attempt+1)
                    if attempt == max_retries - 1:
                        raise
                except Exception as e:
                    logger.warning("gemini_audio_transcription_error", error=str(e), attempt=attempt+1)
                    if attempt == max_retries - 1:
                        raise
                    await asyncio.sleep(2 ** attempt)

            transcript = response.text.strip()
            logger.info("audio_transcribed", length=len(transcript))
            return transcript

        except Exception as e:
            logger.error("audio_transcription_failed", error=str(e))
            raise RuntimeError(f"Audio transcription failed: {str(e)}")

    # ── Citizen Chat ─────────────────────────────────────────

    async def chat_response(self, message: str, session_id: str, language: str = "en") -> dict:
        """
        Generate a chatbot response for the citizen fraud shield.

        Returns:
            dict with: response, risk_assessment (optional)
        """
        if self._available:
            try:
                return await self._gemini_chat(message, session_id, language)
            except Exception as e:
                logger.error("gemini_chat_failed", error=str(e), fallback=True)

        return self._fallback_chat(message)

    async def _gemini_chat(self, message: str, session_id: str, language: str) -> dict:
        """Real Gemini chat response."""
        contents = f"Session ID: {session_id}\nLanguage preference: {language}\nUser message: {message}"

        max_retries = 3
        response = None
        for attempt in range(max_retries):
            try:
                task = self.client.aio.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=CITIZEN_SHIELD_SYSTEM_PROMPT,
                        temperature=0.7,
                    ),
                )
                response = await asyncio.wait_for(task, timeout=20.0)
                break
            except asyncio.TimeoutError:
                logger.warning("gemini_chat_timeout", attempt=attempt+1)
                if attempt == max_retries - 1:
                    raise
            except Exception as e:
                logger.warning("gemini_chat_error", error=str(e), attempt=attempt+1)
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)

        result = self.safe_parse_json_response(response.text)
        if result is None:
            # Chat can gracefully fall back to plain text
            return {"response": response.text.strip() if response.text else "", "risk_assessment": None}
        return result

    def _fallback_chat(self, message: str) -> dict:
        """Template-based fallback chat responses."""
        message_lower = message.lower()

        # Check for scam-related keywords
        if any(k in message_lower for k in ["scam", "fraud", "arrest", "cbi", "police", "money"]):
            return {
                "response": (
                    "I understand you may be dealing with a potential scam situation. "
                    "Please do NOT transfer any money or share personal details like OTPs. "
                    "If someone is claiming to be from CBI, Police, or any government agency and "
                    "threatening arrest, this is a known 'Digital Arrest' scam. "
                    "Report immediately at cybercrime.gov.in or call the helpline 1930."
                ),
                "risk_assessment": {
                    "detected_risk": True,
                    "risk_level": "HIGH",
                    "risk_type": "potential_scam_inquiry",
                },
            }
        elif any(k in message_lower for k in ["report", "complaint", "file", "fir"]):
            return {
                "response": (
                    "To file a cybercrime complaint, you can: "
                    "1) Visit cybercrime.gov.in and file an online complaint, "
                    "2) Call the national cybercrime helpline at 1930, or "
                    "3) Visit your nearest police station. "
                    "You can also use the 'Report Fraud' feature in this app to submit details."
                ),
                "risk_assessment": None,
            }
        elif any(k in message_lower for k in ["hello", "hi", "help", "start"]):
            return {
                "response": (
                    "Welcome to ShieldAI's Citizen Fraud Shield! I can help you: "
                    "• Check if a call or message is a scam — just describe what happened "
                    "• Report fraud or cybercrime "
                    "• Get safety tips and resources. "
                    "How can I help you today?"
                ),
                "risk_assessment": None,
            }
        else:
            return {
                "response": (
                    "Thank you for reaching out. I'm here to help you with fraud-related concerns. "
                    "You can describe a suspicious call or message you received, and I'll analyze it "
                    "for scam patterns. If you need immediate help, call the cybercrime helpline at 1930."
                ),
                "risk_assessment": None,
            }

    # ── Evidence Package Synthesis ───────────────────────────

    async def generate_evidence_package(self, intelligence_data: dict) -> str:
        """
        Generate a structured, court-admissible evidence package summary
        using Gemini.
        """
        if self._available:
            try:
                prompt = EVIDENCE_PACKAGE_PROMPT.format(
                    intelligence_data=json.dumps(intelligence_data, indent=2)
                )
                
                max_retries = 3
                response = None
                for attempt in range(max_retries):
                    try:
                        task = self.client.aio.models.generate_content(
                            model=self.model_name,
                            contents=prompt,
                            config=types.GenerateContentConfig(temperature=0.1),
                        )
                        response = await asyncio.wait_for(task, timeout=45.0)
                        break
                    except asyncio.TimeoutError:
                        logger.warning("gemini_evidence_package_timeout", attempt=attempt+1)
                        if attempt == max_retries - 1:
                            raise
                    except Exception as e:
                        logger.warning("gemini_evidence_package_error", error=str(e), attempt=attempt+1)
                        if attempt == max_retries - 1:
                            raise
                        await asyncio.sleep(2 ** attempt)
                        
                return response.text.strip()
            except Exception as e:
                logger.error("gemini_evidence_package_failed", error=str(e), fallback=True)

        return self._fallback_evidence_package(intelligence_data)

    def _fallback_evidence_package(self, intelligence_data: dict) -> str:
        """Fallback text summary when Gemini is offline."""
        cluster = intelligence_data.get("cluster", {})
        summary = intelligence_data.get("summary", {})
        key_findings = intelligence_data.get("key_findings", [])
        
        findings_str = "\n".join(f"- {f}" for f in key_findings)
        
        cluster_name = cluster.get('name') or cluster.get('cluster_name') or 'Unknown'
        
        return f"""FORENSIC INTELLIGENCE REPORT (FALLBACK METHOD)
==================================================
1. EXECUTIVE SUMMARY
This intelligence package details the coordinated activity of fraud ring {cluster_name}.
The network encompasses {summary.get('total_entities', 0)} entities linked by {summary.get('total_relationships', 0)} connections.

2. FRAUD RING PROFILE
- Cluster ID: {cluster.get('id', 'N/A')}
- Risk Level: {cluster.get('risk_level', 'Unknown')}
- Operation Type: {cluster.get('operation_type', 'Unknown')}
- Geographic Reach: {cluster.get('geographic_span', 'Unknown')}

3. KEY FINDINGS
{findings_str}

4. CONCLUSION
This fallback report compiles direct database indicators. Standardize with full AI-synthesized analysis once Gemini is online.
"""


# Module-level singleton (initialized in main.py lifespan)
_gemini_service: GeminiService | None = None


def get_gemini_service() -> GeminiService:
    """Get the initialized GeminiService singleton."""
    global _gemini_service
    if _gemini_service is None:
        from config import settings
        _gemini_service = GeminiService(
            api_key=settings.GEMINI_API_KEY,
            model_name=settings.GEMINI_MODEL,
        )
    return _gemini_service


def init_gemini_service(api_key: str, model_name: str) -> GeminiService:
    """Initialize the GeminiService singleton."""
    global _gemini_service
    _gemini_service = GeminiService(api_key=api_key, model_name=model_name)
    return _gemini_service
