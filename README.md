# Wingz Ride API

A comprehensive Django REST API for a ride-sharing application, built with Django REST Framework. This API provides endpoints for managing users, rides, and ride events with advanced features like GPS-based distance calculation, real-time filtering, and optimized database queries.

## 🚀 Features

### Core Functionality
- **User Management**: Complete CRUD operations for riders and drivers
- **Ride Management**: Create, update, and track ride requests
- **Event Tracking**: Comprehensive ride event logging and history
- **Authentication**: JWT-based authentication system
- **GPS Integration**: Real-time distance calculation using Haversine formula
- **Advanced Filtering**: Filter rides by location, time, status, and more
- **Performance Optimized**: Database-level filtering and query optimization

### Advanced Features
- **Distance Sorting**: Sort rides by proximity to user location
- **Time-based Filtering**: Filter rides by pickup time ranges
- **Status Management**: Track ride lifecycle from request to completion
- **Event History**: Complete audit trail of ride events
- **Pagination**: Efficient pagination for large datasets
- **Swagger Documentation**: Interactive API documentation

## 🛠️ Tech Stack

- **Backend**: Django 4.2+ with Django REST Framework
- **Database**: SQLite (development) / PostgreSQL (production ready)
- **Authentication**: JWT tokens
- **API Documentation**: Swagger/OpenAPI 3.0
- **Python Version**: 3.8+

## 📋 Prerequisites

Before running this project, make sure you have the following installed:

- Python 3.8 or higher
- pip (Python package installer)
- Git (for version control)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd wingz_api
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Database Setup

```bash
# Run migrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser
```

### 5. Run the Development Server

```bash
python manage.py runserver
```

The API will be available at `http://127.0.0.1:8000/`

### 6. Access API Documentation

Visit `http://127.0.0.1:8000/api/docs/` for interactive API documentation.

## 📁 Project Structure

```
wingz_api/
├── manage.py                 # Django management script
├── requirements.txt          # Python dependencies
├── README.md                # This file
├── .gitignore              # Git ignore rules
├── wingz_api/              # Main Django project
│   ├── __init__.py
│   ├── settings.py         # Django settings
│   ├── urls.py            # Main URL configuration
│   ├── wsgi.py            # WSGI configuration
│   └── asgi.py            # ASGI configuration
└── rides/                  # Main app
    ├── __init__.py
    ├── admin.py           # Django admin configuration
    ├── apps.py            # App configuration
    ├── models.py          # Database models
    ├── serializers.py     # DRF serializers
    ├── views.py           # API views
    ├── urls.py            # App URL configuration
    ├── permissions.py     # Custom permissions
    ├── authentication.py  # Authentication logic
    ├── filters.py         # Custom filters
    └── migrations/        # Database migrations
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the project root (optional for development):

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3
```

### Database Configuration

The project is configured to use SQLite by default for development. For production, update the database settings in `wingz_api/settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'your_db_name',
        'USER': 'your_db_user',
        'PASSWORD': 'your_db_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

## 📚 API Endpoints

### Authentication
- `POST /api/v1/auth/login/` - User login
- `POST /api/v1/auth/register/` - User registration
- `POST /api/v1/auth/refresh/` - Refresh JWT token

### Users
- `GET /api/v1/users/` - List all users
- `POST /api/v1/users/` - Create new user
- `GET /api/v1/users/{id}/` - Get user details
- `PUT /api/v1/users/{id}/` - Update user
- `DELETE /api/v1/users/{id}/` - Delete user
- `GET /api/v1/users/drivers/` - Get all drivers
- `GET /api/v1/users/riders/` - Get all riders

### Rides
- `GET /api/v1/rides/` - List rides with advanced filtering
- `POST /api/v1/rides/` - Create new ride
- `GET /api/v1/rides/{id}/` - Get ride details
- `PUT /api/v1/rides/{id}/` - Update ride
- `DELETE /api/v1/rides/{id}/` - Delete ride

### Ride Events
- `GET /api/v1/ride-events/` - List ride events
- `POST /api/v1/ride-events/` - Create ride event
- `GET /api/v1/ride-events/{id}/` - Get event details
- `PUT /api/v1/ride-events/{id}/` - Update event
- `DELETE /api/v1/ride-events/{id}/` - Delete event

## 🔍 Advanced Features

### Distance Calculation

The API includes GPS-based distance calculation using the Haversine formula:

```python
# Example: Get rides sorted by distance
GET /api/v1/rides/?lat=40.7128&lon=-74.0060&sort_by=distance
```

### Filtering Options

- **Location**: Filter by pickup coordinates
- **Time**: Filter by pickup time ranges
- **Status**: Filter by ride status
- **User**: Filter by rider or driver
- **Date**: Filter by creation date

### Sorting Options

- **Distance**: Sort by proximity to coordinates
- **Pickup Time**: Sort by scheduled pickup time
- **Created Date**: Sort by creation time

## 🧪 Testing

### Test Framework

The project uses Django's built-in test framework. Test cases can be added to `rides/tests.py` as needed.

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test rides
```

