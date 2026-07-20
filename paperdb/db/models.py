"""Pydantic models for all PaperDB entities."""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class Paper(BaseModel):
    id: Optional[int] = None
    paper_key: str
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    title: Optional[str] = None
    authors_text: Optional[str] = None
    year: Optional[int] = None
    journal: Optional[str] = None
    abstract: Optional[str] = None
    keywords: Optional[str] = None
    essence: Optional[str] = None
    markdown_path: Optional[str] = None
    json_path: Optional[str] = None
    bibtex_path: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class PaperFile(BaseModel):
    id: Optional[int] = None
    paper_id: int
    path: str
    file_role: Optional[str] = None
    version_label: Optional[str] = None
    file_size: Optional[int] = None
    modified_time: Optional[float] = None
    sha256: Optional[str] = None
    exists_now: int = 1
    is_preferred: int = 0
    last_seen: Optional[str] = None

class SearchUnit(BaseModel):
    id: Optional[int] = None
    paper_id: int
    run_id: Optional[int] = None
    unit_type: Optional[str] = None
    source_type: Optional[str] = None
    source_id: Optional[int] = None
    section_path: Optional[str] = None
    page_from: Optional[int] = None
    page_to: Optional[int] = None
    content: Optional[str] = None

class ProcessingRun(BaseModel):
    id: Optional[int] = None
    paper_id: int
    operation: str
    backend: Optional[str] = None
    backend_version: Optional[str] = None
    model_name: Optional[str] = None
    prompt_version: Optional[str] = None
    configuration_json: Optional[str] = None
    config_hash: Optional[str] = None
    source_file_id: Optional[int] = None
    input_sha256: Optional[str] = None
    output_path: Optional[str] = None
    supersedes_run_id: Optional[int] = None
    status: str = "pending"
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    message: Optional[str] = None

class Tag(BaseModel):
    id: Optional[int] = None
    canonical_name: str
    category: str

class TagAlias(BaseModel):
    tag_id: int
    alias: str
    normalized_alias: str

class PaperTag(BaseModel):
    paper_id: int
    tag_id: int
    source: Optional[str] = None
    run_id: Optional[int] = None
    confidence: Optional[float] = None
    raw_name: Optional[str] = None

class Equation(BaseModel):
    id: Optional[int] = None
    paper_id: int
    run_id: Optional[int] = None
    latex_raw: Optional[str] = None
    latex_normalized: Optional[str] = None
    equation_number: Optional[str] = None
    section_path: Optional[str] = None
    page_number: Optional[int] = None
    bbox_json: Optional[str] = None
    context_before: Optional[str] = None
    context_after: Optional[str] = None
    parser: Optional[str] = None
    confidence: Optional[float] = None
    verification_status: Optional[str] = None

class EquationVariable(BaseModel):
    id: Optional[int] = None
    equation_id: int
    symbol: Optional[str] = None
    meaning: Optional[str] = None
    source_page: Optional[int] = None
    source_context: Optional[str] = None

class Method(BaseModel):
    id: Optional[int] = None
    paper_id: int
    run_id: Optional[int] = None
    name: Optional[str] = None
    method_type: Optional[str] = None
    purpose: Optional[str] = None
    complexity: Optional[str] = None
    confidence: Optional[float] = None
    card_json: Optional[str] = None
    source_passages_json: Optional[str] = None
    created_at: Optional[str] = None

class MethodEquation(BaseModel):
    method_id: int
    equation_id: int
    role: Optional[str] = None

class Summary(BaseModel):
    id: Optional[int] = None
    paper_id: int
    run_id: Optional[int] = None
    model_name: Optional[str] = None
    prompt_version: Optional[str] = None
    content: Optional[str] = None
    timestamp: Optional[str] = None
    is_active: int = 1

class ContextPack(BaseModel):
    id: Optional[int] = None
    query: str
    filters_json: Optional[str] = None
    selected_units_json: Optional[str] = None
    content: Optional[str] = None
    output_path: Optional[str] = None
    created_at: Optional[str] = None

class Topic(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    created_at: Optional[str] = None

class TopicPaper(BaseModel):
    topic_id: int
    paper_id: int
    relevance: Optional[str] = None
    match_score: Optional[float] = None

class TopicOverview(BaseModel):
    id: Optional[int] = None
    topic_id: int
    content: Optional[str] = None
    original_query: Optional[str] = None
    filters_json: Optional[str] = None
    comparison_matrix_json: Optional[str] = None
    model_name: Optional[str] = None
    prompt_version: Optional[str] = None
    timestamp: Optional[str] = None
    is_active: int = 1

class Citation(BaseModel):
    citing_paper_id: int
    cited_doi: Optional[str] = None
    cited_title: Optional[str] = None
    matched_paper_id: Optional[int] = None

class SearchResult(BaseModel):
    paper: Paper
    score: float = 0.0
    match_reasons: list[str] = Field(default_factory=list)
