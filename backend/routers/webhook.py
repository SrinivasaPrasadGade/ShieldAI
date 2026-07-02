"""
WhatsApp webhook router for ShieldAI.

Endpoint:
  POST /webhook/whatsapp — Twilio WhatsApp webhook
"""

from fastapi import APIRouter, Request, Response, HTTPException
from xml.sax.saxutils import escape as xml_escape

from logging_config import get_logger

logger = get_logger("shield_ai.router.webhook")

router = APIRouter(tags=["Webhooks"])


@router.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    """
    Twilio WhatsApp webhook endpoint.

    Receives incoming WhatsApp messages via Twilio's webhook format,
    processes them through the scam detection pipeline, and returns
    a TwiML response.

    Requires TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in .env.
    """
    from config import settings

    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        raise HTTPException(
            status_code=503,
            detail="WhatsApp webhook not configured. Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in .env",
        )

    try:
        # Parse form data from Twilio
        form_data = await request.form()
        form_dict = dict(form_data)

        try:
            from twilio.request_validator import RequestValidator
            validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
            public_url = str(request.url)
            forwarded_proto = request.headers.get("x-forwarded-proto")
            forwarded_host = request.headers.get("x-forwarded-host")
            if forwarded_proto and forwarded_host:
                public_url = f"{forwarded_proto}://{forwarded_host}{request.url.path}"

            signature = request.headers.get("x-twilio-signature", "")
            is_placeholder = "your-twilio" in settings.TWILIO_AUTH_TOKEN.lower()
            if not validator.validate(public_url, form_dict, signature):
                if is_placeholder:
                    logger.warning("twilio_signature_skipped_placeholder_credentials")
                elif settings.DEBUG:
                    logger.warning("twilio_signature_invalid_debug_mode")
                else:
                    logger.warning("twilio_signature_invalid")
                    raise HTTPException(status_code=403, detail="Invalid Twilio signature")
        except HTTPException:
            raise
        except Exception as validation_error:
            logger.error("twilio_signature_validation_failed", error=str(validation_error))
            raise HTTPException(status_code=503, detail="Twilio signature validation unavailable")

        incoming_msg = form_data.get("Body", "").strip()
        from_number = form_data.get("From", "").replace("whatsapp:", "")
        to_number = form_data.get("To", "")
        message_sid = form_data.get("MessageSid", "")

        import json
        r = None
        session_key = f"whatsapp_session:{from_number}"
        session_data = None

        if message_sid:
            try:
                import redis
                r = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
                if not r.set(f"twilio_idempotency:{message_sid}", "1", nx=True, ex=86400):
                    logger.info("twilio_webhook_duplicate_ignored", message_sid=message_sid)
                    return Response(content="", media_type="application/xml")
            except Exception as e:
                logger.warning("twilio_idempotency_check_failed", error=str(e))
                r = None

        try:
            if not r:
                import redis
                r = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
            raw_session = r.get(session_key)
            if raw_session:
                session_data = json.loads(raw_session)
        except Exception as e:
            logger.warning("whatsapp_session_load_failed", error=str(e))

        logger.info(
            "whatsapp_message_received",
            from_number=from_number[-4:] if from_number else "unknown",
            message_length=len(incoming_msg),
        )
        
        lower_msg = incoming_msg.lower()

        if lower_msg == "cancel" and session_data:
            if r:
                r.delete(session_key)
            response_text = "Report filing cancelled. How else can I help you?"
        elif session_data:
            step = session_data.get("step")
            if step == "description":
                session_data["data"]["description"] = incoming_msg
                session_data["step"] = "phone"
                if r:
                    r.set(session_key, json.dumps(session_data), ex=3600)
                response_text = "2/3: Any phone numbers involved? (Reply 'none' if none, or type 'cancel' to abort)"
            elif step == "phone":
                session_data["data"]["phone_number"] = None if lower_msg == "none" else incoming_msg
                session_data["step"] = "location"
                if r:
                    r.set(session_key, json.dumps(session_data), ex=3600)
                response_text = "3/3: Your location? (Reply 'none' if none, or type 'cancel' to abort)"
            elif step == "location":
                session_data["data"]["location"] = None if lower_msg == "none" else incoming_msg
                
                # File the report
                try:
                    from services.citizen_service import get_citizen_service
                    citizen_svc = get_citizen_service()
                    report = await citizen_svc.create_report(
                        description=session_data["data"].get("description", ""),
                        phone_number=session_data["data"].get("phone_number"),
                        location=session_data["data"].get("location"),
                        source="whatsapp"
                    )
                    ref_num = report.get("reference_number", "UNKNOWN")
                    response_text = f"✅ Your report has been filed successfully.\n\nReference Number: *{ref_num}*\n\nPlease keep this safe. You can contact cybercrime at 1930 for immediate help."
                except Exception as e:
                    logger.error("whatsapp_report_creation_failed", error=str(e))
                    response_text = "Sorry, an error occurred while filing your report. Please try again later."
                
                if r:
                    r.delete(session_key)
            else:
                if r:
                    r.delete(session_key)
                response_text = "Session invalid. Please start again."
        elif not incoming_msg:
            # Empty message — send welcome
            response_text = (
                "🛡️ Welcome to ShieldAI Fraud Shield!\n\n"
                "Send me a description of any suspicious call, message, or activity "
                "and I'll analyze it for scam patterns.\n\n"
                "Type 'report' to file a fraud complaint.\n"
                "Type 'help' for more options."
            )
        elif lower_msg in ("help", "menu", "options"):
            response_text = (
                "🛡️ *ShieldAI Commands:*\n\n"
                "📝 *Describe a scam* — Just type what happened\n"
                "📋 *report* — File a fraud complaint\n"
                "📞 *check [phone number]* — Check if a number is reported\n"
                "ℹ️ *help* — Show this menu\n\n"
                "🚨 *Emergency?* Call 112 or cybercrime helpline 1930"
            )
        elif lower_msg.startswith("report"):
            # Start report flow
            if r:
                r.set(session_key, json.dumps({"step": "description", "data": {}}), ex=3600)
            response_text = (
                "📋 *Filing a Fraud Report*\n\n"
                "1/3: What happened? Please describe the incident in detail "
                "(or type 'cancel' to abort):"
            )
        elif incoming_msg.lower().startswith("check"):
            # Phone number risk check
            phone = incoming_msg[5:].strip()
            if phone:
                try:
                    from services.phone_risk_service import get_phone_risk_service
                    risk_svc = get_phone_risk_service()
                    risk = await risk_svc.assess_risk(phone)

                    emoji = "🔴" if risk["risk_label"] == "HIGH" else "🟡" if risk["risk_label"] == "MEDIUM" else "🟢"
                    masked_phone = phone[-4:].rjust(len(phone), '*') if len(phone) > 4 else phone
                    response_text = (
                        f"{emoji} *Phone Risk Check: {masked_phone}*\n\n"
                        f"Risk Level: {risk['risk_label']}\n"
                        f"Risk Score: {risk['risk_score']}\n"
                        f"Reports: {risk['report_count']}\n"
                        f"In Fraud Network: {'Yes ⚠️' if risk['in_network'] else 'No'}\n"
                    )
                    if risk["fraud_types"]:
                        response_text += f"Fraud Types: {', '.join(risk['fraud_types'])}"
                except Exception:
                    response_text = "Could not check that number. Please try again."
            else:
                response_text = "Usage: check [phone number]\nExample: check 9876543210"
        else:
            # Handle media
            num_media = int(form_data.get("NumMedia", "0"))
            if num_media > 0:
                media_url = form_data.get("MediaUrl0", "")
                media_type = form_data.get("MediaContentType0", "")
                
                try:
                    import httpx
                    auth = (settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                    async with httpx.AsyncClient() as client:
                        resp = await client.get(media_url, auth=auth)
                        resp.raise_for_status()
                        media_bytes = resp.content

                    if media_type.startswith("audio/"):
                        from services.gemini_service import get_gemini_service
                        gemini = get_gemini_service()
                        transcript = await gemini.transcribe_audio(media_bytes, mime_type=media_type)
                        
                        if transcript:
                            analysis = await gemini.analyze_scam_text(transcript)
                            risk_label = analysis.get("risk_label", "UNKNOWN")
                            explanation = analysis.get("explanation", "")
                            
                            response_text = (
                                f"🎤 *Audio Transcript:*\n_{transcript}_\n\n"
                                f"🛡️ *Scam Analysis:*\n"
                                f"Risk Level: {risk_label}\n"
                                f"Analysis: {explanation}"
                            )
                        else:
                            response_text = "Sorry, I couldn't understand the audio."

                    elif media_type.startswith("image/"):
                        from services.gemini_service import get_gemini_service
                        gemini = get_gemini_service()
                        analysis = await gemini.analyze_currency_image(media_bytes, mime_type=media_type)
                        verdict = analysis.get("verdict", "UNKNOWN")
                        analysis_text = analysis.get("analysis", "")
                        
                        emoji = "🔴" if verdict.upper() == "FAKE" else "🟢" if verdict.upper() == "GENUINE" else "🟡"
                        
                        response_text = (
                            f"{emoji} *Currency Analysis Verdict: {verdict.upper()}*\n\n"
                            f"{analysis_text}"
                        )
                    else:
                        response_text = "We currently cannot process this type of media. Please describe your issue in text."
                        
                except Exception as e:
                    logger.error("whatsapp_media_processing_failed", error=str(e))
                    response_text = "Sorry, we encountered an error processing your media."
            else:
                # Route through CitizenService chat to maintain context and rate limits
                try:
                    from services.citizen_service import get_citizen_service
                    citizen_svc = get_citizen_service()
                    
                    ip = request.client.host if request.client else "unknown"
                    result = await citizen_svc.chat(
                        message=incoming_msg,
                        session_id=f"wa_{from_number}",
                        language="en",
                        ip=ip
                    )
                    
                    response_text = result.get("response", "I'm sorry, I couldn't process that.")
                    
                    # Optionally append risk warning if HIGH
                    risk = result.get("risk_assessment")
                    if risk and risk.get("risk_level") == "HIGH":
                        response_text += "\n\n🚨 WARNING: High risk of scam detected! Do NOT send money. Call 1930."
                        
                except Exception as e:
                    logger.error("whatsapp_citizen_chat_failed", error=str(e))
                    response_text = (
                        "I couldn't process your message right now. "
                        "If you're in danger, call 112 or the cybercrime helpline at 1930 immediately."
                    )

        # Return TwiML response
        twiml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            f"<Message>{xml_escape(response_text)}</Message>"
            "</Response>"
        )

        return Response(content=twiml, media_type="application/xml")

    except HTTPException:
        raise
    except Exception as e:
        logger.error("whatsapp_webhook_error", error=str(e))
        twiml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            "<Message>An error occurred. Please try again or call 1930 for help.</Message>"
            "</Response>"
        )
        return Response(content=twiml, media_type="application/xml")
