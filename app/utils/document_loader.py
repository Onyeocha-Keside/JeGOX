import PyPDF2
from docx import Document
from typing import List, Dict, Any, Union
import os
from datetime import datetime
from app.core.logger import logger
from app.core.error import DocumentProcessingError
from app.utils.text_splitter import text_splitter

class DocumentLoader:
    """Handles loading and processing of PDF and DOCX files."""
    
    @staticmethod
    def load_pdf(file_path: str) -> str:
        """Extract text from PDF file."""
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except Exception as e:
            logger.error(f"Error processing PDF {file_path}: {e}")
            raise DocumentProcessingError(f"Failed to process PDF: {str(e)}")

    @staticmethod
    def load_docx(file_path: str) -> str:
        """Extract text from DOCX file."""
        try:
            doc = Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except Exception as e:
            logger.error(f"Error processing DOCX {file_path}: {e}")
            raise DocumentProcessingError(f"Failed to process DOCX: {str(e)}")

    @classmethod
    def process_document(
        cls,
        file_path: str,
        metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Union[str, Dict[str, Any]]]]:
        """
        Process a document and return chunks with metadata.
        
        Args:
            file_path: Path to the document
            metadata: Additional metadata to include
            
        Returns:
            List of dicts containing text chunks and metadata
        """
        try:
            # Extract file information
            file_name = os.path.basename(file_path)
            file_ext = os.path.splitext(file_name)[1].lower()
            
            # Basic metadata
            base_metadata = {
                'file_name': file_name,
                'file_type': file_ext,
                'processed_date': datetime.now().isoformat(),
                'file_path': file_path
            }
            
            # Merge with provided metadata
            if metadata:
                base_metadata.update(metadata)
            
            # Extract text based on file type
            if file_ext == '.pdf':
                text = cls.load_pdf(file_path)
            elif file_ext in ['.docx', '.doc']:
                text = cls.load_docx(file_path)
            else:
                raise DocumentProcessingError(f"Unsupported file type: {file_ext}")
            
            # Split text into chunks with metadata
            chunks = text_splitter.create_chunks_with_metadata(text, base_metadata)
            
            logger.info(f"Successfully processed {file_name} into {len(chunks)} chunks")
            return chunks
            
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {e}")
            raise DocumentProcessingError(f"Document processing failed: {str(e)}")

document_loader = DocumentLoader()