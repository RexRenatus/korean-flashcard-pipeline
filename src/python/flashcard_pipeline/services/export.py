"""Export service for generating various output formats"""

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import io

from ..core.models import ExportFormat, FlashcardRow
from ..core.processing_models import ProcessingResult
from ..core.exceptions import ExportError

logger = logging.getLogger(__name__)


class ExportService:
    """Service for exporting flashcards to various formats"""
    
    def __init__(self):
        self.formatters = {
            ExportFormat.TSV: self._format_tsv,
            ExportFormat.CSV: self._format_csv,
            ExportFormat.JSON: self._format_json,
            ExportFormat.ANKI: self._format_anki,
            ExportFormat.MARKDOWN: self._format_markdown,
            ExportFormat.HTML: self._format_html,
            ExportFormat.PDF: self._format_pdf,
        }
    
    def export(
        self,
        results: List[ProcessingResult],
        format: ExportFormat,
        output_path: Optional[Union[str, Path]] = None,
        **options
    ) -> Union[str, bytes]:
        """
        Export processing results to specified format.
        
        Args:
            results: List of processing results to export
            format: Export format
            output_path: Optional path to save output
            **options: Format-specific options
            
        Returns:
            Formatted output as string or bytes
        """
        if format not in self.formatters:
            raise ExportError(f"Unsupported export format: {format}")
        
        # Generate formatted output
        output = self.formatters[format](results, **options)
        
        # Save to file if path provided
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            mode = 'wb' if isinstance(output, bytes) else 'w'
            encoding = None if isinstance(output, bytes) else 'utf-8'
            
            with open(output_path, mode, encoding=encoding) as f:
                f.write(output)
        
        return output
    
    def _format_tsv(
        self,
        results: List[ProcessingResult],
        include_header: bool = True,
        **options
    ) -> str:
        """Format as TSV"""
        output = io.StringIO()
        
        # Define columns
        columns = [
            "position", "term", "term_number", "tab_name",
            "primer", "front", "back", "tags", "honorific_level"
        ]
        
        writer = csv.DictWriter(output, fieldnames=columns, delimiter='\t')
        
        if include_header:
            writer.writeheader()
        
        # Write rows
        position = 1
        for result in results:
            if not result.stage2_output:
                continue
                
            for flashcard in result.stage2_output.rows:
                row = self._flashcard_to_row(
                    flashcard, result.term, position, result.term_number
                )
                writer.writerow(row)
                position += 1
        
        return output.getvalue()
    
    def _format_csv(
        self,
        results: List[ProcessingResult],
        include_header: bool = True,
        **options
    ) -> str:
        """Format as CSV"""
        output = io.StringIO()
        
        columns = [
            "position", "term", "term_number", "tab_name",
            "primer", "front", "back", "tags", "honorific_level"
        ]
        
        writer = csv.DictWriter(output, fieldnames=columns, delimiter=',')
        
        if include_header:
            writer.writeheader()
        
        position = 1
        for result in results:
            if not result.stage2_output:
                continue
                
            for flashcard in result.stage2_output.rows:
                row = self._flashcard_to_row(
                    flashcard, result.term, position, result.term_number
                )
                writer.writerow(row)
                position += 1
        
        return output.getvalue()
    
    def _format_json(
        self,
        results: List[ProcessingResult],
        pretty: bool = True,
        **options
    ) -> str:
        """Format as JSON"""
        data = {
            "export_date": datetime.now().isoformat(),
            "total_terms": len(results),
            "total_flashcards": sum(
                len(r.stage2_output.flashcards) if r.stage2_output else 0
                for r in results
            ),
            "flashcards": []
        }
        
        position = 1
        for result in results:
            if not result.stage2_output:
                continue
                
            for flashcard in result.stage2_output.rows:
                data["flashcards"].append({
                    "position": position,
                    "term": result.term,
                    "term_number": result.term_number,
                    "tab_name": flashcard.tab_name,
                    "primer": flashcard.primer,
                    "front": flashcard.front,
                    "back": flashcard.back,
                    "tags": flashcard.tags.split(",") if flashcard.tags else [],
                    "honorific_level": flashcard.honorific_level,
                    "metadata": {
                        "tab_name": flashcard.tab_name,
                        "created_at": datetime.now().isoformat()
                    }
                })
                position += 1
        
        if pretty:
            return json.dumps(data, indent=2, ensure_ascii=False)
        else:
            return json.dumps(data, ensure_ascii=False)
    
    def _format_anki(
        self,
        results: List[ProcessingResult],
        deck_name: str = "Korean Flashcards",
        **options
    ) -> str:
        """Format for Anki import"""
        output = io.StringIO()
        
        # Anki uses tab-separated format with specific fields
        # Format: front[tab]back[tab]tags
        
        for result in results:
            if not result.stage2_output:
                continue
                
            for flashcard in result.stage2_output.rows:
                # Combine primer and front for Anki front side
                front = f"{flashcard.primer}\n\n{flashcard.front}"
                back = flashcard.back
                
                # Format tags for Anki (space-separated, no special chars)
                tag_list = flashcard.tags.split(",") if flashcard.tags else []
                tags = " ".join(
                    tag.strip().replace(" ", "_").replace(",", "")
                    for tag in tag_list
                )
                
                # Add term info to tags
                tags += f" term:{result.term.replace(' ', '_')}"
                tags += f" tab:{flashcard.tab_name.replace(' ', '_')}"
                
                # Write line
                output.write(f"{front}\t{back}\t{tags}\n")
        
        return output.getvalue()
    
    def _format_markdown(
        self,
        results: List[ProcessingResult],
        include_toc: bool = True,
        **options
    ) -> str:
        """Format as Markdown"""
        output = io.StringIO()
        
        # Header
        output.write("# Korean Language Flashcards\n\n")
        output.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Statistics
        total_terms = len(results)
        total_cards = sum(
            len(r.stage2_output.flashcards) if r.stage2_output else 0
            for r in results
        )
        output.write(f"**Total Terms:** {total_terms}\n")
        output.write(f"**Total Flashcards:** {total_cards}\n\n")
        
        # Table of Contents
        if include_toc and results:
            output.write("## Table of Contents\n\n")
            for i, result in enumerate(results, 1):
                if result.stage2_output:
                    output.write(f"{i}. [{result.term}](#{result.term.lower().replace(' ', '-')})\n")
            output.write("\n")
        
        # Flashcards
        for result in results:
            if not result.stage2_output:
                continue
            
            output.write(f"## {result.term}\n\n")
            
            for j, flashcard in enumerate(result.stage2_output.rows, 1):
                output.write(f"### Card {j}: {flashcard.tab_name}\n\n")
                
                output.write("#### Primer\n")
                output.write(f"{flashcard.primer}\n\n")
                
                output.write("#### Front\n")
                output.write(f"{flashcard.front}\n\n")
                
                output.write("#### Back\n")
                output.write(f"{flashcard.back}\n\n")
                
                if flashcard.tags:
                    tag_list = [tag.strip() for tag in flashcard.tags.split(",") if tag.strip()]
                    output.write("**Tags:** " + ", ".join(tag_list) + "\n\n")
                
                output.write("---\n\n")
        
        return output.getvalue()
    
    def _format_html(
        self,
        results: List[ProcessingResult],
        include_css: bool = True,
        **options
    ) -> str:
        """Format as HTML"""
        output = io.StringIO()
        
        # HTML header
        output.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Korean Language Flashcards</title>
