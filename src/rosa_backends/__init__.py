"""Model selection for the modified ROSA fork's controlled experiments."""


def create_model(backend, *, model=None, base_url=None, siwc_transport=None, num_ctx=4096, use_mmap=None):
    """Return a tool-capable BaseChatModel without changing ROSA's agent loop."""
    if backend == 'ollama':
        if siwc_transport is not None:
            raise ValueError('OAuth transport supplied for a local model')
        from langchain_ollama import ChatOllama
        model_class = ChatOllama
        options = {}
        if use_mmap is not None:
            from .chat_ollama import ConfiguredChatOllama
            model_class = ConfiguredChatOllama
            options['use_mmap'] = use_mmap
        return model_class(model=model or 'qwen3.5:9b',
                          base_url=base_url or 'http://127.0.0.1:11434',
                          temperature=0, reasoning=False, num_ctx=num_ctx,
                          num_predict=256, seed=42, streaming=False,
                          client_kwargs={'timeout': 300}, cache=False, **options)
    if backend == 'siwc':
        if base_url is not None:
            raise ValueError('OAuth endpoint cannot be overridden')
        if not model or siwc_transport is None:
            raise ValueError('OAuth requires an account catalog model and authenticated transport')
        from .chat_siwc import ChatSiwc
        return ChatSiwc(model=model, backend=siwc_transport)
    raise ValueError('Unknown model backend')


def create_mock_agent(llm, tools, *, max_iterations=5, prompts=None):
    """Use the real ROSA executor with an exact, custom-only registry."""
    from rosa import ROSA
    tools = list(tools)
    expected = tuple(tool.name for tool in tools)
    if not expected or len(set(expected)) != len(expected):
        raise ValueError('An explicit, nonempty tool allowlist with unique names is required')
    agent = ROSA(2, llm, tools=tools, load_default_tools=False,
                 streaming=False, accumulate_chat_history=False,
                 max_iterations=max_iterations, prompts=prompts)
    if len(agent.tool_names) != len(expected) or set(agent.tool_names) != set(expected):
        raise RuntimeError('Unexpected ROSA tool registry')
    return agent
