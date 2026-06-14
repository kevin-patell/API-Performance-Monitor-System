import os
import pandas as pd
from datetime import datetime
from config import Config
from database import db_pool

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

class ReportingEngine:
    
    @staticmethod
    def _fetch_raw_data():
        with db_pool.acquire() as cursor:
            cursor.execute('''
                SELECT c.id, a.name, a.url, a.method, c.status_code, 
                       c.response_time_ms, c.is_success, c.is_anomaly, c.error_message, c.checked_at
                FROM api_checks c
                JOIN apis a ON c.api_id = a.id
                ORDER BY c.checked_at DESC
            ''')
            rows = cursor.fetchall()
        return [dict(r) for r in rows]

    @classmethod
    def generate_csv(cls) -> str:
        df = pd.DataFrame(cls._fetch_raw_data())
        target_path = os.path.join(Config.EXPORT_DIR, f"Metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        df.to_csv(target_path, index=False)
        return target_path

    @classmethod
    def generate_excel(cls) -> str:
        df = pd.DataFrame(cls._fetch_raw_data())
        target_path = os.path.join(Config.EXPORT_DIR, f"Metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        with pd.ExcelWriter(target_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Performance Metrics', index=False)
        return target_path

    @classmethod
    def generate_pdf(cls) -> str:
        data = cls._fetch_raw_data()
        target_path = os.path.join(Config.EXPORT_DIR, f"Metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        
        doc = SimpleDocTemplate(target_path, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        story = []
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'DocTitle', parent=styles['Heading1'], fontSize=22, leading=26, textColor=colors.HexColor("#0f172a"), spaceAfter=15
        )
        
        story.append(Paragraph("System Telemetry Performance Index Report", title_style))
        story.append(Paragraph(f"Analysis Window Framework Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        story.append(Spacer(1, 15))
        
        table_content = [["Target Service Name", "Method", "HTTP Code", "Latency", "Health Profile", "Anomaly"]]
        for row in data[:35]:
            table_content.append([
                row['name'][:22],
                row['method'],
                str(row['status_code'] or 'ERR'),
                f"{row['response_time_ms']:.1f}ms",
                "ONLINE" if row['is_success'] == 1 else "OFFLINE",
                "YES" if row['is_anomaly'] == 1 else "NO"
            ])
            
        t = Table(table_content, colWidths=[140, 50, 60, 70, 90, 60])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e293b")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#f8fafc")),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(t)
        doc.build(story)
        return target_path