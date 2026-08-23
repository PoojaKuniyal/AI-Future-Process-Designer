import os
import re
import json
import asyncio
import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sentence_transformers import SentenceTransformer

from backend.app.config import settings
from backend.app.database import SessionLocal
from backend.app import models
from backend.app.agents.state import AgentState
from backend.app.search import get_search_provider

logger = logging.getLogger(__name__)

# Global model container for embeddings
embedding_model = None

def get_embedding(text: str) -> List[float]:
    global embedding_model
    if embedding_model is None:
        logger.info(f"Loading sentence-transformers model: {settings.EMBEDDING_MODEL_NAME}")
        embedding_model = SentenceTransformer(
            settings.EMBEDDING_MODEL_NAME, 
            device=settings.EMBEDDING_DEVICE
        )
    emb = embedding_model.encode(text)
def to_str(val: Any) -> str:
    """
    Safely converts strings, lists, dicts, or other types into clean, readable text
    to prevent psycopg2 'can't adapt type' database insertion errors.
    """
    if val is None:
        return ""
    if isinstance(val, str):
        return val
    if isinstance(val, (list, tuple)):
        return "\n".join(f"- {to_str(item)}" for item in val)
    if isinstance(val, dict):
        lines = []
        for k, v in val.items():
            if isinstance(v, (list, tuple)):
                lines.append(f"{k}:")
                lines.extend(f"  - {to_str(item)}" for item in v)
            elif isinstance(v, dict):
                lines.append(f"{k}: {json.dumps(v)}")
            else:
                lines.append(f"{k}: {v}")
        return "\n".join(lines)
    return str(val)


def repair_json(json_str: str) -> Any:
    """
    Attempts to parse and repair truncated or unclosed JSON by balancing braces,
    closing open quotes, and stripping incomplete trailing keys/elements.
    """
    s = json_str.strip()
    if not s:
        raise ValueError("Empty string for JSON repair")
        
    start_brace = min([pos for pos in [s.find('{'), s.find('[')] if pos != -1] or [-1])
    if start_brace == -1:
        raise ValueError("No start brace found")
    s = s[start_brace:]

    # Remove trailing commas
    s = re.sub(r',\s*$', '', s)
    s = re.sub(r',\s*([\]}])', r'\1', s)

    # Try direct load
    try:
        return json.loads(s)
    except Exception:
        pass

    # Iteratively close open quotes and unbalanced brackets
    curr = s
    for _ in range(6):
        # Count open unescaped quotes
        unescaped_quotes = len(re.findall(r'(?<!\\)"', curr))
        if unescaped_quotes % 2 != 0:
            curr += '"'
            
        # Clean trailing colons or broken keys
        curr_clean = re.sub(r':\s*"[^"]*$', ':"N/A"', curr)
        curr_clean = re.sub(r',\s*("[^"]*")?\s*$', '', curr_clean)

        open_curlies = curr_clean.count('{') - curr_clean.count('}')
        open_squares = curr_clean.count('[') - curr_clean.count(']')

        candidate = curr_clean + (']' * max(0, open_squares)) + ('}' * max(0, open_curlies))
        candidate = re.sub(r',\s*([\]}])', r'\1', candidate)
        try:
            return json.loads(candidate)
        except Exception:
            # Trim back to the last complete delimiter
            last_delim = max(curr.rfind('}'), curr.rfind(']'))
            if last_delim > 0 and last_delim != len(curr) - 1:
                curr = curr[:last_delim+1]
            else:
                break
                
    raise ValueError("Could not repair truncated JSON")


