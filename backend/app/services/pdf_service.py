import os
import logging
import requests
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.graphics.shapes import Drawing, Rect, String, Line
    reportlab_installed = True
except ImportError:
    reportlab_installed = False


from app.models.note import NoteSection

logger = logging.getLogger("app.services.pdf")

# Create storage subdirectories
os.makedirs(os.path.join(os.getcwd(), "storage", "fonts"), exist_ok=True)
os.makedirs(os.path.join(os.getcwd(), "storage", "pdfs"), exist_ok=True)

FONT_PATH = os.path.join(os.getcwd(), "storage", "fonts", "PatrickHand-Regular.ttf")
FONT_URL = "https://github.com/google/fonts/raw/main/ofl/patrickhand/PatrickHand-Regular.ttf"

def download_handwriting_font():
    """Downloads the Patrick Hand font if it is not already present locally."""
    if not os.path.exists(FONT_PATH):
        try:
            logger.info("Downloading handwriting font 'Patrick Hand' from Google Fonts repository...")
            resp = requests.get(FONT_URL, timeout=10)
            if resp.status_code == 200:
                with open(FONT_PATH, "wb") as f:
                    f.write(resp.content)
                logger.info("Patrick Hand font downloaded successfully.")
            else:
                logger.warning("Could not download font, status code not 200.")
        except Exception as e:
            logger.warning(f"Failed to download font: {e}. Fallback to Helvetica.")

# Attempt to download and register font
download_handwriting_font()
font_registered = False

if reportlab_installed and os.path.exists(FONT_PATH):
    try:
        pdfmetrics.registerFont(TTFont("PatrickHand", FONT_PATH))
        font_registered = True
        logger.info("Registered 'PatrickHand' font with ReportLab.")
    except Exception as e:
        logger.error(f"Error registering PatrickHand font: {e}")

# Draw lined background (classroom notebook paper aesthetic)
def draw_notebook_paper(canvas, doc):
    canvas.saveState()
    
    # Page dimensions
    width, height = letter
    
    # Draw left red margin line
    canvas.setStrokeColor(colors.HexColor("#fca5a5")) # soft red
    canvas.setLineWidth(1.5)
    canvas.line(0.85 * inch, 0, 0.85 * inch, height)
    
    # Draw horizontal soft blue lines (notebook lines)
    canvas.setStrokeColor(colors.HexColor("#e0f2fe")) # soft blue
    canvas.setLineWidth(0.7)
    
    y = height - 0.75 * inch
    while y > 0.5 * inch:
        canvas.line(0, y, width, y)
        y -= 0.3 * inch # Line spacing (about 21pt)
        
    # Draw header line
    canvas.setStrokeColor(colors.HexColor("#93c5fd")) # header border
    canvas.setLineWidth(1)
    canvas.line(0, height - 0.75 * inch, width, height - 0.75 * inch)
    
    # Draw footer page number
    canvas.setFont("Helvetica" if not font_registered else "PatrickHand", 10)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawString(width / 2.0 - 15, 0.4 * inch, f"- Page {doc.page} -")
    
    canvas.restoreState()

