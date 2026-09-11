"""PDF Study Kit — turn a PDF into study material, entirely offline."""
from .extract import extract, Document, Section, ExtractionError
from .generate import build, FORMATS
from .analyze import tf_idf, summarize, definitions

__version__ = "1.0.0"
__all__ = ["extract", "build", "Document", "Section", "ExtractionError",
           "FORMATS", "tf_idf", "summarize", "definitions", "__version__"]