def extract_json_block(text: str) -> Any:
    """
    Extracts and parses JSON from LLM output, handling:
    - <think>...</think> reasoning tags (from thinking models like DeepSeek / Qwen)
    - Markdown code blocks (```json ... ```)
    - Stray commentary before or after JSON
    - Trailing commas, formatting quirks, and truncated token outputs
    """
    if not text:
        raise ValueError("Empty model output received.")

    # 1. If output contains </think>, take everything AFTER the closing </think> tag!
    if '</think>' in text.lower():
        parts = re.split(r'</think>', text, flags=re.IGNORECASE)
        after_think = parts[-1].strip()
        if after_think:
            # Check for code blocks or JSON in the post-think section
            code_blocks = re.findall(r'```(?:json)?\s*([\s\S]*?)\s*```', after_think)
            for block in reversed(code_blocks):
                try:
                    return json.loads(block.strip())
                except Exception:
                    try:
                        return repair_json(block)
                    except Exception:
                        pass
            start_curly = after_think.find('{')
            start_square = after_think.find('[')
            starts = [pos for pos in [start_curly, start_square] if pos != -1]
            if starts:
                start_idx = min(starts)
                end_curly = after_think.rfind('}')
                end_square = after_think.rfind(']')
                end_idx = max(end_curly, end_square)
                if start_idx < end_idx:
                    sub = after_think[start_idx:end_idx+1]
                    try:
                        return json.loads(sub)
                    except Exception:
                        try:
                            return repair_json(sub)
                        except Exception:
                            pass

    # 2. Strip reasoning tags (<think>...</think>)
    cleaned_text = re.sub(r'<think>[\s\S]*?</think>', '', text, flags=re.IGNORECASE)
    if '<think>' in cleaned_text.lower():
        cleaned_text = re.sub(r'<think>[\s\S]*', '', cleaned_text, flags=re.IGNORECASE)
    cleaned_text = cleaned_text.strip()
    
    # If stripping removed everything, fallback to original
    target = cleaned_text if cleaned_text else text

    # 3. Check for markdown code blocks (try all matches)
    code_blocks = re.findall(r'```(?:json)?\s*([\s\S]*?)\s*```', target)
    for block in reversed(code_blocks):
        block_clean = block.strip()
        try:
            return json.loads(block_clean)
        except Exception:
            try:
                return repair_json(block_clean)
            except Exception:
                pass

    # 4. Try direct load of cleaned text
    try:
        return json.loads(target)
    except Exception:
        pass

    # 5. Search for outermost valid JSON structure ({...} or [...])
    start_curly = target.find('{')
    start_square = target.find('[')
    starts = [pos for pos in [start_curly, start_square] if pos != -1]
    
    if starts:
        start_idx = min(starts)
        end_curly = target.rfind('}')
        end_square = target.rfind(']')
        end_idx = max(end_curly, end_square)
        
        if start_idx < end_idx:
            sub = target[start_idx:end_idx+1]
            try:
                return json.loads(sub)
            except Exception:
                try:
                    return repair_json(sub)
                except Exception:
                    pass

    # 6. Try repairing target directly (handles truncated outputs)
    try:
        return repair_json(target)
    except Exception:
        pass

    # 7. Last-resort regex search for any JSON structure
    for match in re.finditer(r'(\{[\s\S]*\}|\[[\s\S]*\])', target):
        try:
            return json.loads(match.group(0))
        except Exception:
            try:
                return repair_json(match.group(0))
            except Exception:
                pass

    raise ValueError(f"No valid JSON block found in model output: {text[:300]}...")


def load_prompt(name: str) -> str:
    path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 
        "prompts", 
        f"{name}.md"
    )
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def sanitize_model_name(raw: str) -> str:
    if not raw:
        return ""
    return raw.split("#")[0].strip()


cached_groq_models = None

async def get_active_groq_model(api_key: str, requested_model: str) -> str:
    global cached_groq_models
    import httpx
    
    clean_model = sanitize_model_name(requested_model)
    # Automatically map reasoning or decommissioned models to the ultra-fast, non-reasoning GPT-OSS model
    if not clean_model or "qwen" in clean_model.lower() or "llama" in clean_model.lower():
        clean_model = "openai/gpt-oss-20b"
        
    if cached_groq_models is None:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(
                    "https://api.groq.com/openai/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"}
                )
                if res.status_code == 200:
                    data = res.json()
                    cached_groq_models = [m["id"] for m in data.get("data", []) if m.get("active", True)]
                    logger.info(f"Discovered {len(cached_groq_models)} active Groq models: {cached_groq_models}")
        except Exception as e:
            logger.warning(f"Failed to query Groq models list: {e}")
            cached_groq_models = []

    if cached_groq_models and clean_model in cached_groq_models:
        return clean_model
        
    # Popular active fallback order
    fallback_priority = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "groq/compound-mini"]
    if cached_groq_models:
        for candidate in fallback_priority:
            if candidate in cached_groq_models:
                logger.info(f"Groq: Model adjusted to active model '{candidate}'")
                return candidate
        if cached_groq_models:
            return cached_groq_models[0]
            
    return "openai/gpt-oss-20b"


