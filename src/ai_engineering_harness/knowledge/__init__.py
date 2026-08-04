"""Módulo Knowledge: Transação de Conhecimento em 5 Etapas com fsync."""

from .transaction import KnowledgeTransactionManager, TransactionState
from .synchronizer import KnowledgeSynchronizer

__all__ = ["KnowledgeTransactionManager", "TransactionState", "KnowledgeSynchronizer"]
