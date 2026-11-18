class DocumentChunker:
    """Split documents into tokenizer-aware overlapping chunks."""

    def __init__(
        self,
        tokenizer,
        max_tokens=110,
        overlap_tokens=20,
    ):
        if not tokenizer.is_fast:
            raise ValueError(
                "A fast tokenizer is required for accurate text offsets."
            )

        special_tokens = tokenizer.num_special_tokens_to_add(pair=False)
        content_budget = max_tokens - special_tokens

        if content_budget <= 0:
            raise ValueError("Token budget is too small.")

        if overlap_tokens < 0 or overlap_tokens >= content_budget:
            raise ValueError(
                "Overlap must be smaller than the available content budget."
            )

        self.tokenizer = tokenizer
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.content_budget = content_budget

    def _split_text(self, text):
        encoded = self.tokenizer(
            text,
            add_special_tokens=False,
            return_offsets_mapping=True,
            truncation=False,
        )

        offsets = encoded["offset_mapping"]
        total_tokens = len(offsets)

        if total_tokens == 0:
            return []

        ranges = []
        start_token = 0
        step = self.content_budget - self.overlap_tokens

        while start_token < total_tokens:
            end_token = min(
                start_token + self.content_budget,
                total_tokens,
            )

            char_start = offsets[start_token][0]
            char_end = offsets[end_token - 1][1]

            if char_end <= char_start:
                raise ValueError("Invalid tokenizer character offsets.")

            chunk_text = text[char_start:char_end]

            actual_count = len(
                self.tokenizer.encode(
                    chunk_text,
                    add_special_tokens=True,
                    truncation=False,
                )
            )

            if actual_count > self.max_tokens:
                raise ValueError(
                    f"Chunk exceeds token budget: "
                    f"{actual_count}/{self.max_tokens}."
                )

            ranges.append((char_start, char_end, actual_count))

            if end_token >= total_tokens:
                break

            start_token += step

        return ranges

    def chunk(self, extracted_document):
        chunks = []
        chunk_id = 0

        for page_data in extracted_document["pages"]:
            text = page_data["text"]

            if not text or not text.strip():
                continue

            for start, end, token_count in self._split_text(text):
                chunk_text = text[start:end]

                if not chunk_text.strip():
                    continue

                chunks.append({
                    "chunk_id": chunk_id,
                    "page": page_data["page"],
                    "text": chunk_text,
                    "start_offset": start,
                    "end_offset": end,
                    "token_count": token_count,
                })

                chunk_id += 1

        return chunks