### Test Data

The API includes sample data for testing. You can create test users and rides through the API endpoints or Django admin.

## 🚀 Deployment

### Production Checklist

1. **Environment Variables**: Set production environment variables
2. **Database**: Configure production database (PostgreSQL recommended)
3. **Static Files**: Collect and serve static files
4. **Security**: Update SECRET_KEY and security settings
5. **HTTPS**: Configure SSL/TLS certificates
6. **CORS**: Configure CORS settings for frontend integration

### Docker Deployment (Optional)

```dockerfile
# Dockerfile example
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "wingz_api.wsgi:application"]
```

## 🔧 Development

### Code Quality

The project follows Django best practices and includes:

- **Type Hints**: Python type annotations for better code clarity
- **Docstrings**: Comprehensive documentation for all functions
- **Error Handling**: Robust error handling and logging
- **Performance**: Optimized database queries and caching

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style

- Follow PEP 8 guidelines
- Use meaningful variable and function names
- Add docstrings for all functions and classes
- Write tests for new features

## 🐛 Troubleshooting

### Common Issues

1. **Database Migration Errors**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

2. **Permission Errors**
   ```bash
   chmod +x manage.py
   ```

3. **Import Errors**
   ```bash
   pip install -r requirements.txt
   ```

4. **Port Already in Use**
   ```bash
   python manage.py runserver 8001
   ```

### Debug Mode

Enable debug mode in `settings.py` for detailed error messages:

```python
DEBUG = True
```

## 📊 Performance Considerations

### Database Optimization

- **Indexes**: Added database indexes for frequently queried fields
- **Query Optimization**: Used `select_related` and `prefetch_related` to minimize database queries
- **Pagination**: Implemented efficient pagination for large datasets

### Memory Management

- **Distance Sorting**: Limited to 10,000 records to prevent memory issues
- **Caching**: Implemented query result caching where appropriate

## 🔒 Security Features

- **JWT Authentication**: Secure token-based authentication
- **Input Validation**: Comprehensive input validation and sanitization
- **SQL Injection Protection**: Django ORM prevents SQL injection
- **CORS Configuration**: Configurable CORS settings for frontend integration

## 📈 Monitoring and Logging

The API includes comprehensive logging for:

- **Request/Response**: All API requests and responses
- **Errors**: Detailed error logging with stack traces
- **Performance**: Query execution times and optimization metrics
- **Authentication**: Login attempts and security events

## 🤝 Support

For support and questions:

1. Check the [API Documentation](http://127.0.0.1:8000/api/docs/)
2. Review the [Troubleshooting](#troubleshooting) section
3. Create an issue in the repository
4. Contact the development team

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Django REST Framework for the excellent API framework
- Django community for extensive documentation and support
- Contributors and testers who helped improve the project

---

**Happy Coding! 🚀**

For more information about Django REST Framework, visit [django-rest-framework.org](https://www.django-rest-framework.org/)