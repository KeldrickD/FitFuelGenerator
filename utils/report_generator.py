from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from datetime import datetime
import io
import logging

def generate_client_report(client, achievements, progress_logs, goals):
    """Generate a comprehensive PDF report for a client"""
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        # Custom styles
        styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30
        ))
        styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=12
        ))

        # Header
        story.append(Paragraph(f"Progress Report - {client.name}", styles['CustomTitle']))
        story.append(Paragraph(f"Generated on {datetime.utcnow().strftime('%B %d, %Y')}", styles['Normal']))
        story.append(Spacer(1, 20))

        # Client Information
        story.append(Paragraph("Client Information", styles['SectionTitle']))
        client_info = [
            ["Fitness Level:", client.fitness_level or "Not specified"],
            ["Primary Goal:", client.goal or "Not specified"],
            ["Member Since:", client.created_at.strftime("%B %d, %Y") if client.created_at else "Not specified"]
        ]
        client_table = Table(client_info, colWidths=[2*inch, 4*inch])
        client_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(client_table)
        story.append(Spacer(1, 20))

        # Achievement Progress
        story.append(Paragraph("Achievement Progress", styles['SectionTitle']))
        if achievements:
            achievement_data = [["Achievement", "Progress", "Status"]]
            for achievement in achievements:
                achievement_data.append([
                    achievement.achievement.name if hasattr(achievement, 'achievement') else "Unknown",
                    f"{achievement.progress}%" if hasattr(achievement, 'progress') else "0%",
                    "Completed" if getattr(achievement, 'completed', False) else "In Progress"
                ])
            achievement_table = Table(achievement_data, colWidths=[3*inch, 2*inch, 2*inch])
            achievement_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('PADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(achievement_table)
        else:
            story.append(Paragraph("No achievements recorded yet.", styles['Normal']))
        story.append(Spacer(1, 20))

        # Goals Progress
        story.append(Paragraph("Goals Progress", styles['SectionTitle']))
        if goals:
            goals_data = [["Goal Type", "Target", "Current Progress", "Due Date"]]
            for goal in goals:
                goals_data.append([
                    goal.goal_type or "Unknown",
                    str(goal.target_value) if goal.target_value else "Not set",
                    str(goal.current_value) if goal.current_value else "Not started",
                    goal.target_date.strftime("%B %d, %Y") if goal.target_date else "Not set"
                ])
            goals_table = Table(goals_data, colWidths=[2*inch, 2*inch, 2*inch, 2*inch])
            goals_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('PADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(goals_table)
        else:
            story.append(Paragraph("No goals set yet.", styles['Normal']))
        story.append(Spacer(1, 20))

        # Recent Progress
        story.append(Paragraph("Recent Progress", styles['SectionTitle']))
        if progress_logs:
            # Last 30 days summary
            recent_logs = progress_logs[:30]  # Get the most recent 30 logs
            workout_completion = sum(1 for log in recent_logs if log.workout_completed)
            story.append(Paragraph(
                f"Last 30 Days Summary:",
                styles['Normal']
            ))
            story.append(Paragraph(
                f"• Workouts Completed: {workout_completion}",
                styles['Normal']
            ))
            story.append(Paragraph(
                f"• Completion Rate: {(workout_completion/len(recent_logs))*100:.1f}%",
                styles['Normal']
            ))

            # Add detailed metrics if available
            if any(log.metrics for log in recent_logs):
                story.append(Spacer(1, 10))
                story.append(Paragraph("Recent Metrics:", styles['Normal']))
                metrics_data = [["Date", "Metric", "Value"]]
                for log in recent_logs:
                    if log.metrics:
                        for metric, value in log.metrics.items():
                            metrics_data.append([
                                log.log_date.strftime("%Y-%m-%d"),
                                metric,
                                str(value)
                            ])
                if len(metrics_data) > 1:  # If we have any metrics besides the header
                    metrics_table = Table(metrics_data, colWidths=[2*inch, 3*inch, 3*inch])
                    metrics_table.setStyle(TableStyle([
                        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                        ('PADDING', (0, 0), (-1, -1), 6),
                    ]))
                    story.append(metrics_table)
        else:
            story.append(Paragraph("No progress logs recorded yet.", styles['Normal']))

        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer

    except Exception as e:
        logging.error(f"Error generating client report: {str(e)}")
        raise