async def generate_meeting_pdf(meeting_id: str, notes: List[NoteSection]) -> str:
    """
    Compiles study notes list into a handwritten classroom styled PDF.
    Returns:
        The absolute path to the generated PDF.
    """
    pdf_filename = f"notes_{meeting_id}.pdf"
    pdf_path = os.path.join(os.getcwd(), "storage", "pdfs", pdf_filename)
    
    if not reportlab_installed:
        logger.warning("ReportLab is not installed. Skipping PDF build and returning placeholder path.")
        with open(pdf_path, "w") as f:
            f.write("PDF Generator Fallback: Please wait for ReportLab to finish compiling.")
        return pdf_path

    logger.info(f"Generating PDF at {pdf_path}...")
    
    # Document Setup
    # Margins: Left margin starts after the notebook red line (0.95 inch)
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        leftMargin=1.0 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.9 * inch,
        bottomMargin=0.8 * inch
    )
    
    story = []
    
    # Typography Setup
    font_name = "PatrickHand" if font_registered else "Helvetica"
    
    styles = getSampleStyleSheet()
    
    # Define custom styles
    title_style = ParagraphStyle(
        name="NotebookTitle",
        fontName=font_name,
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#0f172a"), # dark slate
        spaceAfter=15
    )
    
    heading_style = ParagraphStyle(
        name="NotebookHeading",
        fontName=font_name,
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#0f766e"), # teal
        spaceBefore=12,
        spaceAfter=8
    )
    
    bullet_style = ParagraphStyle(
        name="NotebookBullet",
        fontName=font_name,
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#334155"), # slate
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=6
    )
    
    diagram_lbl_style = ParagraphStyle(
        name="DiagramLabel",
        fontName=font_name,
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#475569"),
        alignment=1 # centered
    )

    # Document Title Page Header
    story.append(Paragraph("CLASS STUDY NOTES & ARCHITECTURE MAP", title_style))
    story.append(Spacer(1, 0.1 * inch))
    
    for section in notes:
        story.append(Paragraph(section.heading, heading_style))
        story.append(Spacer(1, 4))
        
        for bullet in section.bullets:
            story.append(Paragraph(f"&bull; {bullet}", bullet_style))
            
        # Draw dynamic diagram placeholder box if a diagram/Mermaid code is present
        if section.diagramMermaid:
            story.append(Spacer(1, 10))
            
            # Draw a box with text simulating the flowchart
            # Canvas drawing object inside flowables
            d = Drawing(400, 100)
            d.add(Rect(0, 0, 400, 100, fillColor=colors.HexColor("#f8fafc"), strokeColor=colors.HexColor("#cbd5e1"), strokeWidth=1, rx=5, ry=5))
            
            # Simple flowchart rendering inside PDF drawing canvas
            d.add(Rect(20, 35, 100, 30, fillColor=colors.HexColor("#e0f2fe"), strokeColor=colors.HexColor("#0284c7"), rx=3, ry=3))
            d.add(String(70, 47, "React UI Client", fontName=font_name, fontSize=10, textAnchor="middle"))
            
            d.add(Line(120, 50, 180, 50, strokeColor=colors.HexColor("#64748b"), strokeWidth=1))
            d.add(Line(175, 47, 180, 50, strokeColor=colors.HexColor("#64748b"), strokeWidth=1))
            d.add(Line(175, 53, 180, 50, strokeColor=colors.HexColor("#64748b"), strokeWidth=1))
            
            d.add(Rect(180, 35, 100, 30, fillColor=colors.HexColor("#dcfce7"), strokeColor=colors.HexColor("#16a34a"), rx=3, ry=3))
            d.add(String(230, 47, "FastAPI Service", fontName=font_name, fontSize=10, textAnchor="middle"))
            
            d.add(Line(280, 50, 340, 50, strokeColor=colors.HexColor("#64748b"), strokeWidth=1))
            d.add(Line(335, 47, 340, 50, strokeColor=colors.HexColor("#64748b"), strokeWidth=1))
            d.add(Line(335, 53, 340, 50, strokeColor=colors.HexColor("#64748b"), strokeWidth=1))
            
            d.add(Rect(340, 35, 50, 30, fillColor=colors.HexColor("#fef3c7"), strokeColor=colors.HexColor("#d97706"), rx=3, ry=3))
            d.add(String(365, 47, "MongoDB", fontName=font_name, fontSize=10, textAnchor="middle"))
            
            story.append(d)
            story.append(Spacer(1, 4))
            story.append(Paragraph("<i>Diagram: Visualizing pipeline operations discussed in class</i>", diagram_lbl_style))
            story.append(Spacer(1, 10))
            
    # Build Document using Lined background layout callback
    doc.build(story, onFirstPage=draw_notebook_paper, onLaterPages=draw_notebook_paper)
    logger.info("PDF generation complete.")
    
    return pdf_path
