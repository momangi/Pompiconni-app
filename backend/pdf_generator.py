"""
PDF Generator for Poppiconni Books
Generates high-quality A4 PDFs with text + images per scene
"""

import io
import re
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.colors import Color, white, black, lightgrey, gray
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem, Image as RLImage, PageBreak
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from PIL import Image as PILImage
import logging

logger = logging.getLogger(__name__)

# Page dimensions
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 2 * cm
CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN
CONTENT_HEIGHT = PAGE_HEIGHT - 2 * MARGIN

# Copyright texts
COPYRIGHT_SHORT = "© Poppiconni®"
COPYRIGHT_FULL = """© Poppiconni® – Tutti i diritti riservati.
Testi, illustrazioni e contenuti sono protetti da copyright.
È vietata la riproduzione, distribuzione o utilizzo non autorizzato,
totale o parziale, senza consenso scritto del titolare del marchio.
Poppiconni® è un marchio tutelato."""

# Font size mapping (TipTap classes to points)
FONT_SIZE_MAP = {
    'font-size-s': 10,
    'font-size-m': 12,
    'font-size-l': 15,
}
DEFAULT_FONT_SIZE = 12

# Alignment mapping
ALIGNMENT_MAP = {
    'text-left': TA_LEFT,
    'text-center': TA_CENTER,
    'text-right': TA_RIGHT,
}


def parse_tiptap_html_to_flowables(html: str, styles: dict) -> list:
    """
    Convert TipTap HTML to ReportLab flowables.
    Supported tags: p, br, ul, li, strong, em, span
    Supported classes: text-left, text-center, text-right, font-size-s/m/l
    """
    if not html or not html.strip():
        return [Paragraph("<i>Testo non disponibile</i>", styles['normal'])]
    
    flowables = []
    
    # Split by paragraphs
    # Pattern to match <p> tags with their content
    p_pattern = r'<p[^>]*>(.*?)</p>'
    ul_pattern = r'<ul[^>]*>(.*?)</ul>'
    
    # Process the HTML sequentially
    remaining = html
    
    while remaining:
        # Find next tag
        p_match = re.search(p_pattern, remaining, re.DOTALL | re.IGNORECASE)
        ul_match = re.search(ul_pattern, remaining, re.DOTALL | re.IGNORECASE)
        
        if not p_match and not ul_match:
            break
            
        # Determine which comes first
        p_pos = p_match.start() if p_match else float('inf')
        ul_pos = ul_match.start() if ul_match else float('inf')
        
        if p_pos < ul_pos and p_match:
            # Process paragraph
            full_match = p_match.group(0)
            content = p_match.group(1)
            
            # Extract classes from <p> tag
            class_match = re.search(r'class="([^"]*)"', full_match)
            classes = class_match.group(1).split() if class_match else []
            
            # Determine style
            font_size = DEFAULT_FONT_SIZE
            alignment = TA_LEFT
            
            for cls in classes:
                if cls in FONT_SIZE_MAP:
                    font_size = FONT_SIZE_MAP[cls]
                if cls in ALIGNMENT_MAP:
                    alignment = ALIGNMENT_MAP[cls]
            
            # Create custom style
            custom_style = ParagraphStyle(
                f'custom_{len(flowables)}',
                parent=styles['normal'],
                fontSize=font_size,
                leading=font_size * 1.4,
                alignment=alignment,
                spaceAfter=8,
            )
            
            # Convert content formatting
            content = convert_inline_formatting(content)
            
            if content.strip():
                flowables.append(Paragraph(content, custom_style))
            
            remaining = remaining[p_match.end():]
            
        elif ul_match:
            # Process unordered list
            list_content = ul_match.group(1)
            li_items = re.findall(r'<li[^>]*>(.*?)</li>', list_content, re.DOTALL | re.IGNORECASE)
            
            if li_items:
                bullet_items = []
                for item in li_items:
                    item_text = convert_inline_formatting(item)
                    bullet_items.append(ListItem(Paragraph(item_text, styles['list_item']), bulletColor=black))
                
                flowables.append(ListFlowable(
                    bullet_items,
                    bulletType='bullet',
                    start='•',
                    leftIndent=15,
                    bulletFontSize=10,
                ))
            
            remaining = remaining[ul_match.end():]
        else:
            break
    
    if not flowables:
        # Fallback: treat as plain text
        plain_text = re.sub(r'<[^>]+>', '', html)
        if plain_text.strip():
            flowables.append(Paragraph(plain_text, styles['normal']))
        else:
            flowables.append(Paragraph("<i>Testo non disponibile</i>", styles['normal']))
    
    return flowables


