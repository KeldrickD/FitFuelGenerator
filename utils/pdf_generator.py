import logging
from flask import make_response
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO

def generate_pdf(client_data, workout_plan, meal_plan):
    """Generate PDF with workout and meal plans"""
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        # Add title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30
        )
        story.append(Paragraph(f"Fitness Plan for {client_data['name']}", title_style))
        story.append(Spacer(1, 12))

        # Add client information
        story.append(Paragraph("Client Information", styles['Heading2']))
        client_info = [
            ["Goal:", client_data['goal']],
            ["Fitness Level:", client_data['fitness_level']],
            ["Diet Preference:", client_data['diet_preference']],
            ["Weekly Budget:", f"${client_data['weekly_budget']}"],
            ["Training Days:", str(client_data['training_days'])]
        ]
        
        client_table = Table(client_info, colWidths=[100, 300])
        client_table.setStyle(TableStyle([
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ]))
        story.append(client_table)
        story.append(Spacer(1, 20))

        # Add workout plan
        story.append(Paragraph("Workout Plan", styles['Heading2']))
        for day, workout in workout_plan.items():
            story.append(Paragraph(day, styles['Heading3']))
            if workout['exercises'] == 'Rest Day':
                story.append(Paragraph("Rest Day", styles['Normal']))
            else:
                exercise_data = [[ex['name'], f"{ex['sets']} sets", ex['reps']] 
                               for ex in workout['exercises']]
                exercise_table = Table(exercise_data, colWidths=[200, 100, 100])
                exercise_table.setStyle(TableStyle([
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ]))
                story.append(exercise_table)
            story.append(Paragraph(f"Motivation: {workout.get('motivation', '')}", styles['Italic']))
            story.append(Spacer(1, 12))

        # Add meal plan
        story.append(Paragraph("Meal Plan", styles['Heading2']))
        for day, meals in meal_plan.items():
            story.append(Paragraph(day, styles['Heading3']))
            meal_data = []
            for meal_type, meal in meals['meals'].items():
                meal_data.append([meal_type.capitalize(), meal['name'], f"${meal['cost']:.2f}"])
            
            meal_table = Table(meal_data, colWidths=[100, 300, 100])
            meal_table.setStyle(TableStyle([
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ]))
            story.append(meal_table)
            story.append(Paragraph(f"Daily Total: ${meals['total_cost']:.2f}", styles['Normal']))
            story.append(Spacer(1, 12))

        # Generate PDF
        doc.build(story)
        buffer.seek(0)
        
        # Create response
        response = make_response(buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=fitness_plan_{client_data["name"]}.pdf'
        
        return response

    except Exception as e:
        logging.error(f"Error generating PDF: {str(e)}")
        raise
