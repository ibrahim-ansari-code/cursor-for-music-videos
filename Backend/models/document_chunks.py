# """
# Document Chunks Model for Vector Embeddings

# This model represents document chunks stored with vector embeddings
# for semantic search capabilities in the Brikli Agent.
# """
# from typing import Optional, Any
# from uuid import UUID, uuid4
# from datetime import datetime, UTC
# from sqlmodel import SQLModel, Field, JSON, Column
# from sqlalchemy import DateTime
# from sqlalchemy.dialects.postgresql import UUID
# from pgvector.sqlalchemy import Vector
# from pydantic import ConfigDict


# class DocumentChunkBase(SQLModel):
#     """Base model for document chunks"""
#     model_config = ConfigDict(arbitrary_types_allowed=True)
    
#     user_id: UUID = Field(foreign_key="users.id", index=True)
#     source_id: UUID = Field(index=True)
#     source_type: str = Field(max_length=50, index=True)
#     content: str
#     chunk_metadata: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


# class DocumentChunk(DocumentChunkBase, table=True):
#     """
#     Document chunk with vector embedding for semantic search
    
#     Attributes:
#         id: Unique identifier
#         user_id: User who owns this document chunk
#         source_id: ID of the source document (lease_id, invoice_id, etc.)
#         source_type: Type of source document ('lease', 'invoice', 'expense', etc.)
#         content: Text content of the chunk
#         embedding: Vector embedding from OpenAI text-embedding-ada-002 (1536 dimensions)
#         chunk_metadata: Additional metadata (page number, section, chunk index, etc.)
#         created_at: Timestamp when the chunk was created
#     """
#     __tablename__ = "document_chunks"  # type: ignore
    
#     id: UUID = Field(
#         default_factory=uuid4,
#         primary_key=True,
#         sa_column_kwargs={"server_default": "gen_random_uuid()"}
#     )
    
#     # Vector column for embeddings - using pgvector
#     # Note: We use sa_column to properly define the vector type
#     embedding: Optional[list[float]] = Field(
#         default=None,
#         sa_column=Column(Vector(1536), nullable=True)
#     )
    
#     created_at: datetime = Field(
#         default_factory=lambda: datetime.now(UTC),
#         sa_column=Column(DateTime(timezone=True), nullable=False)
#     )


# class DocumentChunkCreate(DocumentChunkBase):
#     """Schema for creating a document chunk"""
#     embedding: Optional[list[float]] = None


# class DocumentChunkRead(DocumentChunkBase):
#     """Schema for reading a document chunk"""
#     id: UUID
#     created_at: datetime
#     # Embedding is optional in read to avoid sending large vectors unnecessarily
#     embedding: Optional[list[float]] = None


# class DocumentChunkSearch(SQLModel):
#     """Schema for search results with similarity score"""
#     id: UUID
#     content: str
#     source_id: UUID
#     source_type: str
#     chunk_metadata: dict[str, Any]
#     similarity: float
#     created_at: datetime
