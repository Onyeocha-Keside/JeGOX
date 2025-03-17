import pytest
from app.utils.document_loader import DocumentLoader
from app.utils.text_splitter import TextSplitter
from app.core.error import DocumentProcessingError
import os
from unittest.mock import mock_open, patch

class TestDocumentProcessing:
    """Test suite for document processing functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.test_text = "This is a test document.\n" * 50
        self.text_splitter = TextSplitter()
        self.document_loader = DocumentLoader()

    def test_text_splitting(self):
        """Test text splitting functionality."""
        chunks = self.text_splitter.split_text(self.test_text)
        
        assert isinstance(chunks, list)
        assert len(chunks) > 0
        assert all(len(chunk) <= self.text_splitter.chunk_size for chunk in chunks)

    def test_text_splitting_with_overlap(self):
        """Test text splitting with overlap."""
        splitter = TextSplitter(chunk_size=100, chunk_overlap=20)
        text = "word " * 30  # Create text with known word count
        chunks = splitter.split_text(text)
        
        # Check for overlap
        if len(chunks) > 1:
            # Get the end of first chunk and start of second chunk
            first_chunk_words = chunks[0].split()[-5:]  # Last 5 words
            second_chunk_words = chunks[1].split()[:5]  # First 5 words
            
            # There should be some overlap
            assert any(word in second_chunk_words for word in first_chunk_words)

    @pytest.mark.asyncio
    async def test_pdf_processing(self):
        """Test PDF document processing."""
        test_pdf_content = b"%PDF-1.4\ntest content"
        mock_pdf_file = mock_open(read_data=test_pdf_content)
        
        with patch("builtins.open", mock_pdf_file):
            with patch("PyPDF2.PdfReader") as mock_pdf_reader:
                # Mock PDF reader
                mock_pdf_reader.return_value.pages = [
                    type("Page", (), {"extract_text": lambda: "Test page content"})()
                ]
                
                text = DocumentLoader.load_pdf("test.pdf")
                assert isinstance(text, str)
                assert len(text) > 0

    @pytest.mark.asyncio
    async def test_docx_processing(self):
        """Test DOCX document processing."""
        with patch("docx.Document") as mock_docx:
            # Mock Document object
            mock_doc = mock_docx.return_value
            mock_doc.paragraphs = [
                type("Paragraph", (), {"text": "Test paragraph"})()
            ]
            
            text = DocumentLoader.load_docx("test.docx")
            assert isinstance(text, str)
            assert len(text) > 0

    def test_create_chunks_with_metadata(self):
        """Test chunk creation with metadata."""
        test_text = "Test document content"
        test_metadata = {"source": "test.pdf", "author": "Test Author"}
        
        chunks = self.text_splitter.create_chunks_with_metadata(
            test_text,
            test_metadata
        )
        
        assert isinstance(chunks, list)
        assert len(chunks) > 0
        for chunk in chunks:
            assert "text" in chunk
            assert "metadata" in chunk
            assert chunk["metadata"]["source"] == "test.pdf"
            assert chunk["metadata"]["author"] == "Test Author"
            assert "chunk_index" in chunk["metadata"]
            assert "total_chunks" in chunk["metadata"]

    def test_invalid_document_type(self):
        """Test processing invalid document type."""
        with pytest.raises(DocumentProcessingError):
            DocumentLoader.process_document("test.invalid")

    def test_empty_document(self):
        """Test processing empty document."""
        with patch("builtins.open", mock_open(read_data="")):
            chunks = self.text_splitter.split_text("")
            assert len(chunks) == 0