"""Gayatri AI — 22 Prompt-Engineered Agents (Ready for Deployment).

These agents are fully designed with system prompts, triggers, and descriptions.
They operate using only the local LLM — no external system integration required.
"""

from __future__ import annotations

import logging

from core.agents.registry import AgentResponse, ModelUnavailableError, agent_registry

logger = logging.getLogger("gayatri.agents.prompts")


def _local_chat(messages: list[dict], max_tokens: int = 300) -> str:
    """Call the local model with full message list. Raises ModelUnavailableError on failure."""
    try:
        from core.providers.local import LocalProvider
        return LocalProvider.chat(messages, max_tokens=max_tokens)
    except Exception as exc:
        logger.warning(f"Local model unavailable: {exc}")
        raise ModelUnavailableError(f"Local model unavailable: {exc}") from exc

def _local_chat_stream(messages: list[dict], max_tokens: int = 300):
    """Stream response from the local model."""
    try:
        from core.providers.local import LocalProvider
        return LocalProvider.chat_stream(messages, max_tokens=max_tokens)
    except Exception as exc:
        logger.warning(f"Local model unavailable: {exc}")
        raise ModelUnavailableError(f"Local model unavailable: {exc}") from exc


def _build_messages(system: str, user_message: str,
                    history: list[dict] | None = None) -> list[dict]:
    """Build a message list with system prompt, optional history, and current user message."""
    messages = [{"role": "system", "content": system}]
    if history:
        for msg in history:
            if msg.get("role") in ("user", "assistant"):
                messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})
    return messages


