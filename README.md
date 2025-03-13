# FitFuel - AI-Powered Workout and Meal Planning Platform

FitFuel is an innovative AI-powered platform designed exclusively for personal trainers to create custom workout and meal plans for their clients. Generate professional, branded plans in minutes that adapt to client progress and budget constraints.

## Features

- **Custom Workout Plans**: Generate progressive exercise routines based on client fitness levels and goals
- **Smart Meal Planning**: Create budget-conscious meal plans that respect dietary preferences
- **Budget Management**: Automatically adjust meal plans to fit client's weekly food budget
- **Progression Tracking**: Auto-adjusting workout intensity based on client progress
- **Seasonal Adaptability**: Smart ingredient substitutions based on seasonal availability
- **Quick Substitutions**: Easy-to-use tool for swapping meals or exercises
- **Motivational Content**: AI-generated encouragement messages
- **Brand Integration**: Custom branding options for trainers

## Installation

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up environment variables in `.env`:
   ```
   FLASK_APP=app.py
   FLASK_ENV=development
   SECRET_KEY=your_secret_key
   DATABASE_URL=sqlite:///fitfuel.db
   OPENAI_API_KEY=your_openai_api_key
   ```
5. Initialize the database:
   ```bash
   flask db upgrade
   ```
6. Run the application:
   ```bash
   flask run
   ```

## Tech Stack

- Backend: Python/Flask
- Database: SQLAlchemy
- Frontend: HTML, CSS, JavaScript
- PDF Generation: ReportLab
- AI Integration: OpenAI API (optional for motivational content)

## Pricing

- **Free Tier**: 1 plan/month
- **Premium**: $15/month for unlimited plans and features

## License

Copyright © 2024 FitFuel. All rights reserved. 