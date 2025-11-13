"""
Reusable Email Template System for Brikli Notifications

Based on the Brikli brand design with consistent styling across all notification types.
Uses the same professional design as password reset emails.
"""
from typing import Optional, List
from dataclasses import dataclass


@dataclass
class EmailSection:
    """A content section within an email"""
    text: str
    is_bold: bool = False


@dataclass
class EmailNotice:
    """A highlighted notice/alert box"""
    emoji: str
    title: str
    message: str
    color: str = "#f59e0b"  # amber-500 by default
    bg_color: str = "#fff7ed"  # amber-50 by default


@dataclass
class EmailCTA:
    """Call-to-action button"""
    text: str
    url: str


@dataclass
class EmailMetadataRow:
    """Key-value row for displaying structured data"""
    label: str
    value: str
    emoji: Optional[str] = None


class BrikliEmailTemplate:
    """
    Base email template system using Brikli brand design.
    
    Creates professional, responsive HTML emails with consistent branding.
    """
    
    BRIKLI_GREEN = "#004225"
    BRIKLI_GREEN_HOVER = "#016231"
    LOGO_URL = "https://app.brikli.com/BrikliTransparentWhite.png"
    
    @staticmethod
    def create_email(
        title: str,
        greeting: str,
        sections: List[EmailSection],
        cta: Optional[EmailCTA] = None,
        metadata: Optional[List[EmailMetadataRow]] = None,
        notice: Optional[EmailNotice] = None,
        footer_note: Optional[str] = None
    ) -> str:
        """
        Generate a complete HTML email with Brikli branding.
        
        Args:
            title: Email title (h1)
            greeting: Opening greeting (e.g., "Hi John,")
            sections: List of content paragraphs
            cta: Optional call-to-action button
            metadata: Optional structured data rows
            notice: Optional highlighted notice box
            footer_note: Optional additional footer text
            
        Returns:
            Complete HTML email string
        """
        
        # Build content sections
        content_html = f"<p>{greeting}</p>\n"
        
        for section in sections:
            if section.is_bold:
                content_html += f"      <p><strong>{section.text}</strong></p>\n"
            else:
                content_html += f"      <p>{section.text}</p>\n"
        
        # Add metadata table if provided
        metadata_html = ""
        if metadata:
            metadata_html = BrikliEmailTemplate._build_metadata_table(metadata)
        
        # Add CTA button if provided
        cta_html = ""
        if cta:
            cta_html = f"""
      <div class="cta">
        <a href="{cta.url}">{cta.text}</a>
      </div>
"""
        
        # Add notice box if provided
        notice_html = ""
        if notice:
            notice_html = f"""
      <div class="notice" style="background-color: {notice.bg_color}; border-left: 4px solid {notice.color};">
        {notice.emoji} <strong>{notice.title}</strong><br />
        {notice.message}
      </div>
"""
        
        # Build footer note
        footer_text = footer_note if footer_note else "Thank you for using Brikli Property Management."
        
        # Complete HTML email
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>{title}</title>
  <style>
    body {{
      margin: 0;
      padding: 0;
      background-color: #f9fafb;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      color: #111827;
    }}
    .email-container {{
      max-width: 600px;
      margin: 0 auto;
      background-color: #ffffff;
      border-radius: 16px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.05);
      overflow: hidden;
    }}
    .header {{
      background-color: {BrikliEmailTemplate.BRIKLI_GREEN};
      text-align: center;
      padding: 48px 24px 40px 24px;
    }}
    .header img {{
      width: 180px;
      height: auto;
    }}
    .content {{
      padding: 40px 40px 30px 40px;
      text-align: left;
    }}
    h1 {{
      color: {BrikliEmailTemplate.BRIKLI_GREEN};
      font-size: 24px;
      font-weight: 700;
      text-align: center;
      margin-bottom: 24px;
    }}
    p {{
      font-size: 16px;
      line-height: 1.6;
      color: #374151;
      margin: 0 0 20px 0;
    }}
    .cta {{
      text-align: center;
      margin: 40px 0;
    }}
    .cta a {{
      background-color: {BrikliEmailTemplate.BRIKLI_GREEN};
      color: #ffffff !important;
      text-decoration: none;
      font-weight: 600;
      font-size: 16px;
      padding: 15px 36px;
      border-radius: 10px;
      display: inline-block;
      transition: background-color 0.3s ease;
    }}
    .cta a:hover {{
      background-color: {BrikliEmailTemplate.BRIKLI_GREEN_HOVER};
    }}
    .metadata-table {{
      background-color: #f9fafb;
      border: 1px solid #e5e7eb;
      border-radius: 10px;
      padding: 20px;
      margin: 24px 0;
    }}
    .metadata-row {{
      display: flex;
      padding: 8px 0;
      border-bottom: 1px solid #e5e7eb;
    }}
    .metadata-row:last-child {{
      border-bottom: none;
    }}
    .metadata-label {{
      font-weight: 600;
      color: #111827;
      min-width: 140px;
      font-size: 14px;
    }}
    .metadata-value {{
      color: #374151;
      font-size: 14px;
    }}
    .notice {{
      background-color: #fff7ed;
      border-left: 4px solid #f59e0b;
      border-radius: 10px;
      padding: 16px;
      color: #78350f;
      font-size: 14px;
      line-height: 1.6;
      margin-bottom: 30px;
    }}
    .footer {{
      border-top: 1px solid #e5e7eb;
      text-align: center;
      padding: 24px;
      font-size: 13px;
      color: #6b7280;
    }}
    .footer a {{
      color: {BrikliEmailTemplate.BRIKLI_GREEN};
      text-decoration: underline;
    }}
    .priority-badge {{
      display: inline-block;
      padding: 4px 12px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
    }}
    .priority-high {{
      background-color: #fee2e2;
      color: #991b1b;
    }}
    .priority-medium {{
      background-color: #fef3c7;
      color: #92400e;
    }}
    .priority-low {{
      background-color: #dcfce7;
      color: #166534;
    }}
  </style>