async def get_active_ollama_model() -> str:
    url = f"{settings.LLM_BASE_URL}/api/tags"
    import httpx
    clean_model = sanitize_model_name(settings.LLM_MODEL)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                models_list = data.get("models", [])
                pulled_names = [m.get("name") for m in models_list if m.get("name")]
                
                # Check for exact matches
                if clean_model in pulled_names:
                    return clean_model
                
                # Check for tag-less base matches
                config_base = clean_model.split(":")[0]
                for p_name in pulled_names:
                    if p_name.split(":")[0] == config_base:
                        logger.info(f"Ollama dynamic match: Using model '{p_name}' matching base '{config_base}'")
                        return p_name
                
                # Fall back to first available model
                if pulled_names:
                    fallback = pulled_names[0]
                    logger.warning(f"Ollama: Configured model '{clean_model}' not found. Falling back to pulled model '{fallback}' to prevent failure.")
                    return fallback
    except Exception as e:
        logger.warning(f"Ollama tags query failed: {e}. Defaulting to configured model.")
    return clean_model or "qwen2.5:7b"


async def call_llm(system_prompt: str, user_message: str, max_tokens: int = 2048) -> str:
    """
    Calls the configured LLM provider (Groq, OpenAI, or Ollama) using direct HTTP requests.
    """
    provider = os.getenv("LLM_PROVIDER", settings.LLM_PROVIDER or "ollama").strip().lower()
    raw_model = sanitize_model_name(os.getenv("LLM_MODEL", settings.LLM_MODEL))
    
    # Strict instruction for reliable structured output
    strict_system = f"{system_prompt}\n\nCRITICAL: Respond ONLY with a valid JSON object or array. Do NOT output thinking steps, reasoning tags (<think>), or explanations."

    # 1. Groq Provider
    if provider == "groq":
        api_key = os.getenv("GROQ_API_KEY", settings.GROQ_API_KEY or "").strip()
        if not api_key:
            raise ValueError("GROQ_API_KEY is not set in .env")
            
        model = await get_active_groq_model(api_key, raw_model)
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": strict_system},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.1,
            "max_tokens": max_tokens
        }
        
        import httpx
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]

            # Handle 429 Rate Limit automatically
            if response.status_code == 429:
                wait_sec = 8.0
                match = re.search(r'try again in ([\d\.]+)s', response.text, re.IGNORECASE)
                if match:
                    try:
                        wait_sec = min(float(match.group(1)) + 1.0, 30.0)
                    except Exception:
                        pass

                # Try alternative high-speed models first
                fallback_models = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "groq/compound-mini"]
                for fb in fallback_models:
                    if fb != model and (not cached_groq_models or fb in cached_groq_models):
                        payload["model"] = fb
                        logger.info(f"Groq 429 on '{model}': trying alternative fast model: {fb}")
                        fb_res = await client.post(url, headers=headers, json=payload)
                        if fb_res.status_code == 200:
                            return fb_res.json()["choices"][0]["message"]["content"]
                        await asyncio.sleep(1)

                logger.info(f"Groq rate limit cooldown: sleeping {wait_sec}s before final retry on {model}...")
                await asyncio.sleep(wait_sec)
                payload["model"] = model
                retry_res = await client.post(url, headers=headers, json=payload)
                if retry_res.status_code == 200:
                    return retry_res.json()["choices"][0]["message"]["content"]
                raise Exception(f"Groq rate limit: {retry_res.text}")

            elif response.status_code in [400, 404] and "model" in response.text.lower():
                logger.warning(f"Groq: Model '{model}' not found or unsupported ({response.text}). Falling back to 'openai/gpt-oss-20b'.")
                payload["model"] = "openai/gpt-oss-20b"
                fallback_res = await client.post(url, headers=headers, json=payload)
                if fallback_res.status_code == 200:
                    return fallback_res.json()["choices"][0]["message"]["content"]
                raise Exception(f"Groq fallback failed: Status {fallback_res.status_code} - {fallback_res.text}")
            else:
                raise Exception(f"Groq call failed: Status {response.status_code} - {response.text}")

    # 2. OpenAI Provider
    elif provider == "openai":
        api_key = settings.OPENAI_API_KEY.strip() if settings.OPENAI_API_KEY else ""
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set in .env")
            
        model = raw_model or "gpt-4o"
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.2
        }
        
        import httpx
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            else:
                raise Exception(f"OpenAI call failed: Status {response.status_code} - {response.text}")

    # 3. Ollama Provider (Default fallback)
    else:
        resolved_model = await get_active_ollama_model()
        url = f"{settings.LLM_BASE_URL}/api/chat"
        payload = {
            "model": resolved_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "options": {
                "temperature": 0.2
            },
            "stream": False
        }
        
        import httpx
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                data = response.json()
                return data["message"]["content"]
            else:
                raise Exception(f"Ollama call failed: Status {response.status_code} - {response.text}")


