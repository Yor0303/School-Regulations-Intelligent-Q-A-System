__all__ = ["KnowledgeBaseService"]


def __getattr__(name):
    if name == "KnowledgeBaseService":
        from .kb_service import KnowledgeBaseService

        return KnowledgeBaseService
    raise AttributeError(name)