</head>
<body>
  <div class="email-container">
    <!-- Header -->
    <div class="header">
      <img src="{BrikliEmailTemplate.LOGO_URL}" alt="Brikli Logo" />
    </div>

    <!-- Content -->
    <div class="content">
      <h1>{title}</h1>
{content_html}
{metadata_html}
{cta_html}
{notice_html}
    </div>

    <!-- Footer -->
    <div class="footer">
      {footer_text}<br />
      Need help? Contact <a href="mailto:support@brikli.com">support@brikli.com</a><br /><br />
      © 2025 Brikli. All rights reserved.
    </div>
  </div>
</body>
</html>"""
    
    @staticmethod
    def _build_metadata_table(metadata: List[EmailMetadataRow]) -> str:
        """Build HTML table for structured metadata"""
        rows_html = ""
        for row in metadata:
            emoji_prefix = f"{row.emoji} " if row.emoji else ""
            rows_html += f"""        <div class="metadata-row">
          <div class="metadata-label">{emoji_prefix}{row.label}:</div>
          <div class="metadata-value">{row.value}</div>
        </div>
"""
        
        return f"""
      <div class="metadata-table">
{rows_html}      </div>
"""
    
    @staticmethod
    def get_priority_badge_html(priority: str) -> str:
        """Get HTML for priority badge"""
        priority_map = {
            "high": ("🔴 HIGH", "priority-high"),
            "medium": ("🟡 MEDIUM", "priority-medium"),
            "low": ("🟢 LOW", "priority-low")
        }
        
        text, css_class = priority_map.get(priority.lower(), ("NORMAL", "priority-medium"))
        return f'<span class="priority-badge {css_class}">{text}</span>'