# --- Graph Node Implementations ---

async def discover_process_node(state: AgentState) -> Dict[str, Any]:
    logger.info("Entering: Discover Process Node")
    db: Session = SessionLocal()
    try:
        # Check if the process exists and has activities
        process = db.query(models.Process).filter(models.Process.id == state["process_id"]).first()
        if not process:
            return {"error": "Process not found in database."}

        existing_activities = db.query(models.CurrentActivity).filter(
            models.CurrentActivity.process_id == process.id
        ).all()

        if existing_activities:
            logger.info("Found existing/seeded current activities. Skipping LLM discovery.")
            activities_list = []
            for act in existing_activities:
                activities_list.append({
                    "id": act.id,
                    "name": act.name,
                    "role": act.role,
                    "system": act.system,
                    "problem": act.problem,
                    "evidence": act.evidence
                })
            return {"current_activities": activities_list}

        # Otherwise, discover process activities using LLM
        prompt_template = load_prompt("discovery")
        system_prompt = "You are a Business Process Discovery Agent."
        user_msg = prompt_template.replace("{industry}", state["industry"]).replace("{process_name}", state["process_name"])

        logger.info(f"Invoking LLM for Process Discovery: {state['process_name']}")
        output = await call_llm(system_prompt, user_msg)
        parsed_activities = extract_json_block(output)
        if isinstance(parsed_activities, dict):
            parsed_activities = parsed_activities.get("activities", parsed_activities.get("current_activities", [parsed_activities]))

        activities_list = []
        for act in parsed_activities:
            if not isinstance(act, dict):
                continue
            db_act = models.CurrentActivity(
                process_id=process.id,
                name=act.get("name", "Discovered Activity"),
                role=act.get("role", "N/A"),
                system=act.get("system", "N/A"),
                problem=act.get("problem", "N/A"),
                evidence=act.get("evidence", "")
            )
            db.add(db_act)
            db.flush()
            activities_list.append({
                "id": db_act.id,
                "name": db_act.name,
                "role": db_act.role,
                "system": db_act.system,
                "problem": db_act.problem,
                "evidence": db_act.evidence
            })
        
        db.commit()
        logger.info(f"Discovered {len(activities_list)} current activities.")
        return {"current_activities": activities_list}
    except Exception as e:
        logger.error(f"Error in discovery node: {e}", exc_info=True)
        db.rollback()
        return {"error": f"Discovery Agent failed: {e}"}
    finally:
        db.close()


