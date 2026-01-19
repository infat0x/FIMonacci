"""
AI Analysis Engine
Uses AI services (Mistral/Grok) to analyze file integrity alerts
"""

import os
import json
from datetime import datetime, timezone
from typing import Dict, Optional
from flask import current_app

from . import db
from .database import FileIntegrity


class AIAnalysisEngine:
    """AI-powered analysis of file integrity alerts"""
    
    def __init__(self):
        self.provider = os.environ.get('AI_PROVIDER', 'mistral').lower()  # 'mistral' | 'grok'
        self.enabled = os.environ.get('AI_ANALYSIS_ENABLED', 'false').lower() == 'true'

        # Mistral configuration
        self.mistral_api_key = os.environ.get("MISTRAL_API_KEY", "")
        self.mistral_model = os.environ.get("MISTRAL_MODEL", "mistral-small-latest")

        # Grok configuration (if available)
        self.grok_api_key = os.environ.get('GROK_API_KEY', '')
        self.grok_api_url = os.environ.get('GROK_API_URL', '')
    
    def analyze_alert(self, alert: FileIntegrity) -> Optional[Dict]:
        """
        Analyze a file integrity alert using AI
        
        Returns:
            Dictionary with 'analysis', 'risk_score', and 'recommendations'
        """
        if not self.enabled:
            return None
        
        try:
            # Prepare context for AI analysis
            context = self._prepare_context(alert)
            
            if self.provider == 'mistral' and self.mistral_api_key:
                return self._analyze_with_mistral(context, alert)
            elif self.provider == 'grok' and self.grok_api_key:
                return self._analyze_with_grok(context, alert)
            else:
                current_app.logger.warning("AI provider not configured")
                return None
                
        except Exception as e:
            current_app.logger.error(f"AI analysis failed: {e}")
            return None
    
    def _prepare_context(self, alert: FileIntegrity) -> str:
        """Prepare context string for AI analysis"""
        context = f"""
File Integrity Alert Analysis Request:

Alert Type: {alert.alert_type}
File Path: {alert.path}
Timestamp: {alert.timestamp.isoformat()}
Initial Hash: {alert.initial_hash}
Current Hash: {alert.current_hash or 'N/A'}

File Metadata:
- Owner User: {alert.owner_user or 'Unknown'}
- Owner Group: {alert.owner_group or 'Unknown'}
- Process Name: {alert.process_name or 'Unknown'}
- Process ID: {alert.process_id or 'Unknown'}
- Process User: {alert.process_user or 'Unknown'}
- Detected File Type: {alert.detected_file_type or 'Unknown'}
- File Extension: {alert.file_extension or 'Unknown'}
- Magic Byte Mismatch: {alert.magic_byte_mismatch}

Client Information:
- Hostname: {alert.client.hostname if alert.client else 'Unknown'}
- Client ID: {alert.client.client_id if alert.client else 'Unknown'}

Please analyze this file integrity alert and provide:
1. Risk assessment (0-100 score)
2. Potential security implications
3. Recommended actions
4. Whether this appears to be malicious activity
"""
        return context
    
    def _analyze_with_mistral(self, context: str, alert: FileIntegrity) -> Optional[Dict]:
        """Analyze using Mistral Chat Completions (JSON mode)"""
        try:
            from mistralai import Mistral

            prompt = f"""
You are a cybersecurity analyst. Analyze the following file integrity monitoring alert:

{context}

Return VALID JSON ONLY with the following structure:
{{
    "risk_score": <decimal 0.0-1.0>,
    "analysis": "<detailed analysis>",
    "recommendations": ["<action1>", "<action2>", ...],
    "is_malicious": <true/false>,
    "confidence": <number 0-100>
}}

IMPORTANT: risk_score must be a decimal between 0.0 and 1.0 where:
- 0.8-1.0 = Critical severity
- 0.6-0.8 = High severity
- 0.4-0.6 = Medium severity
- 0.0-0.4 = Low severity
"""

            client = Mistral(api_key=self.mistral_api_key)
            resp = client.chat.complete(
                model=self.mistral_model,
                messages=[
                    {"role": "system", "content": "You are a senior SOC analyst. Output JSON only."},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
            )

            content = resp.choices[0].message.content if resp and resp.choices else ""
            analysis_data = json.loads(content or "{}")

            if analysis_data:
                alert.ai_analysis = analysis_data.get('analysis', '')
                # Ensure risk_score is between 0.0 and 1.0
                risk_score = float(analysis_data.get('risk_score', 0.5))
                # Convert if sent as 0-100 scale by mistake
                if risk_score > 1.0:
                    risk_score = risk_score / 100.0
                alert.ai_risk_score = risk_score
                alert.ai_analysis_timestamp = datetime.now(timezone.utc)
                db.session.commit()
                return analysis_data
        except Exception as e:
            current_app.logger.error(f"Mistral analysis failed: {e}")

        return None
    
    def _analyze_with_grok(self, context: str, alert: FileIntegrity) -> Optional[Dict]:
        """Analyze using Grok API (placeholder - implement when API available)"""
        # Grok API implementation would go here
        current_app.logger.info("Grok analysis not yet implemented")
        return None
    
    def _extract_json_from_response(self, text: str) -> Optional[Dict]:
        """Extract JSON from AI response text"""
        try:
            # Try to find JSON block in response
            import re
            json_match = re.search(r'\{[^{}]*"risk_score"[^{}]*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            
            # Try parsing entire response as JSON
            return json.loads(text)
        except:
            # If JSON extraction fails, create a basic analysis
            return {
                "risk_score": 0.5,
                "analysis": text[:500] if text else "Analysis completed",
                "recommendations": ["Review file changes", "Check process legitimacy"],
                "is_malicious": False,
                "confidence": 50
            }
    
    def batch_analyze_alerts(self, alerts: list, limit: int = 10) -> int:
        """
        Analyze multiple alerts (with rate limiting)
        
        Args:
            alerts: List of FileIntegrity objects
            limit: Maximum number of alerts to analyze
            
        Returns:
            Number of alerts analyzed
        """
        analyzed = 0
        for alert in alerts[:limit]:
            if not alert.ai_analysis:  # Skip if already analyzed
                result = self.analyze_alert(alert)
                if result:
                    analyzed += 1
        return analyzed


# Global instance
ai_analysis_engine = AIAnalysisEngine()

