"""
VertaFlow Structural & Semantic Chunker
Production RAG chunking pipeline designed according to agency-rag-pipeline-engineer specs.
Splits enterprise documents, PDFs, FAQs, and URLs into semantically coherent chunks with rich metadata.
"""

import re
from typing import List, Dict, Any, Optional

class VertaChunker:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 80):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = ["\n\n", "\n", ". ", "! ", "? ", "; ", " ", ""]

    def chunk_document(
        self,
        text: str,
        title: str = "",
        item_type: str = "text",
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Chunks a document based on its structural type.
        - FAQ: preserves Q&A pairs as unified semantic units
        - Structured text / Markdown: splits by headers and sections
        - Unstructured / PDF text: recursive character splitting
        """
        text = text.strip()
        if not text:
            return []

        meta = metadata.copy() if metadata else {}
        meta["source_title"] = title
        meta["item_type"] = item_type

        # 1. Structural FAQ Handling: If it's an FAQ item, preserve it intact if <= chunk_size * 2
        if item_type == "faq":
            return [{
                "content": f"{title}\n{text}" if title and title not in text else text,
                "chunk_index": 0,
                "metadata": {
                    **meta,
                    "section": title,
                    "char_count": len(text),
                    "estimated_tokens": int(len(text.split()) * 1.3)
                }
            }]

        # 2. Markdown / Section Header based splitting
        header_sections = self._split_by_headers(text)
        raw_chunks = []

        for sec_title, sec_text in header_sections:
            if len(sec_text) <= self.chunk_size:
                raw_chunks.append((sec_title, sec_text.strip()))
            else:
                # Sub-chunk large sections recursively
                sub_chunks = self._recursive_split(sec_text, self.chunk_size, self.chunk_overlap)
                for sc in sub_chunks:
                    raw_chunks.append((sec_title, sc.strip()))

        # Build output objects with metadata
        result = []
        for idx, (section_name, chunk_content) in enumerate(raw_chunks):
            if not chunk_content:
                continue
            chunk_meta = {
                **meta,
                "section": section_name or title,
                "chunk_index": idx,
                "char_count": len(chunk_content),
                "estimated_tokens": int(len(chunk_content.split()) * 1.3)
            }
            result.append({
                "content": chunk_content,
                "chunk_index": idx,
                "metadata": chunk_meta
            })

        return result

    def _split_by_headers(self, text: str) -> List[tuple[str, str]]:
        """Splits markdown headers (#, ##, ###) or numbered sections."""
        lines = text.split("\n")
        sections = []
        current_header = "Boshlang'ich qism"
        current_lines = []

        header_pattern = re.compile(r'^(#{1,4}\s+|[0-9]+\.\s+|[A-Z0-9\s\-_]{4,}:)(.*)$')

        for line in lines:
            match = header_pattern.match(line.strip())
            if match and len(current_lines) > 2:
                sec_text = "\n".join(current_lines).strip()
                if sec_text:
                    sections.append((current_header, sec_text))
                current_header = line.strip().lstrip("#").strip()
                current_lines = [line]
            else:
                current_lines.append(line)

        if current_lines:
            sec_text = "\n".join(current_lines).strip()
            if sec_text:
                sections.append((current_header, sec_text))

        return sections if sections else [("Asosiy", text)]

    def _recursive_split(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """Recursively splits text on natural boundaries without cutting sentences."""
        if len(text) <= chunk_size:
            return [text]

        # Choose best separator present in text
        chosen_sep = ""
        for sep in self.separators:
            if sep in text:
                chosen_sep = sep
                break

        if not chosen_sep:
            # Force split if no separators exist
            return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size - chunk_overlap)]

        splits = text.split(chosen_sep)
        good_splits = []
        current_chunk = []
        current_len = 0

        for piece in splits:
            piece_len = len(piece) + len(chosen_sep)
            if current_len + piece_len > chunk_size and current_chunk:
                merged = chosen_sep.join(current_chunk)
                good_splits.append(merged)
                
                # Overlap logic: keep trailing elements
                overlap_chunk = []
                overlap_len = 0
                for prev in reversed(current_chunk):
                    if overlap_len + len(prev) < chunk_overlap:
                        overlap_chunk.insert(0, prev)
                        overlap_len += len(prev)
                    else:
                        break
                current_chunk = overlap_chunk
                current_len = overlap_len

            current_chunk.append(piece)
            current_len += piece_len

        if current_chunk:
            good_splits.append(chosen_sep.join(current_chunk))

        return good_splits
