# NVC Banking Platform Documentation Integration Guide

This guide explains how to integrate the documentation files into the web interface of the NVC Banking Platform.

## Available Documentation

The documentation directory contains several comprehensive guides:

1. **User Guide (`user_guide.md`)**: Complete guide for end users of the platform
2. **Admin Guide (`admin_guide.md`)**: Detailed guide for administrators
3. **Technical Reference (`technical_reference.md`)**: In-depth technical documentation for developers

## Integration Options

### Option 1: Add Documentation Routes to the Web Interface

Add new routes in the main_routes.py file to serve the documentation:

```python
@main.route('/docs/user-guide')
def user_guide():
    """User guide documentation route"""
    with open('docs/user_guide.md', 'r') as file:
        content = file.read()
    # Convert markdown to HTML (requires markdown library)
    html_content = markdown.markdown(content)
    return render_template('documentation.html', 
                           title='User Guide',
                           content=html_content)

@main.route('/docs/admin-guide')
@admin_required
def admin_guide():
    """Admin guide documentation route - admin only"""
    with open('docs/admin_guide.md', 'r') as file:
        content = file.read()
    html_content = markdown.markdown(content)
    return render_template('documentation.html', 
                           title='Administrator Guide',
                           content=html_content)

@main.route('/docs/technical-reference')
@admin_required
def technical_reference():
    """Technical reference documentation route - admin only"""
    with open('docs/technical_reference.md', 'r') as file:
        content = file.read()
    html_content = markdown.markdown(content)
    return render_template('documentation.html', 
                           title='Technical Reference',
                           content=html_content)
```

### Option 2: Add PDF Generation for Documentation

Convert the markdown documents to downloadable PDFs:

```python
@main.route('/docs/user-guide/pdf')
def user_guide_pdf():
    """Generate and download user guide as PDF"""
    with open('docs/user_guide.md', 'r') as file:
        content = file.read()
    html_content = markdown.markdown(content)
    
    # Create PDF using WeasyPrint
    html = render_template('documentation_pdf.html', 
                           title='NVC Banking Platform - User Guide',
                           content=html_content)
    pdf = weasyprint.HTML(string=html).write_pdf()
    
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=user_guide.pdf'
    return response
```

### Option 3: Add Documentation Links to Navigation

Add links to the documentation in the website navigation:

1. **For User Guide**: Add to the main navigation in layout.html
2. **For Admin Guide**: Add to the admin dashboard navigation
3. **For Technical Reference**: Add to the admin settings area

Example addition to layout.html:

```html
<li class="nav-item dropdown">
    <a class="nav-link dropdown-toggle" href="#" id="docsDropdown" role="button" 
       data-bs-toggle="dropdown" aria-expanded="false">
        Documentation
    </a>
    <ul class="dropdown-menu" aria-labelledby="docsDropdown">
        <li><a class="dropdown-item" href="{{ url_for('web.main.user_guide') }}">User Guide</a></li>
        {% if current_user.is_authenticated and (current_user.role == 'admin' or current_user.username in ['admin', 'headadmin']) %}
        <li><a class="dropdown-item" href="{{ url_for('web.main.admin_guide') }}">Admin Guide</a></li>
        <li><a class="dropdown-item" href="{{ url_for('web.main.technical_reference') }}">Technical Reference</a></li>
        {% endif %}
    </ul>
</li>
```

## Required Template

Create a documentation.html template:

```html
{% extends 'layout.html' %}

{% block title %}{{ title }} - NVC Banking Platform{% endblock %}

{% block content %}
<div class="container mt-4">
    <div class="row">
        <div class="col-md-12">
            <div class="card shadow">
                <div class="card-header bg-primary text-white">
                    <h2>{{ title }}</h2>
                </div>
                <div class="card-body documentation-content">
                    {{ content|safe }}
                </div>
                <div class="card-footer text-muted">
                    <a href="#" onclick="window.print();" class="btn btn-outline-secondary">
                        <i class="fas fa-print me-2"></i>Print
                    </a>
                    {% if pdf_url %}
                    <a href="{{ pdf_url }}" class="btn btn-outline-primary">
                        <i class="fas fa-file-pdf me-2"></i>Download PDF
                    </a>
                    {% endif %}
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block styles %}
{{ super() }}
<style>
    .documentation-content {
        font-size: 16px;
        line-height: 1.6;
    }
    .documentation-content h1, 
    .documentation-content h2, 
    .documentation-content h3 {
        margin-top: 1.5rem;
        margin-bottom: 1rem;
    }
    .documentation-content h1 {
        font-size: 2.25rem;
        border-bottom: 1px solid var(--bs-gray-300);
        padding-bottom: 0.5rem;
    }
    .documentation-content h2 {
        font-size: 1.75rem;
    }
    .documentation-content h3 {
        font-size: 1.5rem;
    }
    .documentation-content ul, 
    .documentation-content ol {
        margin-bottom: 1rem;
    }
    .documentation-content table {
        width: 100%;
        margin-bottom: 1rem;
        border-collapse: collapse;
    }
    .documentation-content table, 
    .documentation-content th, 
    .documentation-content td {
        border: 1px solid var(--bs-gray-300);
        padding: 0.5rem;
    }
    .documentation-content th {
        background-color: var(--bs-gray-200);
    }
    .documentation-content code {
        background-color: var(--bs-gray-200);
        padding: 0.2rem 0.4rem;
        border-radius: 0.25rem;
    }
    @media print {
        .card-header, .card-footer, nav, footer {
            display: none !important;
        }
        .card {
            border: none !important;
            box-shadow: none !important;
        }
        .card-body {
            padding: 0 !important;
        }
    }
</style>
{% endblock %}
```

## Dependencies

Add the necessary Python package for Markdown rendering:

```bash
python -m pip install markdown
```

This is already included in your environment if you're using WeasyPrint for PDF generation.

## Implementation Steps

1. Create the documentation.html template
2. Add the routes to main_routes.py
3. Add navigation links in appropriate places
4. Install any needed dependencies
5. Test each documentation route

## Permissions

- User Guide: Available to all authenticated users
- Admin Guide: Restricted to users with admin role or specific usernames
- Technical Reference: Restricted to users with admin role or specific usernames

## Future Improvements

Consider these enhancements after initial implementation:

1. Add search functionality within documentation
2. Implement table of contents navigation
3. Add versioning to documentation
4. Create a unified documentation portal page

This integration approach provides a seamless way for users and administrators to access the comprehensive documentation directly within the web interface.