""")
        
        if include_css:
            output.write("""    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .flashcard {
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin: 20px 0;
            padding: 20px;
        }
        .flashcard h3 {
            color: #333;
            margin-top: 0;
        }
        .primer {
            background: #f0f0f0;
            padding: 15px;
            border-radius: 5px;
            margin: 10px 0;
        }
        .front, .back {
            margin: 15px 0;
            padding: 15px;
            border-left: 3px solid #4CAF50;
        }
        .tags {
            color: #666;
            font-size: 0.9em;
        }
        .term-section {
            margin: 40px 0;
        }
        .stats {
            background: #e3f2fd;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 30px;
        }
    </style>
""")
        
        output.write("</head>\n<body>\n")
        
        # Header
        output.write("<h1>Korean Language Flashcards</h1>\n")
        output.write(f"<p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>\n")
        
        # Statistics
        total_terms = len(results)
        total_cards = sum(
            len(r.stage2_output.flashcards) if r.stage2_output else 0
            for r in results
        )
        output.write('<div class="stats">\n')
        output.write(f'<strong>Total Terms:</strong> {total_terms}<br>\n')
        output.write(f'<strong>Total Flashcards:</strong> {total_cards}\n')
        output.write('</div>\n')
        
        # Flashcards
        for result in results:
            if not result.stage2_output:
                continue
            
            output.write(f'<div class="term-section">\n')
            output.write(f'<h2>{result.term}</h2>\n')
            
            for j, flashcard in enumerate(result.stage2_output.rows, 1):
                output.write('<div class="flashcard">\n')
                output.write(f'<h3>Card {j}: {flashcard.tab_name}</h3>\n')
                
                output.write('<div class="primer">\n')
                output.write(f'<strong>Primer:</strong><br>\n{flashcard.primer}\n')
                output.write('</div>\n')
                
                output.write('<div class="front">\n')
                output.write(f'<strong>Front:</strong><br>\n{flashcard.front}\n')
                output.write('</div>\n')
                
                output.write('<div class="back">\n')
                output.write(f'<strong>Back:</strong><br>\n{flashcard.back}\n')
                output.write('</div>\n')
                
                if flashcard.tags:
                    tag_list = [tag.strip() for tag in flashcard.tags.split(",") if tag.strip()]
                    output.write('<p class="tags"><strong>Tags:</strong> ')
                    output.write(', '.join(tag_list))
                    output.write('</p>\n')
                
                output.write('</div>\n')
            
            output.write('</div>\n')
        
        output.write("</body>\n</html>")
        
        return output.getvalue()
    
    def _format_pdf(
        self,
        results: List[ProcessingResult],
        **options
    ) -> bytes:
        """Format as PDF (requires additional dependencies)"""
        try:
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            import io
            
            # Create PDF in memory
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            story = []
            
            # Styles
            styles = getSampleStyleSheet()
            title_style = styles['Title']
            heading_style = styles['Heading1']
            subheading_style = styles['Heading2']
            body_style = styles['Normal']
            
            # Title
            story.append(Paragraph("Korean Language Flashcards", title_style))
            story.append(Spacer(1, 0.3*inch))
            
            # Date and stats
            story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", body_style))
            
            total_terms = len(results)
            total_cards = sum(
                len(r.stage2_output.flashcards) if r.stage2_output else 0
                for r in results
            )
            story.append(Paragraph(f"Total Terms: {total_terms}", body_style))
            story.append(Paragraph(f"Total Flashcards: {total_cards}", body_style))
            story.append(Spacer(1, 0.5*inch))
            
            # Flashcards
            for result in results:
                if not result.stage2_output:
                    continue
                
                story.append(Paragraph(result.term, heading_style))
                story.append(Spacer(1, 0.2*inch))
                
                for j, flashcard in enumerate(result.stage2_output.rows, 1):
                    story.append(Paragraph(f"Card {j}: {flashcard.tab_name}", subheading_style))
                    story.append(Spacer(1, 0.1*inch))
                    
                    story.append(Paragraph("<b>Primer:</b>", body_style))
                    story.append(Paragraph(flashcard.primer, body_style))
                    story.append(Spacer(1, 0.1*inch))
                    
                    story.append(Paragraph("<b>Front:</b>", body_style))
                    story.append(Paragraph(flashcard.front, body_style))
                    story.append(Spacer(1, 0.1*inch))
                    
                    story.append(Paragraph("<b>Back:</b>", body_style))
                    story.append(Paragraph(flashcard.back, body_style))
                    story.append(Spacer(1, 0.1*inch))
                    
                    if flashcard.tags:
                        tag_list = [tag.strip() for tag in flashcard.tags.split(",") if tag.strip()]
                        story.append(Paragraph(f"<b>Tags:</b> {', '.join(tag_list)}", body_style))
                    
                    story.append(Spacer(1, 0.3*inch))
                
                story.append(PageBreak())
            
            # Build PDF
            doc.build(story)
            pdf_data = buffer.getvalue()
            buffer.close()
            
            return pdf_data
            
        except ImportError:
            raise ExportError(
                "PDF export requires reportlab library. "
                "Install with: pip install reportlab"
            )
    
    def _flashcard_to_row(
        self,
        flashcard: FlashcardRow,
        term: str,
        position: int,
        term_number: int
    ) -> Dict[str, Any]:
        """Convert flashcard to row format"""
        return {
            "position": position,
            "term": term,
            "term_number": term_number,
            "tab_name": flashcard.tab_name,
            "primer": flashcard.primer,
            "front": flashcard.front,
            "back": flashcard.back,
            "tags": flashcard.tags,
            "honorific_level": flashcard.honorific_level or ""
        }
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported export formats"""
        return [fmt.value for fmt in ExportFormat]
    
    def validate_format(self, format: str) -> bool:
        """Check if format is supported"""
        try:
            ExportFormat(format)
            return True
        except ValueError:
            return False


# Factory function
def create_export_service() -> ExportService:
    """Create export service instance"""
    return ExportService()