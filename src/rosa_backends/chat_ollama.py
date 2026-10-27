"""Expose an explicit loading option absent from pinned ChatOllama 0.3.10."""
from langchain_ollama import ChatOllama


class ConfiguredChatOllama(ChatOllama):
    use_mmap: bool

    def _chat_params(self, messages, stop=None, **kwargs):
        params = super()._chat_params(messages, stop=stop, **kwargs)
        params['options'] = {**params['options'], 'use_mmap': self.use_mmap}
        return params
