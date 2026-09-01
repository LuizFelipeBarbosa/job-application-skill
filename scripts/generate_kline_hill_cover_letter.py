from pathlib import Path

from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


OUTPUT = Path(
    "/Users/lfpmb/Documents/Job-Applications/private/documents/tailored/"
    "Kline_Hill_Partners_Deal_Team_Analyst_2027_Cover_Letter.pdf"
)


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    pdfmetrics.registerFont(TTFont("Arial", "/System/Library/Fonts/Supplemental/Arial.ttf"))
    pdfmetrics.registerFont(TTFont("Arial-Bold", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"))

    document = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=LETTER,
        rightMargin=0.78 * inch,
        leftMargin=0.78 * inch,
        topMargin=0.62 * inch,
        bottomMargin=0.62 * inch,
        title="Kline Hill Partners Deal Team Analyst Cover Letter",
        author="Luiz Felipe Barbosa",
    )

    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontName="Arial",
        fontSize=10.2,
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
            "150 Columbus Ave, New York, NY 10023 &nbsp;|&nbsp; +1 (347) 449-4034 &nbsp;|&nbsp; "
            "luizfelipepmbarbosa@gmail.com &nbsp;|&nbsp; linkedin.com/in/luiz-felipe-barbosa-5989a9294",
            contact,
        ),
        Paragraph("August 24, 2026", body),
        Spacer(1, 2),
        Paragraph("Hiring Team<br/>Kline Hill Partners<br/>Greenwich, Connecticut", body),
        Spacer(1, 3),
        Paragraph("Dear Kline Hill Partners Hiring Team:", body),
        Paragraph(
            "I am excited to apply for the Deal Team Analyst position. I am completing dual B.A. degrees "
            "in Applied Mathematics (Statistics) and Media Studies at the University of California, Berkeley "
            "in December 2026, and I would be available to begin in January 2027. Kline Hill's disciplined focus "
            "on the less efficient, small-deal segment of the secondary market is especially compelling to me. "
            "The role's combination of company and fund research, portfolio modeling, valuation, and investment "
            "committee preparation closely matches the analytical investment work I have pursued.",
            body,
        ),
        Paragraph(
            "At Base Partners, I conducted market research and financial analysis across fintech, SaaS, and "
            "consumer companies, led expert interviews, analyzed online consumer sentiment, and synthesized "
            "findings into investment memos for partners. At Industry Ventures, I built an automated "
            "topic-modeling and visualization pipeline spanning more than 150,000 historical deal memos and "
            "developed semantic-search tools that supported diligence across thousands of documents. These "
            "experiences strengthened my ability to structure ambiguous questions, assess large and varied "
            "information sets, and communicate concise, decision-ready conclusions.",
            body,
        ),
        Paragraph(
            "I would bring the same rigor, attention to detail, and ownership to Kline Hill's deal teams. My "
            "quantitative coursework has built a strong statistical foundation, while my investing experience "
            "has taught me to connect models and market evidence to the key drivers of risk and value. As a "
            "founding engineer of Earplug, I also helped take a product from concept to deployment and supported "
            "a winning pitch, which reinforced the importance of clear communication and dependable execution "
            "in a small, entrepreneurial team.",
            body,
        ),
        Paragraph(
            "Thank you for considering my application. I would welcome the opportunity to discuss how my "
            "investment research, data analysis, and collaborative problem-solving experience could contribute "
            "to Kline Hill Partners.",
            body,
        ),
        Spacer(1, 4),
        Paragraph("Sincerely,<br/><br/>Luiz Felipe Barbosa", body),
    ]
    document.build(story)


if __name__ == "__main__":
    main()
