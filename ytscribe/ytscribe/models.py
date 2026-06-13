from pydantic import BaseModel, Field
from typing import Optional


class Segment(BaseModel):
    start: float  # seconds
    end: float
    text: str


class VideoMetadata(BaseModel):
    video_id: str
    title: str
    channel: str
    channel_url: Optional[str] = None
    duration: int  # seconds
    upload_date: Optional[str] = None  # YYYYMMDD
    description: Optional[str] = None
    thumbnail: Optional[str] = None
    webpage_url: str


class Moment(BaseModel):
    t: int  # seconds
    reason: str
    caption: str


class KeyQuote(BaseModel):
    t: int
    text: str


class ClaudeAnalysis(BaseModel):
    title: str
    summary: str
    themes: list[str] = Field(default_factory=list)
    moments: list[Moment] = Field(default_factory=list)
    key_quotes: list[KeyQuote] = Field(default_factory=list)
    note_body_md: str
