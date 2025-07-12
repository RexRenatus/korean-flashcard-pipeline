"""
PDF Exporter
============

Exports flashcards to PDF format with template support.
Includes Korean font handling and multiple layout options.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import io

try:
    from reportlab.lib.pagesizes import letter, A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, Image, KeepTogether
    )
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("ReportLab not available. PDF export will not work.")

from ..models import ExportConfig
from ..exceptions import ExportError

logger = logging.getLogger(__name__)


class PDFExporter:
    """
    PDF format exporter for flashcards.
    
    Features:
    - Template-based layouts
    - Korean font support
    - Multiple card layouts
    - Print-friendly formatting
    - Index and summary pages
    - Progress tracking
    """
    
    # Available layouts
    LAYOUTS = {
        'cards': 'Flashcard style with front/back',
        'list': 'Simple list format',
        'table': 'Tabular format',
        'study': 'Study sheet with notes',
        'compact': 'Space-saving format'
    }
    
    # Default fonts
    DEFAULT_FONTS = {
        'korean': 'NanumGothic',
        'english': 'Helvetica',
        'mono': 'Courier'
    }
    
    def __init__(
        self,
        font_dir: Optional[Path] = None,
        default_layout: str = 'cards',
        page_size: str = 'A4'
    ):
        """
        Initialize PDF exporter.
        
        Args:
            font_dir: Directory containing font files
            default_layout: Default layout to use
            page_size: Default page size (A4, letter)
        """
        if not REPORTLAB_AVAILABLE:
            raise ImportError("ReportLab is required for PDF export")
        
        self.font_dir = font_dir or Path("fonts")
        self.default_layout = default_layout
        self.page_size = A4 if page_size == 'A4' else letter
        self.styles = getSampleStyleSheet()
        
        # Initialize fonts
        self._initialize_fonts()
        
        # Create custom styles
        self._create_custom_styles()
    
    def _initialize_fonts(self):
        """Initialize Korean fonts for PDF"""
        try:
            # Try to register Korean fonts
            if self.font_dir.exists():
                # Look for common Korean fonts
                font_files = {
                    'NanumGothic': 'NanumGothic.ttf',
                    'MalgunGothic': 'malgun.ttf',
                    'NotoSansKR': 'NotoSansKR-Regular.ttf'
                }
                
                for font_name, font_file in font_files.items():
                    font_path = self.font_dir / font_file
                    if font_path.exists():
                        try:
                            pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
                            self.DEFAULT_FONTS['korean'] = font_name
                            logger.info(f"Registered Korean font: {font_name}")
                            break
                        except Exception as e:
                            logger.warning(f"Failed to register font {font_name}: {e}")
            
        except Exception as e:
            logger.warning(f"Font initialization failed: {e}")
            logger.warning("PDF export will use default fonts (may not display Korean correctly)")
    
    def _create_custom_styles(self):
        """Create custom paragraph styles"""
        # Korean text style
        self.styles.add(ParagraphStyle(
            name='Korean',
            parent=self.styles['Normal'],
            fontName=self.DEFAULT_FONTS['korean'],
            fontSize=14,
            leading=20,
            alignment=TA_LEFT
        ))
        
        # English text style
        self.styles.add(ParagraphStyle(
            name='English',
            parent=self.styles['Normal'],
            fontName=self.DEFAULT_FONTS['english'],
            fontSize=12,
            leading=16,
            alignment=TA_LEFT
        ))
        
        # Card title style
        self.styles.add(ParagraphStyle(
            name='CardTitle',
            parent=self.styles['Heading2'],
            fontName=self.DEFAULT_FONTS['korean'],
            fontSize=16,
            textColor=colors.HexColor('#0066cc'),
            alignment=TA_CENTER
        ))
        
        # Romanization style
        self.styles.add(ParagraphStyle(
            name='Romanization',
            parent=self.styles['Normal'],
            fontName=self.DEFAULT_FONTS['english'],
            fontSize=10,
            textColor=colors.grey,
            alignment=TA_LEFT
        ))
        
        # Tag style
        self.styles.add(ParagraphStyle(
            name='Tags',
            parent=self.styles['Normal'],
            fontName=self.DEFAULT_FONTS['english'],
            fontSize=9,
            textColor=colors.HexColor('#666666'),
            alignment=TA_LEFT
        ))
    
    def export(
        self,
        export_data: Dict[str, Any],
        config: ExportConfig
    ) -> None:
        """
        Export flashcards to PDF file.
        
        Args:
            export_data: Dictionary containing flashcards and metadata
            config: Export configuration
        """
        try:
            flashcards = export_data.get('flashcards', [])
            if not flashcards:
                logger.warning("No flashcards to export")
                return
            
            # Determine layout
            layout = config.template_name or self.default_layout
            if layout not in self.LAYOUTS:
                layout = self.default_layout
            
            # Create PDF document
            doc = SimpleDocTemplate(
                str(config.output_path),
                pagesize=self.page_size,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=18
            )
            
            # Build content
            story = []
            
            # Add title page
            story.extend(self._create_title_page(export_data, config))
            
            # Add content based on layout
            if layout == 'cards':
                story.extend(self._create_card_layout(flashcards))
            elif layout == 'list':
                story.extend(self._create_list_layout(flashcards))
            elif layout == 'table':
                story.extend(self._create_table_layout(flashcards))
            elif layout == 'study':
                story.extend(self._create_study_layout(flashcards))
            elif layout == 'compact':
                story.extend(self._create_compact_layout(flashcards))
            
            # Add summary if configured
            if config.include_metadata:
                story.append(PageBreak())
                story.extend(self._create_summary_page(export_data))
            
            # Build PDF
            doc.build(story)
            
            logger.info(
                f"Exported {len(flashcards)} flashcards to PDF: {config.output_path}"
            )
            
        except Exception as e:
            logger.error(f"PDF export failed: {e}")
            raise ExportError(f"Failed to export PDF file: {e}")
    
    def _create_title_page(
        self,
        export_data: Dict[str, Any],
        config: ExportConfig
    ) -> List:
        """Create title page"""
        story = []
        
        # Title
        title = Paragraph(
            "Korean Language Flashcards",
            self.styles['Title']
        )
        story.append(title)
        story.append(Spacer(1, 0.5 * inch))
        
        # Metadata
        metadata = export_data.get('metadata', {})
        info_text = f"""
        <para>
        Total Cards: {len(export_data.get('flashcards', []))}<br/>
        Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}<br/>
        </para>
        """
        
        info = Paragraph(info_text, self.styles['Normal'])
        story.append(info)
        
        # Add deck info if available
        if decks := export_data.get('decks'):
            story.append(Spacer(1, 0.3 * inch))
            deck_names = ', '.join(d.get('name', 'Unknown') for d in decks)
            deck_info = Paragraph(f"<b>Decks:</b> {deck_names}", self.styles['Normal'])
            story.append(deck_info)
        
        # Add tag summary if available
        if tags := export_data.get('tags'):
            story.append(Spacer(1, 0.3 * inch))
            tag_list = ', '.join(f"{tag} ({count})" for tag, count in tags.items())
            tag_info = Paragraph(f"<b>Tags:</b> {tag_list}", self.styles['Normal'])
            story.append(tag_info)
        
        story.append(PageBreak())
        return story
    
    def _create_card_layout(self, flashcards: List[Dict[str, Any]]) -> List:
        """Create flashcard-style layout"""
        story = []
        
        for idx, flashcard in enumerate(flashcards):
            # Card container
            card_elements = []
            
            # Card number
            card_num = Paragraph(f"Card {idx + 1}", self.styles['Normal'])
            card_elements.append(card_num)
            card_elements.append(Spacer(1, 0.2 * inch))
            
            # Korean text (front)
            korean = Paragraph(
                flashcard.get('korean', ''),
                self.styles['CardTitle']
            )
            card_elements.append(korean)
            
            # Romanization
            if romanization := flashcard.get('romanization'):
                rom_para = Paragraph(romanization, self.styles['Romanization'])
                card_elements.append(rom_para)
            
            card_elements.append(Spacer(1, 0.3 * inch))
            
            # Divider
            card_elements.append(
                Table([['']], colWidths=[6 * inch], style=[
                    ('LINEBELOW', (0, 0), (-1, -1), 1, colors.grey)
                ])
            )
            card_elements.append(Spacer(1, 0.3 * inch))
            
            # English text (back)
            english = Paragraph(
                flashcard.get('english', ''),
                self.styles['English']
            )
            card_elements.append(english)
            
            # Explanation
            if explanation := flashcard.get('explanation'):
                card_elements.append(Spacer(1, 0.2 * inch))
                exp_para = Paragraph(
                    f"<i>{explanation}</i>",
                    self.styles['Normal']
                )
                card_elements.append(exp_para)
            
            # Tags
            if tags := flashcard.get('tags'):
                card_elements.append(Spacer(1, 0.2 * inch))
                tag_text = ' '.join(f"#{tag}" for tag in tags)
                tag_para = Paragraph(tag_text, self.styles['Tags'])
                card_elements.append(tag_para)
            
            # Keep card together
            story.append(KeepTogether(card_elements))
            story.append(Spacer(1, 0.5 * inch))
            
            # Page break every 3 cards
            if (idx + 1) % 3 == 0 and idx < len(flashcards) - 1:
                story.append(PageBreak())
        
        return story
    
    def _create_list_layout(self, flashcards: List[Dict[str, Any]]) -> List:
        """Create simple list layout"""
        story = []
        
        for idx, flashcard in enumerate(flashcards):
            # Format as numbered list
            text = f"""
            <para>
            <b>{idx + 1}. {flashcard.get('korean', '')}</b><br/>
            {flashcard.get('romanization', '')}<br/>
            → {flashcard.get('english', '')}<br/>
            </para>
            """
            
            para = Paragraph(text, self.styles['Normal'])
            story.append(para)
            
            if explanation := flashcard.get('explanation'):
                exp_para = Paragraph(
                    f"<i>{explanation}</i>",
                    self.styles['Normal']
                )
                story.append(exp_para)
            
            story.append(Spacer(1, 0.2 * inch))
        
        return story
    
    def _create_table_layout(self, flashcards: List[Dict[str, Any]]) -> List:
        """Create table layout"""
        story = []
        
        # Prepare table data
        data = [['Korean', 'Romanization', 'English', 'Tags']]
        
        for flashcard in flashcards:
            row = [
                flashcard.get('korean', ''),
                flashcard.get('romanization', ''),
                flashcard.get('english', ''),
                ' '.join(flashcard.get('tags', []))
            ]
            data.append(row)
        
        # Create table
        table = Table(data, colWidths=[2*inch, 1.5*inch, 2*inch, 1.5*inch])
        
        # Style table
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), self.DEFAULT_FONTS['english']),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (0, -1), self.DEFAULT_FONTS['korean']),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
        ]))
        
        story.append(table)
        
        return story
    
    def _create_study_layout(self, flashcards: List[Dict[str, Any]]) -> List:
        """Create study sheet layout with space for notes"""
        story = []
        
        for idx, flashcard in enumerate(flashcards):
            # Two-column layout
            data = [
                ['Korean:', flashcard.get('korean', '')],
                ['Romanization:', flashcard.get('romanization', '')],
                ['English:', flashcard.get('english', '')],
                ['Notes:', ''],
                ['', ''],
                ['', '']
            ]
            
            table = Table(data, colWidths=[1.5*inch, 5*inch])
            table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), self.DEFAULT_FONTS['english']),
                ('FONTNAME', (1, 0), (1, 0), self.DEFAULT_FONTS['korean']),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LINEBELOW', (1, 3), (1, 5), 0.5, colors.grey),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            
            story.append(table)
            story.append(Spacer(1, 0.3 * inch))
            
            # Page break every 4 cards
            if (idx + 1) % 4 == 0 and idx < len(flashcards) - 1:
                story.append(PageBreak())
        
        return story
    
    def _create_compact_layout(self, flashcards: List[Dict[str, Any]]) -> List:
        """Create space-saving compact layout"""
        story = []
        
        # Group flashcards in rows of 2
        for i in range(0, len(flashcards), 2):
            row_data = []
            
            for j in range(2):
                if i + j < len(flashcards):
                    card = flashcards[i + j]
                    cell_content = f"""
                    <b>{card.get('korean', '')}</b><br/>
                    {card.get('english', '')}<br/>
                    <font size="8">{' '.join(card.get('tags', []))}</font>
                    """
                    row_data.append(Paragraph(cell_content, self.styles['Normal']))
                else:
                    row_data.append('')
            
            table = Table([row_data], colWidths=[3.5*inch, 3.5*inch])
            table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ]))
            
            story.append(table)
            story.append(Spacer(1, 0.1 * inch))
        
        return story
    
    def _create_summary_page(self, export_data: Dict[str, Any]) -> List:
        """Create summary page with statistics"""
        story = []
        
        story.append(Paragraph("Export Summary", self.styles['Heading1']))
        story.append(Spacer(1, 0.3 * inch))
        
        # Statistics
        if stats := export_data.get('statistics'):
            stats_text = f"""
            <para>
            <b>Total Cards:</b> {stats.get('total_cards', 0)}<br/>
            <b>Unique Tags:</b> {stats.get('unique_tags', 0)}<br/>
            <b>Average Explanation Length:</b> {stats.get('avg_explanation_length', 0):.0f} characters<br/>
            </para>
            """
            
            story.append(Paragraph(stats_text, self.styles['Normal']))
            
            # Status breakdown
            if status_counts := stats.get('cards_by_status'):
                story.append(Spacer(1, 0.2 * inch))
                story.append(Paragraph("<b>Cards by Status:</b>", self.styles['Normal']))
                
                for status, count in status_counts.items():
                    story.append(Paragraph(f"  • {status}: {count}", self.styles['Normal']))
        
        return story