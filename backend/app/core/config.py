from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://nexar:nexar@db:5432/nexar_ops"
    dev_user_email: str = "ahmad.shafqat@getnexar.com"
    # When true, outbound URL checks (private/loopback ranges etc.) are bypassed so
    # resources can target localhost during development. Must stay OFF in production;
    # docker-compose enables it explicitly for local dev.
    allow_local_test: bool = False
    cors_origins: str = "http://localhost:3000,http://frontend:3000"
    # Prefix for internal tools (path-only urls), e.g. http://backend:8000
    internal_api_base_url: str = "http://backend:8000"
    # Secret header values on resources may only reference env vars with this prefix,
    # so resource definitions can't read arbitrary process env (API keys, DB URLs).
    resource_secret_env_prefix: str = "RESOURCE_SECRET_"

    sop_search_top_k: int = 5
    # Threshold when the model explicitly calls search_sop_processes.
    sop_match_threshold: float = 0.35
    # Stricter threshold for the automatic per-message SOP match, which runs on
    # every message. Keeping it higher avoids informational/KB questions being
    # wrongly locked into an SOP (which would filter the tool set mid-turn).
    sop_auto_match_threshold: float = 0.5
    # A matched SOP must beat the runner-up by at least this margin to be auto-locked.
    # Prevents locking the wrong SOP when two candidates score nearly the same (common
    # once many similar SOPs exist); ambiguous cases defer to the model to disambiguate.
    sop_auto_match_margin: float = 0.08
    agent_max_tool_rounds: int = 8

    llm_provider: str = "openai"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = ""
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    gemini_model: str = "gemini-2.0-flash"
    google_api_key: str = ""
    # Low temperature keeps tool routing deterministic (avoids the model narrating
    # "I'll search..." as plain text instead of emitting a real tool call).
    llm_temperature: float = 0.2
    llm_max_tokens: int = 1024
    # Resiliency for LLM calls: per-attempt timeout + bounded exponential backoff on
    # transient failures (rate limit / overloaded / 5xx). Tune per environment.
    llm_timeout_seconds: float = 60.0
    llm_max_attempts: int = 3
    llm_retry_base_delay: float = 0.5
    # Separate budget for KB formatting — response must include full markdown JSON.
    kb_format_max_tokens: int = 8192
    # KB formatting is a faithful transformation, not a creative task — run it at
    # temperature 0 for maximum determinism and to minimize heading paraphrasing/merging.
    kb_format_temperature: float = 0.0

    embedding_provider: str = "local"
    embedding_model_local: str = "BAAI/bge-small-en-v1.5"
    embedding_model_google: str = "text-embedding-004"
    embedding_dimensions: int = 384
    kb_search_top_k: int = 8
    kb_max_result_chars: int = 12000
    # Diversity: cap how many sections a single article can contribute to the top
    # results, so one long article can't crowd out other relevant articles.
    # Open slots are backfilled from the best remaining sections regardless of cap,
    # so single-article queries are not penalized.
    kb_max_sections_per_reference: int = 3
    # How many candidate chunks to pull before section dedup + diversity selection.
    # Larger pool => better chance of surfacing other articles before dedup.
    kb_candidate_multiplier: int = 6


settings = Settings()
