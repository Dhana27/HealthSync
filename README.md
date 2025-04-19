# Virtual Healthcare Assistant

A comprehensive healthcare platform that connects patients with doctors through virtual consultations, health monitoring, and AI-powered assistance.

## Features

- **User Authentication**
  - Patient and Doctor registration
  - Role-based access control
  - Profile management

- **Virtual Consultation**
  - Real-time chat between doctors and patients
  - Video consultation support
  - Consultation history tracking
  - Doctor availability management

- **Health Monitoring**
  - Fitbit integration for vital signs tracking
  - Health data visualization
  - Symptom tracking and analysis
  - AI-powered health insights

- **Notifications**
  - Medication reminders
  - Appointment notifications
  - Consultation alerts
  - Health status updates

- **AI Assistant**
  - Health-related queries
  - Symptom analysis
  - Medical information
  - Emergency guidance

## Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd virtual_assistant
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   Create a `.env` file with the following variables:
   ```
   DEBUG=True
   SECRET_KEY=your-secret-key
   DATABASE_URL=your-database-url
   FITBIT_CLIENT_ID=your-fitbit-client-id
   FITBIT_CLIENT_SECRET=your-fitbit-client-secret
   ```

5. Run migrations:
   ```bash
   python manage.py migrate
   ```

6. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```

7. Run the development server:
   ```bash
   python manage.py runserver
   ```

## Project Structure

- `core/` - Main application module
  - `models.py` - Database models
  - `views.py` - View functions
  - `urls.py` - URL routing
  - `templates/` - HTML templates

- `notifications/` - Notification handling
  - `models.py` - Notification models
  - `views.py` - Notification views
  - `templates/` - Notification templates

- `static/` - Static files (CSS, JS, images)
- `media/` - User-uploaded files
- `templates/` - Base templates

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 