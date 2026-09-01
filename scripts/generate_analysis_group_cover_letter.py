from pathlib import Path

from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


OUTPUT = Path(
    "/Users/lfpmb/Documents/Job-Applications/private/documents/tailored/"
    "Analysis_Group_Analyst_Generalist_2027_Cover_Letter.pdf"
)


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    pdfmetrics.registerFont(
        TTFont("Arial", "/System/Library/Fonts/Supplemental/Arial.ttf")
    )
    pdfmetrics.registerFont(
        TTFont("Arial-Bold", "/System/Library/Fonts/Supplemental/Arial Bold.ttf")
    )

    document = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=LETTER,
        rightMargin=0.78 * inch,
        leftMargin=0.78 * inch,
        topMargin=0.62 * inch,
        bottomMargin=0.62 * inch,
        title="Analysis Group Analyst - Generalist Cover Letter",
        author="Luiz Felipe Barbosa",
    )

    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontName="Arial",
        fontSize=10.3,
        leading=14.2,
        alignment=TA_LEFT,
        spaceAfter=9,
    )
    header = ParagraphStyle(
        "Header",
        parent=body,
        fontName="Arial-Bold",
        fontSize=15,
        leading=18,
        spaceAfter=2,
    )
    contact = ParagraphStyle(
        "Contact",
        parent=body,
        fontSize=9.2,
        leading=12,
        textColor="#333333",
        spaceAfter=12,
    )

    story = [
        Paragraph("Luiz Felipe Barbosa", header),
        Paragraph(
            "Berkeley, CA &nbsp;|&nbsp; +1 (347) 449-4034 &nbsp;|&nbsp; "
            "luizfelipepmbarbosa@gmail.com &nbsp;|&nbsp; lfpmb.com",
            contact,
        ),
        Paragraph("August 25, 2026", body),
        Spacer(1, 2),
        Paragraph("Analysis Group Recruiting Team", body),
        Spacer(1, 3),
        Paragraph("Dear Analysis Group Recruiting Team:", body),
        Paragraph(
            "I am applying for the Analyst - Generalist position beginning in 2027. My geographic "
            "preferences are San Francisco, New York, Washington, DC, and Chicago. I expect to complete "
            "bachelor's degrees in Applied Mathematics, with a Statistics focus, and Media Studies, with "
            "a Media Law and Policy focus, at UC Berkeley in December 2026.",
            body,
        ),
        Paragraph(
            "Analysis Group's combination of rigorous quantitative analysis and consequential business, "
            "financial, regulatory, and litigation work strongly appeals to me. I am particularly interested "
            "in the opportunity to apply statistical methods and programming to real-world questions while "
            "contributing to qualitative research, expert reports, and client-facing analysis across multiple "
            "practices.",
            body,
        ),
        Paragraph(
            "As a Data Science Intern at Industry Ventures, I built analytical workflows using topic modeling "
            "across more than 150,000 historical deal memos, developed semantic-search tools spanning thousands "
            "of venture-capital documents, and integrated document-extraction systems into due-diligence "
            "workflows. At Base Partners, I conducted hypothesis-driven market research and financial analysis "
            "across fintech, SaaS, and consumer companies, performed expert interviews and sentiment analysis, "
            "and synthesized findings into investment memos. My independent prediction-market research has "
            "further developed my experience with Python, pandas, statsmodels, quantitative modeling, and data "
            "visualization.",
            body,
        ),
        Paragraph(
            "These experiences have taught me to combine quantitative evidence with careful qualitative "
            "research and communicate complex findings clearly. I would be excited to bring that approach to "
            "Analysis Group's collaborative case teams and continue developing as a rigorous, versatile analyst.",
            body,
        ),
        Paragraph("Thank you for your consideration.", body),
        Spacer(1, 4),
        Paragraph("Sincerely,<br/><br/>Luiz Felipe Barbosa", body),
    ]
    document.build(story)


if __name__ == "__main__":
    main()