async def generate_queries_node(state: AgentState) -> Dict[str, Any]:
    logger.info("Entering: Generate Queries Node")
    if "error" in state and state["error"]:
        return {"error": state["error"]}

    db: Session = SessionLocal()
    try:
        current_state_lines = []
        for idx, act in enumerate(state["current_activities"]):
            prob = act.get("problem", "N/A")
            if len(prob) > 250:
                prob = prob[:250] + "..."
            current_state_lines.append(
                f"{idx+1}. Activity: {act['name']}\n   Role: {act['role']}\n   System: {act['system']}\n   Problem: {prob}"
            )
        current_state_context = "\n\n".join(current_state_lines)

        prompt_template = load_prompt("researcher")
        system_prompt = "You are a Technology Research Planning Agent."
        user_msg = prompt_template.replace("{industry}", state["industry"]).replace("{process_name}", state["process_name"]).replace("{current_state_context}", current_state_context)

        logger.info("Generating research queries using LLM.")
        output = await call_llm(system_prompt, user_msg, max_tokens=1500)
        parsed_queries = extract_json_block(output)
        if isinstance(parsed_queries, dict):
            parsed_queries = parsed_queries.get("queries", parsed_queries.get("research_queries", [parsed_queries]))

        queries_list = []
        for q in parsed_queries:
            if not isinstance(q, dict):
                continue
            db_query = models.ResearchQuery(
                process_id=state["process_id"],
                query_text=q.get("query", str(q)),
                intent=q.get("intent", "AI Opportunity")
            )
            db.add(db_query)
            db.flush()
            queries_list.append({
                "id": db_query.id,
                "query_text": db_query.query_text,
                "intent": db_query.intent
            })

        db.commit()
        logger.info(f"Generated {len(queries_list)} queries.")
        return {"research_queries": queries_list}
    except Exception as e:
        logger.error(f"Error in query generation node: {e}", exc_info=True)
        db.rollback()
        return {"error": f"Researcher Planning Agent failed: {e}"}
    finally:
        db.close()


async def execute_research_node(state: AgentState) -> Dict[str, Any]:
    logger.info("Entering: Execute Research Node")
    if "error" in state and state["error"]:
        return {"error": state["error"]}

    db: Session = SessionLocal()
    try:
        search_provider = get_search_provider(state.get("search_provider"))
        search_results = []

        for q in state["research_queries"]:
            raw_results = await search_provider.search(q["query_text"], limit=4)
            # Dynamic Fallback: if search fails or returns empty, use MockSearchProvider to prevent empty comparisons
            if not raw_results:
                logger.warning(f"Active search provider returned empty results for '{q['query_text']}'. Falling back to MockSearchProvider.")
                from backend.app.search.mock_provider import MockSearchProvider
                mock_provider = MockSearchProvider()
                raw_results = await mock_provider.search(q["query_text"], limit=4)
            for res in raw_results:
                db_source = models.ResearchSource(
                    query_id=q["id"],
                    process_id=state["process_id"],
                    title=res["title"],
                    url=res["url"],
                    retrieved_content=res["snippet"],
                    metadata_json={}
                )
                db.add(db_source)
                db.flush()
                search_results.append({
                    "id": db_source.id,
                    "query_id": q["id"],
                    "title": db_source.title,
                    "url": db_source.url,
                    "snippet": db_source.retrieved_content
                })

        db.commit()
        logger.info(f"Retrieved and saved {len(search_results)} search sources.")
        return {"search_results": search_results}
    except Exception as e:
        logger.error(f"Error in research node: {e}", exc_info=True)
        db.rollback()
        return {"error": f"Web Research Execution failed: {e}"}
    finally:
        db.close()


