"""Módulo Knowledge: Transação de Conhecimento em 5 Etapas com fsync."""

from .synchronizer import KnowledgeSynchronizer
from .transaction import KnowledgeTransactionManager, TransactionState

__all__ = ["KnowledgeSynchronizer", "KnowledgeTransactionManager", "TransactionState"]