def convert_inline_formatting(text: str) -> str:
    """Convert HTML inline tags to ReportLab markup"""
    # Convert <strong> to <b>
    text = re.sub(r'<strong>(.*?)</strong>', r'<b>\1</b>', text, flags=re.DOTALL | re.IGNORECASE)
    # Convert <em> to <i>
    text = re.sub(r'<em>(.*?)</em>', r'<i>\1</i>', text, flags=re.DOTALL | re.IGNORECASE)
    # Convert <br> and <br/> to line breaks
    text = re.sub(r'<br\s*/?>', '<br/>', text, flags=re.IGNORECASE)
    # Remove <span> tags (keep content)
    text = re.sub(r'<span[^>]*>(.*?)</span>', r'\1', text, flags=re.DOTALL | re.IGNORECASE)
    # Remove any remaining unsupported tags
    text = re.sub(r'<(?!b>|/b>|i>|/i>|br/>)[^>]+>', '', text)
    
    return text.strip()


def create_faded_image(image_data: bytes, opacity: float = 0.15) -> io.BytesIO:
    """
    Create a faded version of an image for background use.
    Uses PIL to apply transparency.
    """
    try:
        img = PILImage.open(io.BytesIO(image_data))
        
        # Convert to RGBA if not already
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Create white overlay with alpha
        overlay = PILImage.new('RGBA', img.size, (255, 255, 255, int(255 * (1 - opacity))))
        
        # Composite
        faded = PILImage.alpha_composite(img, overlay)
        
        # Convert back to RGB for PDF
        faded_rgb = faded.convert('RGB')
        
        output = io.BytesIO()
        faded_rgb.save(output, format='PNG', quality=95)
        output.seek(0)
        return output
    except Exception as e:
        logger.error(f"Error creating faded image: {e}")
        return None


def fit_image_to_area(image_data: bytes, max_width: float, max_height: float) -> tuple:
    """
    Calculate dimensions to fit image in area while maintaining aspect ratio.
    Returns (width, height) in points.
    """
    try:
        img = PILImage.open(io.BytesIO(image_data))
        img_width, img_height = img.size
        
        # Calculate scaling factors
        width_ratio = max_width / img_width
        height_ratio = max_height / img_height
        
        # Use the smaller ratio to fit within bounds
        ratio = min(width_ratio, height_ratio)
        
        return (img_width * ratio, img_height * ratio)
    except Exception as e:
        logger.error(f"Error calculating image dimensions: {e}")
        return (max_width * 0.8, max_height * 0.8)