def register_prompt_agents() -> None:
    """Idempotently register all 22 prompt-engineered agents."""
    if agent_registry.get("Orchestrator Agent") is not None:
        return

    # ── Foundational Agents (9) ─────────────────────────────────────────

    @agent_registry.register(
        name="Orchestrator Agent",
        commands=["/orchestrate", "/plan"],
        triggers=["orchestrate", "break down", "coordinate", "multi-step"],
        description="Central routing, task decomposition, multi-agent coordination",
    )
    class OrchestratorAgent:
        def process(self, context) -> AgentResponse:
            system = (
                "You are the Orchestrator Agent. Your role is to break down complex "
                "requests into structured subtasks and coordinate execution. Analyze the "
                "user's request, identify the key steps needed, and provide a clear "
                "execution plan. If the request requires a specific specialist agent, "
                "note which one and why."
            )
            msgs = _build_messages(system, context.user_message,
                                   getattr(context, 'history', None))
            stream = _local_chat_stream(msgs, max_tokens=400)
            return AgentResponse(text='', text_stream=stream, agent_name="Orchestrator Agent")

    @agent_registry.register(
        name="Research Agent",
        commands=["/research", "/search"],
        triggers=["research", "find information", "look up", "search for", "investigate"],
        description="Web search, source synthesis, cited findings",
    )
    class ResearchAgent:
        def process(self, context) -> AgentResponse:
            system = (
                "You are a Research Agent. Your role is to help users find and "
                "synthesize information. When asked a question, provide a well-structured "
                "answer with key findings. If you don't have real-time search access, "
                "work with the information available in the conversation and provide "
                "a reasoned response. Be thorough, cite sources when possible, and "
                "distinguish between facts and opinions."
            )
            msgs = _build_messages(system, context.user_message,
                                   getattr(context, 'history', None))
            stream = _local_chat_stream(msgs, max_tokens=500)
            return AgentResponse(text='', text_stream=stream, agent_name="Research Agent")

    @agent_registry.register(
        name="Document Agent",
        commands=["/doc", "/document"],
        triggers=["read this", "summarize this document", "paraphrase", "rewrite this"],
        description="Read, paraphrase, rewrite, summarize documents",
    )
    class DocumentAgent:
        def process(self, context) -> AgentResponse:
            system = (
                "You are a Document Agent. Your role is to help users work with "
                "documents — reading, summarizing, paraphrasing, and rewriting. "
                "When given text, provide clear, well-structured outputs. Maintain "
                "the original meaning while improving clarity and readability."
            )
            msgs = _build_messages(system, context.user_message,
                                   getattr(context, 'history', None))
            stream = _local_chat_stream(msgs, max_tokens=500)
            return AgentResponse(text='', text_stream=stream, agent_name="Document Agent")

    @agent_registry.register(
        name="Summarization Agent",
        commands=["/summarize", "/summary"],
        triggers=["summarize", "key points", "tl;dr", "condense", "brief overview"],
        description="Long-form multi-document summarization",
    )
    class SummarizationAgent:
        def process(self, context) -> AgentResponse:
            system = (
                "You are a Summarization Agent. Your role is to create concise, "
                "accurate summaries of long-form content. Extract key points, "
                "maintain logical flow, and present the summary in a structured "
                "format. Adapt length based on user preference."
            )
            msgs = _build_messages(system, context.user_message,
                                   getattr(context, 'history', None))
            stream = _local_chat_stream(msgs, max_tokens=500)
            return AgentResponse(text='', text_stream=stream, agent_name="Summarization Agent")

    @agent_registry.register(
        name="Translation Agent",
        commands=["/translate", "/trans"],
        triggers=["translate", "convert to hindi", "convert to english", "hindi mein"],
        description="Indian languages ↔ English translation and localization",
    )
    class TranslationAgent:
        def process(self, context) -> AgentResponse:
            system = (
                "You are a Translation and Localization Agent. Your role is to "
                "translate text between English and Indian languages (Hindi, Tamil, "
                "Telugu, Bengali, Marathi, Gujarati, Kannada, Malayalam, Punjabi, "
                "Odia, Assamese, Urdu). Preserve meaning, tone, and context. "
                "Handle code-switching naturally. When translating technical content, "
                "keep technical terms in English with translations in parentheses."
            )
            msgs = _build_messages(system, context.user_message,
                                   getattr(context, 'history', None))
            stream = _local_chat_stream(msgs, max_tokens=500)
            return AgentResponse(text='', text_stream=stream, agent_name="Translation Agent")

    @agent_registry.register(
        name="Voice Assistant Agent",
        commands=["/voice"],
        triggers=["voice command", "speak", "listen"],
        description="Voice-first command and response interface",
    )
    class VoiceAgent:
        def process(self, context) -> AgentResponse:
            system = (
                "You are a Voice Assistant Agent. Respond to voice commands concisely "
                "and clearly. Use short sentences. Avoid formatting that doesn't work "
                "well with speech synthesis. Confirm actions when appropriate."
            )
            msgs = _build_messages(system, context.user_message,
                                   getattr(context, 'history', None))
            stream = _local_chat_stream(msgs, max_tokens=200)
            return AgentResponse(text='', text_stream=stream, agent_name="Voice Assistant Agent")

    @agent_registry.register(
        name="Data Extraction Agent",
        commands=["/extract", "/data"],
        triggers=["extract data", "pull information", "get fields", "parse this"],
        description="Extract structured data from documents, PDFs, images",
    )
    class DataExtractionAgent:
        def process(self, context) -> AgentResponse:
            system = (
                "You are a Data Extraction Agent. Your role is to extract structured "
                "data from unstructured text, documents, and images. Present extracted "
                "data in clear structured formats (tables, JSON, lists). Identify "
                "field names, values, and relationships. Flag any ambiguous or "
                "missing data."
            )
            msgs = _build_messages(system, context.user_message,
                                   getattr(context, 'history', None))
            stream = _local_chat_stream(msgs, max_tokens=500)
            return AgentResponse(text='', text_stream=stream, agent_name="Data Extraction Agent")

    @agent_registry.register(
        name="Meeting Transcription Agent",
        commands=["/transcribe"],
        triggers=["transcribe", "meeting notes", "summarize meeting", "who said what"],
        description="Transcribe, identify speakers, summarize meetings",
    )
    class TranscriptionAgent:
        def process(self, context) -> AgentResponse:
            system = (
                "You are a Meeting Transcription Agent. Your role is to process "
                "meeting transcripts — identify speakers, extract action items, "
                "and provide structured summaries. Format output with clear "
                "sections: attendees, key points, decisions made, and action items "
                "with owners."
            )
            msgs = _build_messages(system, context.user_message,
                                   getattr(context, 'history', None))
            stream = _local_chat_stream(msgs, max_tokens=500)
            return AgentResponse(text='', text_stream=stream, agent_name="Meeting Transcription Agent")

    @agent_registry.register(
        name="Personal Assistant Agent",
        commands=["/assistant", "/pa"],
        triggers=["manage schedule", "daily schedule", "remind me", "my tasks", "plan my day"],
        description="Schedule management, reminders, task coordination",
    )
    class PersonalAssistantAgent:
        def process(self, context) -> AgentResponse:
            system = (
                "You are a Personal Assistant Agent. Help users manage their "
                "schedule, set reminders, and coordinate tasks. Be organized, "
                "proactive, and concise. When setting reminders, confirm the "
                "details. When planning, provide structured timelines."
            )
            msgs = _build_messages(system, context.user_message,
                                   getattr(context, 'history', None))
            stream = _local_chat_stream(msgs, max_tokens=300)
            return AgentResponse(text='', text_stream=stream, agent_name="Personal Assistant Agent")

    # ── Business & Operations Agents (13) ────────────────────────────────

    @agent_registry.register(
        name="HR & Talent Agent",
        commands=["/hr", "/talent"],
        triggers=["resume", "job description", "onboarding", "candidate", "hiring"],
        description="Resume screening, job descriptions, onboarding, policy queries",
    )
    class HRAgent:
        def process(self, context) -> AgentResponse:
            system = (
                "You are an HR and Talent Agent. Your role is to help with resume "
                "screening, job descriptions, onboarding processes, and HR policy "
                "queries. Be professional, objective, and compliant with standard "
                "HR practices. When screening resumes, focus on relevant qualifications "
                "and experience."
            )
            msgs = _build_messages(system, context.user_message,
                                   getattr(context, 'history', None))
            stream = _local_chat_stream(msgs, max_tokens=500)
            return AgentResponse(text='', text_stream=stream, agent_name="HR & Talent Agent")

    @agent_registry.register(
        name="Financial Agent",
        commands=["/finance", "/financial"],
        triggers=["financial analysis", "budget", "revenue", "expenses", "profit loss"],
        description="Financial analysis, reporting, anomaly detection",
    )
    class FinancialAgent:
        def process(self, context) -> AgentResponse:
            system = (
                "You are a Financial Analysis Agent. Your role is to help with "
                "financial analysis, reporting, and forecasting. Analyze data, "
                "identify trends and anomalies, and present findings clearly. "
                "Be precise with numbers and always note assumptions."
            )
            msgs = _build_messages(system, context.user_message,
                                   getattr(context, 'history', None))
            stream = _local_chat_stream(msgs, max_tokens=500)
            return AgentResponse(text='', text_stream=stream, agent_name="Financial Agent")

    @agent_registry.register(
        name="Project Management Agent",
        commands=["/pm", "/project"],
        triggers=["project plan", "timeline", "milestones", "resource allocation"],
        description="Planning, timelines, resource allocation, milestone tracking",
    )
    class PMAgent:
        def process(self, context) -> AgentResponse:
            system = (
                "You are a Project Management Agent. Your role is to help plan "
                "projects, create timelines, allocate resources, and track milestones. "
                "Be structured and practical. Break down projects into phases with "
                "clear deliverables and dependencies."
            )
            msgs = _build_messages(system, context.user_message,
                                   getattr(context, 'history', None))
            stream = _local_chat_stream(msgs, max_tokens=500)
            return AgentResponse(text='', text_stream=stream, agent_name="Project Management Agent")

    @agent_registry.register(
        name="Email Agent",
        commands=["/email", "/mail"],
        triggers=["draft email", "write email", "reply to", "email response"],
        description="Draft responses, triage messages, extract action items",
    )
    class EmailAgent:
        def process(self, context) -> AgentResponse:
            system = (
                "You are an Email and Communications Agent. Your role is to help "
                "draft professional emails, triage messages, and extract action items. "
                "Match the tone to the context. Be concise. For action items, list "
                "them clearly with owners and deadlines."
            )
            msgs = _build_messages(system, context.user_message,
                                   getattr(context, 'history', None))
            stream = _local_chat_stream(msgs, max_tokens=400)
            return AgentResponse(text='', text_stream=stream, agent_name="Email Agent")

    @agent_registry.register(
        name="Creative Agent",
        commands=["/creative", "/design"],
        triggers=["creative design", "creative writing", "marketing content", "visual concept"],
        description="Design concepts, marketing content, creative drafts",
    )
    class CreativeAgent:
        def process(self, context) -> AgentResponse:
            system = (
                "You are a Creative and Design Agent. Your role is to help with "
                "creative content, design concepts, and marketing materials. "
                "Generate ideas, draft copy, and suggest visual approaches. "
                "Be innovative while staying practical."
            )
            msgs = _build_messages(system, context.user_message,
                                   getattr(context, 'history', None))
            stream = _local_chat_stream(msgs, max_tokens=500)
            return AgentResponse(text='', text_stream=stream, agent_name="Creative Agent")

    @agent_registry.register(
        name="Social Media Agent",
        commands=["/social"],
        triggers=["social media", "brand mention", "sentiment", "competitor"],
        description="Brand mentions, sentiment tracking, competitor monitoring",
    )
    class SocialMediaAgent:
        def process(self, context) -> AgentResponse:
            system = (
                "You are a Social Media and Brand Monitoring Agent. Your role is "
                "to track brand mentions, analyze sentiment, and monitor competitors. "
                "Provide structured reports with sentiment scores, key themes, and "
                "actionable insights."
            )
            msgs = _build_messages(system, context.user_message,
                                   getattr(context, 'history', None))
            stream = _local_chat_stream(msgs, max_tokens=500)
            return AgentResponse(text='', text_stream=stream, agent_name="Social Media Agent")

    @agent_registry.register(
        name="Sales Agent",
        commands=["/sales"],
        triggers=["lead qualification", "sales outreach", "crm update", "sales pipeline"],
        description="Lead qualification, outreach drafting, CRM updates",
    )
    class SalesAgent:
        def process(self, context) -> AgentResponse:
            system = (
                "You are a Sales and CRM Agent. Your role is to help with lead "
                "qualification, outreach drafting, and CRM management. Qualify leads "
                "based on BANT criteria. Draft personalized outreach messages. "
                "Update CRM records with relevant information."
            )
            msgs = _build_messages(system, context.user_message,
                                   getattr(context, 'history', None))
            stream = _local_chat_stream(msgs, max_tokens=500)
            return AgentResponse(text='', text_stream=stream, agent_name="Sales Agent")

    @agent_registry.register(
        name="Legal Review Agent",
        commands=["/legal"],
        triggers=["contract review", "legal document", "risk assessment", "redline"],
        description="Contract review, risk flagging, redline drafting",
    )
    class LegalAgent:
        def process(self, context) -> AgentResponse:
            system = (
                "You are a Legal Contract Review Agent. Your role is to review "
                "contracts against a playbook, flag risks, and draft redlines. "
                "Be precise about risk levels (high/medium/low). Reference specific "
                "clauses. Provide clear, actionable redline suggestions."
            )
            msgs = _build_messages(system, context.user_message,
                                   getattr(context, 'history', None))
            stream = _local_chat_stream(msgs, max_tokens=500)
            return AgentResponse(text='', text_stream=stream, agent_name="Legal Review Agent")

    @agent_registry.register(
        name="Procurement Agent",
        commands=["/procure"],
        triggers=["vendor", "procurement", "rfp", "supplier", "contract renewal"],
        description="Vendor comparison, RFP drafting, contract renewal tracking",
    )
    class ProcurementAgent:
        def process(self, context) -> AgentResponse:
            system = (
                "You are a Procurement and Vendor Management Agent. Your role is "
                "to help compare vendors, draft RFPs, and track contract renewals. "
                "Create structured comparison matrices. Draft clear RFP documents. "
                "Track renewal timelines and flag upcoming deadlines."
            )
            msgs = _build_messages(system, context.user_message,
                                   getattr(context, 'history', None))
            stream = _local_chat_stream(msgs, max_tokens=500)
            return AgentResponse(text='', text_stream=stream, agent_name="Procurement Agent")

    @agent_registry.register(
        name="Meeting Scheduler Agent",
        commands=["/schedule"],
        triggers=["schedule meeting", "book meeting", "find time", "calendar"],
        description="Coordinate availability, book meetings",
    )
    class SchedulerAgent:
        def process(self, context) -> AgentResponse:
            system = (
                "You are a Meeting Scheduler Agent. Your role is to coordinate "
                "availability and book meetings. When given participants and "
                "preferences, propose optimal meeting times. Handle timezone "
                "differences. Confirm all details before finalizing."
            )
            msgs = _build_messages(system, context.user_message,
                                   getattr(context, 'history', None))
            stream = _local_chat_stream(msgs, max_tokens=300)
            return AgentResponse(text='', text_stream=stream, agent_name="Meeting Scheduler Agent")

    @agent_registry.register(
        name="Customer Support Agent",
        commands=["/support"],
        triggers=["customer issue", "support ticket", "help desk", "kb"],
        description="First-line queries, KB responses, ticket escalation",
    )
    class SupportAgent:
        def process(self, context) -> AgentResponse:
            system = (
                "You are a Customer Support Agent. Your role is to handle first-line "
                "queries, provide KB-based responses, and escalate when needed. "
                "Be empathetic, solution-oriented, and concise. Escalate complex "
                "issues with clear context."
            )
            msgs = _build_messages(system, context.user_message,
                                   getattr(context, 'history', None))
            stream = _local_chat_stream(msgs, max_tokens=400)
            return AgentResponse(text='', text_stream=stream, agent_name="Customer Support Agent")

    @agent_registry.register(
        name="News Analyst Agent",
        commands=["/news"],
        triggers=["latest news", "news update", "industry trends", "market news"],
        description="Industry news, trend identification, sector digests",
    )
    class NewsAgent:
        def process(self, context) -> AgentResponse:
            system = (
                "You are a News and Trend Analysis Agent. Your role is to track "
                "industry news, identify trends, and provide sector digests. "
                "Structure outputs with: top stories, trend analysis, impact "
                "assessment, and recommended actions."
            )
            msgs = _build_messages(system, context.user_message,
                                   getattr(context, 'history', None))
            stream = _local_chat_stream(msgs, max_tokens=500)
            return AgentResponse(text='', text_stream=stream, agent_name="News Analyst Agent")

    @agent_registry.register(
        name="Presentation Agent",
        commands=["/slides", "/presentation"],
        triggers=["create slides", "presentation", "deck", "ppt"],
        description="Slide generation, structuring, visual content suggestions",
    )
    class PresentationAgent:
        def process(self, context) -> AgentResponse:
            system = (
                "You are a Presentation Agent. Your role is to help create and "
                "structure presentations. When given a topic, outline a slide deck "
                "with clear sections, bullet points, and speaker notes. Suggest "
                "visual elements where relevant. Follow standard presentation structure: "
                "title, agenda, content sections, summary, Q&A."
            )
            msgs = _build_messages(system, context.user_message,
                                   getattr(context, 'history', None))
            stream = _local_chat_stream(msgs, max_tokens=500)
            return AgentResponse(text='', text_stream=stream, agent_name="Presentation Agent")

    # ── Sector Specialist Agents (8) ────────────────────────────────────

    @agent_registry.register(
        name="Assignment Grader",
        commands=["/grade"],
        triggers=["grade this", "check assignment", "mark this", "rubric"],
        description="Rubric-based grading with personalized feedback",
    )
    class GraderAgent:
        def process(self, context) -> AgentResponse:
            system = (
                "You are an Assignment Grader. Your role is to evaluate student "
                "submissions against rubrics. Provide scores with specific feedback. "
                "Highlight strengths and areas for improvement. Be constructive."
            )
            msgs = _build_messages(system, context.user_message,
                                   getattr(context, 'history', None))
            stream = _local_chat_stream(msgs, max_tokens=500)
            return AgentResponse(text='', text_stream=stream, agent_name="Assignment Grader")

    @agent_registry.register(
        name="Policy Analyst Agent",
        commands=["/policy"],
        triggers=["government scheme", "policy analysis", "policy budget", "government program"],
        description="Government schemes, budgets, policy synthesis",
    )
    class PolicyAgent:
        def process(self, context) -> AgentResponse:
            system = (
                "You are a Government Policy and Scheme Analyst. Your role is to "
                "help users understand government schemes, budgets, and policies. "
                "Provide clear explanations of eligibility, benefits, and application "
                "processes. Synthesize complex policy information into accessible summaries."
            )
            msgs = _build_messages(system, context.user_message,
                                   getattr(context, 'history', None))
            stream = _local_chat_stream(msgs, max_tokens=500)
            return AgentResponse(text='', text_stream=stream, agent_name="Policy Analyst Agent")

    @agent_registry.register(
        name="Clinical Analysis Agent",
        commands=["/clinical"],
        triggers=["clinical", "patient data", "medical literature", "trial"],
        description="Anonymized patient data analysis, trial matching, literature review",
    )
    class ClinicalAgent:
        def process(self, context) -> AgentResponse:
            system = (
                "You are a Clinical Analysis Agent. Your role is to help analyze "
                "anonymized patient data, match clinical trials, and review medical "
                "literature. Always emphasize anonymization. Provide evidence-based "
                "analysis. Note limitations of available data."
            )
            msgs = _build_messages(system, context.user_message,
                                   getattr(context, 'history', None))
            stream = _local_chat_stream(msgs, max_tokens=500)
            return AgentResponse(text='', text_stream=stream, agent_name="Clinical Analysis Agent")

    @agent_registry.register(
        name="Property Valuation Agent",
        commands=["/property"],
        triggers=["property value", "real estate", "house price", "valuation"],
        description="Property listings and valuation from comparable data",
    )
    class PropertyAgent:
        def process(self, context) -> AgentResponse:
            system = (
                "You are a Property Valuation Agent. Your role is to help with "
                "property listings and valuations based on comparable market data. "
                "Provide structured valuations with price ranges, comparable "
                "properties, and market trends."
            )
            msgs = _build_messages(system, context.user_message,
                                   getattr(context, 'history', None))
            stream = _local_chat_stream(msgs, max_tokens=500)
            return AgentResponse(text='', text_stream=stream, agent_name="Property Valuation Agent")

    @agent_registry.register(
        name="Loan Underwriting Agent",
        commands=["/loan"],
        triggers=["loan application", "underwriting", "credit assessment", "eligibility"],
        description="Financial analysis and eligibility for loan applications",
    )
    class LoanAgent:
        def process(self, context) -> AgentResponse:
            system = (
                "You are a Loan Underwriting Agent. Your role is to analyze loan "
                "applications, assess financial eligibility, and evaluate risk. "
                "Provide structured assessments with risk ratings. Consider income, "
                "credit history, and collateral."
            )
            msgs = _build_messages(system, context.user_message,
                                   getattr(context, 'history', None))
            stream = _local_chat_stream(msgs, max_tokens=500)
            return AgentResponse(text='', text_stream=stream, agent_name="Loan Underwriting Agent")

    @agent_registry.register(
        name="Crop Advisory Agent",
        commands=["/crop"],
        triggers=["crop advisory", "farming advice", "soil health", "crop weather", "crop yield"],
        description="Crop, soil, weather-informed advisory with yield estimation",
    )
    class CropAgent:
        def process(self, context) -> AgentResponse:
            system = (
                "You are a Crop Advisory Agent. Your role is to provide farming "
                "advice based on crop type, soil conditions, and weather data. "
                "Suggest appropriate crops, fertilizer schedules, and irrigation "
                "plans. Estimate expected yields. Consider regional conditions."
            )
            msgs = _build_messages(system, context.user_message,
                                   getattr(context, 'history', None))
            stream = _local_chat_stream(msgs, max_tokens=500)
            return AgentResponse(text='', text_stream=stream, agent_name="Crop Advisory Agent")

    @agent_registry.register(
        name="Demand Forecasting Agent",
        commands=["/forecast"],
        triggers=["demand forecast", "sales prediction", "inventory", "seasonal"],
        description="Product demand prediction from sales and seasonal patterns",
    )
    class ForecastAgent:
        def process(self, context) -> AgentResponse:
            system = (
                "You are a Demand Forecasting Agent. Your role is to predict "
                "product demand based on sales history, seasonal patterns, and "
                "market trends. Provide forecasts with confidence intervals. "
                "Recommend inventory adjustments."
            )
            msgs = _build_messages(system, context.user_message,
                                   getattr(context, 'history', None))
            stream = _local_chat_stream(msgs, max_tokens=500)
            return AgentResponse(text='', text_stream=stream, agent_name="Demand Forecasting Agent")

    logger.info(f"Registered {len(agent_registry._agents)} prompt-engineered agents")
