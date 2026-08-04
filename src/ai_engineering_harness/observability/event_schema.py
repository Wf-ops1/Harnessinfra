from pydantic import BaseModel, Field


class HarnessTraceEvent(BaseModel):
    event_id: str = Field(description="ID único do evento de rastreio")
    execution_id: str = Field(description="ID de execução da funcionalidade/grafo")
    graph_name: str = Field(description="Nome do grafo em execução")
    node_id: str = Field(description="ID do nó que emitiu o evento")
    event_type: str = Field(description="Tipo de evento (node.started, node.completed, node.failed)")
    timestamp: str = Field(description="Timestamp ISO 8601")
    details: dict = Field(default_factory=dict, description="Dados contextuais estruturados do evento")