async def synthesize_evidence_node(state: AgentState) -> Dict[str, Any]:
    logger.info("Entering: Synthesize Evidence Node")
    if "error" in state and state["error"]:
        return {"error": state["error"]}

    db: Session = SessionLocal()
    try:
        evidence_analyses = []
        prompt_template = load_prompt("synthesis")
        system_prompt = "You are an Evidence Synthesis Agent."

        # Group search results to make them accessible for each activity
        sources_summary_lines = []
        for src in state["search_results"][:6]:
            snip = src.get("snippet", "")
            if len(snip) > 250:
                snip = snip[:250] + "..."
            sources_summary_lines.append(
                f"- Source Title: {src['title']}\n  URL: {src['url']}\n  Snippet: {snip}"
            )
        all_sources_text = "\n\n".join(sources_summary_lines)

        # Use Semaphore to throttle concurrent synthesis requests to avoid rate limit spikes
        sem = asyncio.Semaphore(2)

        async def _synthesize_for_activity(act):
            async with sem:
                user_msg = prompt_template.replace("{activity_name}", act["name"]).replace("{problem}", act["problem"]).replace("{search_sources}", all_sources_text)
                logger.info(f"Synthesizing evidence for activity: '{act['name']}'")
                output = await call_llm(system_prompt, user_msg, max_tokens=1500)
                parsed = extract_json_block(output)
                await asyncio.sleep(0.4)  # 400ms buffer between Groq calls
                return act, parsed, output

        # Concurrently synthesize evidence across activities
        tasks = [_synthesize_for_activity(act) for act in state["current_activities"]]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for item in results:
            if isinstance(item, Exception):
                logger.error(f"Activity synthesis error: {item}")
                continue
            act, parsed_synthesis, output = item

            # Match to a source URL from the search results if present, or assign the first source
            matched_source_id = None
            if state["search_results"]:
                matched_source_id = state["search_results"][0]["id"]
                # Try finding a source in text matching the URL
                for src in state["search_results"]:
                    if src["url"] in output or src["title"] in output:
                        matched_source_id = src["id"]
                        break

            if not matched_source_id and state["search_results"]:
                matched_source_id = state["search_results"][0]["id"]

            if not matched_source_id:
                # If search returned nothing, create a fallback source record
                fallback_source = models.ResearchSource(
                    process_id=state["process_id"],
                    title="Industry Best Practice Insights",
                    url="https://www.shopify.com/blog/retail-operations",
                    retrieved_content="Standard operational optimization documentation."
                )
                db.add(fallback_source)
                db.flush()
                matched_source_id = fallback_source.id

            evidence_summary_text = to_str(parsed_synthesis.get("evidence_summary", ""))
            # Compute embeddings for pgvector support
            embedding_vector = get_embedding(evidence_summary_text) if evidence_summary_text else None

            db_analysis = models.EvidenceAnalysis(
                source_id=matched_source_id,
                activity_id=act["id"],
                problem=to_str(act.get("problem", "")),
                technology=to_str(parsed_synthesis.get("technology", "")),
                how_it_works=to_str(parsed_synthesis.get("how_it_works", "")),
                applicability_why=to_str(parsed_synthesis.get("applicability_why", "")),
                parts_to_automate=to_str(parsed_synthesis.get("parts_to_automate", "")),
                human_control=to_str(parsed_synthesis.get("human_control", "")),
                systems_roles_affected=to_str(parsed_synthesis.get("systems_roles_affected", "")),
                future_state_description=to_str(parsed_synthesis.get("future_state_description", "")),
                evidence_summary=evidence_summary_text,
                embedding=embedding_vector
            )
            db.add(db_analysis)
            db.flush()
            evidence_analyses.append({
                "id": db_analysis.id,
                "activity_id": act["id"],
                "technology": db_analysis.technology,
                "how_it_works": db_analysis.how_it_works,
                "applicability_why": db_analysis.applicability_why,
                "future_state_description": db_analysis.future_state_description,
                "evidence_summary": db_analysis.evidence_summary
            })

        db.commit()
        logger.info(f"Synthesized evidence for {len(evidence_analyses)} activities.")
        return {"evidence_analyses": evidence_analyses}
    except Exception as e:
        logger.error(f"Error in synthesis node: {e}", exc_info=True)
        db.rollback()
        return {"error": f"Evidence Synthesis Agent failed: {e}"}
    finally:
        db.close()


