import os

DEFAULT_MODELS = {
    "anthropic": "claude-opus-5",
    "openai": "gpt-5",
    "gemini": "gemini-2.5-pro",
}


def _require_env(var):
    if not os.environ.get(var):
        raise SystemExit(f"set {var} in your environment")


def _import(name):
    try:
        module = __import__(name)
        if module is None:
            raise ImportError(name)
        return module
    except ImportError:
        raise SystemExit(f"provider needs the SDK: pip install {name}")


def _anthropic(model, prompt):
    anthropic = _import("anthropic")
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=model,
        max_tokens=16000,
        messages=[{"role": "user", "content": prompt}],
    )
    if resp.stop_reason == "refusal":
        raise SystemExit("model declined the request; try rewording tone or fun facts")
    return "".join(b.text for b in resp.content if b.type == "text")


def _openai(model, prompt):
    _require_env("OPENAI_API_KEY")
    openai = _import("openai")
    client = openai.OpenAI()
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content


def _gemini(model, prompt):
    _require_env("GEMINI_API_KEY")
    try:
        import importlib
        genai = importlib.import_module("google.genai")
        if genai is None:
            raise ImportError
    except ImportError:
        raise SystemExit("provider needs the SDK: pip install google-genai")
    client = genai.Client()
    resp = client.models.generate_content(model=model, contents=prompt)
    return resp.text


_PROVIDERS = {"anthropic": _anthropic, "openai": _openai, "gemini": _gemini}


def generate(provider, model, prompt):
    fn = _PROVIDERS.get(provider)
    if fn is None:
        raise SystemExit(f"unknown provider '{provider}'; choose from {sorted(_PROVIDERS)}")
    try:
        return fn(model, prompt)
    except SystemExit:
        raise
    except Exception as e:
        raise SystemExit(f"{provider} error: {type(e).__name__}: {e}")
