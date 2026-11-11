"""
response_writer.py — Response Writer Agent for final answer formatting.

Takes the accumulated context and sources from previous agents,
and uses Gemini to produce a well-formatted markdown answer.
"""

import os
from dotenv import load_dotenv
load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
from agents.state import GraphState
from department_config import SECTIONS_DISPLAY, DEPARTMENT_CODE, DEPARTMENT_NAME

llm = ChatGoogleGenerativeAI(
    model=os.getenv("LLM_MODEL", "gemini-3.8-flash"),
    temperature=0.3,
    max_retries=3,
)

SYSTEM_PROMPT = """You are AIDA – AI-Driven Department Agent, an intelligent AI-powered assistant designed specifically for the Artificial Intelligence and Machine Learning (AIML) Department.
AIDA is an AI-powered department assistant that helps students, faculty, and administrators access department-specific academic and administrative information.
Answer questions based on the context provided below.

**Formatting Rules:**
- Use **Markdown** for all answers.
- Use `## Headers` for sections.
- Use `* bullet points` or `- bullet points` for lists.
- Use `**bold**` for key terms.
- For document-based answers, include citations with the document name and page number.
- For schedule/deadline answers, format the data clearly into tables or lists.
- For faculty inquiries, clearly present the faculty member's name, designation, department, institutional email, office/cabin location, specialization, subjects handled, and office hours/availability.
- For department events, workshops, seminars, and hackathons, clearly present the event title, scheduled date and time, venue/location, organizer, and description. Highlight venues, locations, and timings prominently.
- For study plans, organize by day with clear time blocks and priorities.
- Be concise but thorough.

**Important:**
- PREFER RETRIEVED DEPARTMENT INFORMATION: When answering questions about the AIML syllabus, academic policies, attendance rules, grading schemes, project guidelines, or lab manuals, base your answers strictly on the provided context.
- DO NOT INVENT DEPARTMENT INFORMATION: Never fabricate, assume, or guess university policies, passing thresholds, attendance percentages, or course requirements.
- IF INFORMATION IS UNAVAILABLE: If the context indicates that the requested information is not found in the uploaded documents, clearly state that the information is unavailable in the official department documentation rather than improvising.
- If the context indicates this is a general conversation query (e.g., greetings, thanks), respond politely and naturally without mentioning documents.
- If the context indicates a faculty member or information was not found in the department database, clearly let the student know rather than inventing information.
- If the context contains error messages, acknowledge the issue politely and let the student know you're having trouble fetching that data.
- Use the context to answer the question. If the context contains related or partially relevant information, use it to construct the best possible answer. Combine information from multiple context chunks if needed.
- HUMAN APPROVAL REQUIREMENT FOR STUDENT REQUESTS: You may explain how to submit requests, explain department requirements, or assist students in drafting clear request descriptions (e.g. for leave, bonafide certificates, project guide allocation, lab compute access, or course exemptions). However, you MUST NEVER approve, reject, or grant requests yourself. You must clearly state that all formal approvals or rejections are strictly made by authorized human faculty members or department administrators through the department portal.
- Never make up factual university information that isn't supported by the context.

Context:
{context}
"""


async def response_writer_node(state: GraphState) -> dict:
    """
    Generate the final markdown response using Gemini.

    Reads the 'context' and 'query' from state, calls Gemini,
    and writes the result to 'response'.

    Special case: if any context item has tool='clarification_needed',
    we return the clarification question directly without calling the LLM.

    Returns:
        Updated state with 'response' set to the LLM-generated answer.
    """
    query = state["query"]
    context_items = state.get("context", [])

    # --- CLARIFICATION FAST-PATH ---
    # If the timetable agent set a clarification_needed block, bypass the LLM
    # and return a crisp question immediately. This prevents the LLM from
    # hallucinating "I don't have that information" instead of asking.
    for item in context_items:
        if isinstance(item, dict) and item.get("tool") == "clarification_needed":
            return {"response": f"Which section are you in — {SECTIONS_DISPLAY}? Please let me know and I'll pull up your timetable right away!"}

    # Build context string from all gathered data
    context_parts = []
    for item in context_items:
        if isinstance(item, dict):
            tool = item.get("tool", "unknown")
            content = item.get("content", "")
            source = item.get("source", "")
            page = item.get("page", "")

            if source and page:
                context_parts.append(f"[{tool}: {source}, Page {page}]\n{content}")
            else:
                context_parts.append(f"[{tool}]\n{content}")
        else:
            context_parts.append(str(item))

    # Handle empty context (general queries)
    if not context_parts:
        context_str = "No specific context retrieved. This appears to be a general conversation query."
    else:
        context_str = "\n\n---\n\n".join(context_parts)

    # Build messages
    messages: list[BaseMessage] = [
        SystemMessage(content=SYSTEM_PROMPT.format(context=context_str)),
    ]

    history = state.get("history", [])
    for msg in history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))

    messages.append(HumanMessage(content=query))

    print(f"[Response Writer] Generating response ({len(context_parts)} context items)")

    response = await llm.ainvoke(messages)
    
    response_content = response.content
    if isinstance(response_content, list):
        response_content = " ".join([b.get("text", "") if isinstance(b, dict) else b for b in response_content])
    elif not isinstance(response_content, str):
        response_content = str(response_content)  # type: ignore

    print(f"[Response Writer] Response generated ({len(response_content)} chars)")

    return {"response": response_content}