async def design_transformation_node(state: AgentState) -> Dict[str, Any]:
    logger.info("Entering: Design Transformation Node")
    if "error" in state and state["error"]:
        return {"error": state["error"]}

    db: Session = SessionLocal()
    try:
        # Prepare context inputs
        current_activities_lines = []
        for act in state["current_activities"]:
            prob = act.get("problem", "N/A")
            if len(prob) > 250:
                prob = prob[:250] + "..."
            current_activities_lines.append(
                f"- Name: {act['name']}\n  Role: {act['role']}\n  System: {act['system']}\n  Problem: {prob}"
            )
        current_activities_str = "\n".join(current_activities_lines)

        evidence_lines = []
        for idx, ev in enumerate(state["evidence_analyses"]):
            ev_sum = ev.get("evidence_summary", "")
            if len(ev_sum) > 250:
                ev_sum = ev_sum[:250] + "..."
            evidence_lines.append(
                f"Evidence Item [{idx}]:\n- Activity ID: {ev['activity_id']}\n- Technology: {ev['technology']}\n- How It Works: {ev['how_it_works']}\n- Future State: {ev['future_state_description']}\n- Evidence Summary: {ev_sum}"
            )
        synthesized_evidence_str = "\n\n".join(evidence_lines)

        prompt_template = load_prompt("transformation")
        system_prompt = "You are a Transformation Designer Agent."
        user_msg = prompt_template.replace("{industry}", state["industry"]).replace("{process_name}", state["process_name"]).replace("{current_activities}", current_activities_str).replace("{synthesized_evidence}", synthesized_evidence_str)

        logger.info("Invoking LLM for Transformation Design.")
        output = await call_llm(system_prompt, user_msg, max_tokens=4096)
        parsed_transformation = extract_json_block(output)

        # Save AI Opportunities
        opp_map = {}
        for opp in parsed_transformation.get("opportunities", []):
            if not isinstance(opp, dict):
                continue
            opp_name = to_str(opp.get("opportunity_name", "AI Opportunity"))
            db_opp = models.AIOpportunity(
                process_id=state["process_id"],
                opportunity_name=opp_name,
                description=to_str(opp.get("description", "")),
                technology=to_str(opp.get("technology", "")),
                expected_benefit=to_str(opp.get("expected_benefit", "")),
                risk=to_str(opp.get("risk", ""))
            )
            db.add(db_opp)
            db.flush()
            opp_map[opp_name] = db_opp.id

        # Save Future Activities and establish explicit relations
        future_activities_list = []
        ai_opportunities_list = list(opp_map.values())

        for fa in parsed_transformation.get("future_activities", []):
            if not isinstance(fa, dict):
                continue
            # Find corresponding current activity id
            curr_act_name = to_str(fa.get("current_activity_name", ""))
            matched_curr_act_id = None
            for ca in state["current_activities"]:
                if ca["name"].strip().lower() == curr_act_name.strip().lower() or curr_act_name.strip().lower() in ca["name"].strip().lower():
                    matched_curr_act_id = ca["id"]
                    break

            if not matched_curr_act_id and state["current_activities"]:
                matched_curr_act_id = state["current_activities"][0]["id"]

            db_fa = models.FutureActivity(
                process_id=state["process_id"],
                current_activity_id=matched_curr_act_id,
                name=to_str(fa.get("name", "Future Activity")),
                role=to_str(fa.get("role", "AI/Human")),
                system=to_str(fa.get("system", "New System")),
                decision_type=to_str(fa.get("decision_type", "AI-assisted")),
                expected_benefit=to_str(fa.get("expected_benefit", "")),
                risk=to_str(fa.get("risk", ""))
            )
            db.add(db_fa)
            db.flush()

            # Find matching Opportunity ID
            linked_opp_name = to_str(fa.get("linked_opportunity_name", ""))
            matched_opp_id = opp_map.get(linked_opp_name)
            if not matched_opp_id and opp_map:
                matched_opp_id = list(opp_map.values())[0]

            # Find matching Evidence Analysis ID
            ev_idx = fa.get("linked_evidence_index", 0)
            matched_ev_id = None
            if isinstance(ev_idx, int) and 0 <= ev_idx < len(state["evidence_analyses"]):
                matched_ev_id = state["evidence_analyses"][ev_idx]["id"]
            elif state["evidence_analyses"]:
                matched_ev_id = state["evidence_analyses"][0]["id"]

            # Save the relationship to verify provenance: Future Activity -> AI Opportunity -> Evidence Analysis
            if matched_opp_id and matched_ev_id:
                db_rel = models.EvidenceRelationship(
                    future_activity_id=db_fa.id,
                    ai_opportunity_id=matched_opp_id,
                    evidence_analysis_id=matched_ev_id
                )
                db.add(db_rel)
                db.flush()

            future_activities_list.append({
                "id": db_fa.id,
                "name": db_fa.name,
                "role": db_fa.role,
                "system": db_fa.system,
                "decision_type": db_fa.decision_type,
                "expected_benefit": db_fa.expected_benefit,
                "risk": db_fa.risk
            })

        db.commit()
        logger.info(f"Transformation design generated {len(future_activities_list)} future activities and {len(ai_opportunities_list)} opportunities.")
        return {
            "future_activities": future_activities_list,
            "ai_opportunities": ai_opportunities_list
        }
    except Exception as e:
        logger.error(f"Error in transformation design node: {e}", exc_info=True)
        db.rollback()
        return {"error": f"Transformation Designer Agent failed: {e}"}
    finally:
        db.close()
