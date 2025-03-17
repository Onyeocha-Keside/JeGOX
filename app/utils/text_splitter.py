from typing import List
from app.core.logger import logger

class TextSplitter:
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separator: str = "\n"
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separator = separator

    def split_text(self, text: str) -> List[str]:
        """
        Split text into overlapping chunks.
        
        Args:
            text: Text to split
            
        Returns:
            List of text chunks
        """
        try:
            # Split text into paragraphs
            paragraphs = text.split(self.separator)
            chunks = []
            current_chunk = []
            current_size = 0
            
            for paragraph in paragraphs:
                paragraph = paragraph.strip()
                if not paragraph:
                    continue
                    
                # If paragraph is longer than chunk_size, split it
                if len(paragraph) > self.chunk_size:
                    if current_chunk:
                        chunks.append(self.separator.join(current_chunk))
                        current_chunk = []
                        current_size = 0
                    
                    # Split long paragraph
                    words = paragraph.split()
                    temp_chunk = []
                    temp_size = 0
                    
                    for word in words:
                        if temp_size + len(word) + 1 > self.chunk_size:
                            chunks.append(" ".join(temp_chunk))
                            # Keep overlap
                            overlap_words = temp_chunk[-self.chunk_overlap:]
                            temp_chunk = overlap_words + [word]
                            temp_size = sum(len(w) + 1 for w in temp_chunk)
                        else:
                            temp_chunk.append(word)
                            temp_size += len(word) + 1
                    
                    if temp_chunk:
                        chunks.append(" ".join(temp_chunk))
                    continue
                
                # Handle normal paragraphs
                if current_size + len(paragraph) + 1 > self.chunk_size:
                    chunks.append(self.separator.join(current_chunk))
                    # Keep overlap
                    overlap_start = max(0, len(current_chunk) - self.chunk_overlap)
                    current_chunk = current_chunk[overlap_start:] + [paragraph]
                    current_size = sum(len(c) + 1 for c in current_chunk)
                else:
                    current_chunk.append(paragraph)
                    current_size += len(paragraph) + 1
            
            if current_chunk:
                chunks.append(self.separator.join(current_chunk))
            
            return chunks
            
        except Exception as e:
            logger.error(f"Error splitting text: {e}")
            raise ValueError(f"Failed to split text: {str(e)}")

    def create_chunks_with_metadata(
        self, 
        text: str, 
        metadata: dict
    ) -> List[dict]:
        """
        Create chunks with associated metadata.
        
        Args:
            text: Text to split
            metadata: Metadata to attach to each chunk
            
        Returns:
            List of dicts containing chunks and metadata
        """
        chunks = self.split_text(text)
        return [
            {
                'text': chunk,
                'metadata': {
                    **metadata,
                    'chunk_index': i,
                    'total_chunks': len(chunks)
                }
            }
            for i, chunk in enumerate(chunks)
        ]

text_splitter = TextSplitter()