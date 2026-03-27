# Research Knowledge Base

A TUI-based application for managing and chatting with research papers and blog posts.

## LLM Configuration

The application uses LiteLLM to interface with various LLM providers (Groq, OpenAI, Ollama, OpenRouter, etc.).

### Adding an LLM Configuration

You can configure a default LLM through the TUI using the `/llm-configs` command.

1. Open the TUI: `uv run manage.py tui`
2. Type `/llm-configs` and press Enter (you can use Tab for command autocomplete).
3. Fill in the provider (e.g., `groq`, `openai`, `ollama`).
4. Fill in the model name (e.g., `groq/llama-3.1-8b-instant`, `openai/gpt-4o`).
5. You can provide an API key in the form, which will be saved in the database. Alternatively, you can provide the API key in your `.env` file.

Note that model name and api key env var should be set according to `litellm` docs. Check the docs for the provider you're using, e.g: <https://docs.litellm.ai/docs/providers/groq>

### Environment Variables for API Keys

If you prefer not to enter your API key in the TUI form, you can add it to your `.env` file in the root directory. The application will automatically pick up keys from the environment.

**Important:** Your environment variable names must adhere to [LiteLLM's naming conventions](https://docs.litellm.ai/docs/providers).

Common examples for `.env`:

```env
GROQ_API_KEY=your_groq_api_key
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
OPENROUTER_API_KEY=your_openrouter_api_key
```

## The TUI

Run the backend server:

```bash
uv run manage.py runserver 8001
```

Then, the TUI:

```bash
uv run manage.py tui
```