class BookPDFGenerator:
    """Generates PDF for a book with all scenes"""
    
    def __init__(self, book: dict, scenes: list, get_image_func):
        """
        Args:
            book: Book document from database
            scenes: List of scene documents (sorted by sceneNumber)
            get_image_func: Async function to get image bytes from GridFS by file_id
        """
        self.book = book
        self.scenes = scenes
        self.get_image = get_image_func
        self.styles = self._create_styles()
    
    def _create_styles(self) -> dict:
        """Create paragraph styles for the PDF"""
        base_styles = getSampleStyleSheet()
        
        return {
            'normal': ParagraphStyle(
                'BookNormal',
                parent=base_styles['Normal'],
                fontSize=12,
                leading=16,
                spaceAfter=10,
                fontName='Helvetica',
            ),
            'list_item': ParagraphStyle(
                'BookListItem',
                parent=base_styles['Normal'],
                fontSize=12,
                leading=16,
                fontName='Helvetica',
            ),
            'placeholder': ParagraphStyle(
                'Placeholder',
                parent=base_styles['Normal'],
                fontSize=10,
                textColor=lightgrey,
                alignment=TA_CENTER,
            ),
        }
    
    async def generate(self) -> io.BytesIO:
        """Generate the complete PDF and return as BytesIO"""
        buffer = io.BytesIO()
        
        # Create PDF with custom page drawing
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=MARGIN,
            rightMargin=MARGIN,
            topMargin=MARGIN,
            bottomMargin=MARGIN,
        )
        
        # Build content
        story = []
        
        for scene in self.scenes:
            # LEFT PAGE: Text + Faded Background
            left_page_content = await self._create_left_page(scene)
            story.extend(left_page_content)
            story.append(PageBreak())
            
            # RIGHT PAGE: Line Art
            right_page_content = await self._create_right_page(scene)
            story.extend(right_page_content)
            story.append(PageBreak())
        
        # Remove last PageBreak
        if story and isinstance(story[-1], PageBreak):
            story.pop()
        
        # Build PDF
        doc.build(story)
        
        buffer.seek(0)
        return buffer
    
    async def _create_left_page(self, scene: dict) -> list:
        """Create left page content: text + faded background image"""
        flowables = []
        
        # Get colored image for background (if available)
        colored_image_id = scene.get('coloredImageFileId')
        bg_image_data = None
        
        if colored_image_id:
            try:
                bg_image_data = await self.get_image(colored_image_id)
            except Exception as e:
                logger.warning(f"Could not load colored image: {e}")
        
        # If we have a background image, create faded version
        if bg_image_data:
            faded = create_faded_image(bg_image_data, opacity=0.12)
            if faded:
                # Calculate size to cover the content area
                img_width, img_height = fit_image_to_area(
                    bg_image_data, CONTENT_WIDTH, CONTENT_HEIGHT * 0.5
                )
                
                try:
                    bg_img = RLImage(faded, width=img_width, height=img_height)
                    bg_img.hAlign = 'CENTER'
                    flowables.append(bg_img)
                    flowables.append(Spacer(1, 10))
                except Exception as e:
                    logger.warning(f"Could not add background image: {e}")
        
        # Parse and add text content
        text_html = scene.get('text', {}).get('html', '')
        text_flowables = parse_tiptap_html_to_flowables(text_html, self.styles)
        flowables.extend(text_flowables)
        
        # If no background image was added, add note
        if not bg_image_data:
            flowables.append(Spacer(1, 20))
            flowables.append(Paragraph(
                f"<font color='lightgrey'>Scena {scene.get('sceneNumber', '?')}</font>",
                self.styles['placeholder']
            ))
        
        return flowables
    
    async def _create_right_page(self, scene: dict) -> list:
        """Create right page content: line art image full page"""
        flowables = []
        
        lineart_image_id = scene.get('lineArtImageFileId')
        
        if lineart_image_id:
            try:
                img_data = await self.get_image(lineart_image_id)
                
                # Fit image to page content area
                img_width, img_height = fit_image_to_area(
                    img_data, CONTENT_WIDTH, CONTENT_HEIGHT
                )
                
                img = RLImage(io.BytesIO(img_data), width=img_width, height=img_height)
                img.hAlign = 'CENTER'
                
                # Center vertically with spacer
                vertical_space = (CONTENT_HEIGHT - img_height) / 2
                if vertical_space > 0:
                    flowables.append(Spacer(1, vertical_space))
                
                flowables.append(img)
                
            except Exception as e:
                logger.warning(f"Could not load line art image: {e}")
                flowables.append(Spacer(1, CONTENT_HEIGHT / 3))
                flowables.append(Paragraph(
                    "<font color='lightgrey'>Immagine non disponibile</font>",
                    self.styles['placeholder']
                ))
        else:
            # Placeholder for missing image
            flowables.append(Spacer(1, CONTENT_HEIGHT / 3))
            flowables.append(Paragraph(
                "<font color='lightgrey'>Immagine da colorare non disponibile</font>",
                self.styles['placeholder']
            ))
            flowables.append(Paragraph(
                f"<font color='lightgrey'>Scena {scene.get('sceneNumber', '?')}</font>",
                self.styles['placeholder']
            ))
        
        return flowables


async def generate_book_pdf(book: dict, scenes: list, get_image_func) -> io.BytesIO:
    """
    Main entry point for PDF generation.
    
    Args:
        book: Book document
        scenes: List of scenes sorted by sceneNumber
        get_image_func: Async function(file_id) -> bytes to get images from GridFS
    
    Returns:
        BytesIO buffer containing the PDF
    """
    generator = BookPDFGenerator(book, scenes, get_image_func)
    return await generator.generate()
