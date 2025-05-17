import os
import logging
import time
from datetime import datetime

from flask import Flask, render_template, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_jwt_extended import JWTManager
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager

# Import performance optimization modules
try:
    import template_cache
    import memory_cache
    import response_cache
    OPTIMIZATIONS_AVAILABLE = True
except ImportError:
    OPTIMIZATIONS_AVAILABLE = False


# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass


# Create extension instances
db = SQLAlchemy(model_class=Base)
csrf = CSRFProtect()
jwt = JWTManager()
login_manager = LoginManager()
login_manager.login_view = 'web.main.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))


# The global Flask app instance
app = None

def create_app():
    global app
    # Create the app
    app = Flask(__name__)
    # Set a default secret key if SESSION_SECRET environment variable isn't available
    app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key_for_testing_only")
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

    # Configure the database with optimized settings
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
        "pool_size": 15,         # Increased pool size for better concurrency
        "max_overflow": 20,      # Allow additional connections when pool is full
        "pool_timeout": 60,      # Longer timeout to prevent connection errors
        "connect_args": {
            "connect_timeout": 10,  # Connection timeout in seconds
            "keepalives": 1,        # Enable TCP keepalives
            "keepalives_idle": 30,  # Time between keepalive probes in seconds
            "keepalives_interval": 10,  # Time between successive keepalive probes
            "keepalives_count": 5   # Number of failed probes before disconnection
        },
        "execution_options": {
            "isolation_level": "READ COMMITTED"  # Standard isolation level
        }
    }
    
    # Disable SQLAlchemy modification tracking for better performance
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Add JSON filter for templates
    @app.template_filter('from_json')
    def from_json(value):
        import json
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return {}
            
    # Add format_number filter for formatting large numbers with commas
    @app.template_filter('format_number')
    def format_number(value):
        """Format a number with commas as thousands separators"""
        try:
            return "{:,}".format(int(value))
        except (ValueError, TypeError):
            return value
            
    # Add datetime filter for formatting timestamps
    @app.template_filter('datetime')
    def format_datetime(value):
        """Format a datetime object to a readable string"""
        if value is None:
            return ""
        try:
            return value.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError, AttributeError):
            return str(value)
            
    # Add format_currency filter for formatting currency values
    @app.template_filter('format_currency')
    def format_currency(value):
        """Format a currency value with 2 decimal places"""
        if value is None:
            return "0.00"
        try:
            return "{:.2f}".format(float(value))
        except (ValueError, TypeError):
            return str(value)
    
    # Allow embedding in iframes for Replit
    @app.after_request
    def set_security_headers(response):
        # This allows embedding in Replit iframe
        response.headers['X-Frame-Options'] = 'ALLOW-FROM https://replit.com'
        # For modern browsers that don't support ALLOW-FROM
        response.headers['Content-Security-Policy'] = "frame-ancestors 'self' https://replit.com https://*.replit.com;"
        return response
    
    # Configure session 
    app.config["SESSION_COOKIE_SECURE"] = False  # Allow non-HTTPS for development
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["PERMANENT_SESSION_LIFETIME"] = 2592000  # 30 days
    app.config["SESSION_TYPE"] = "filesystem"
    # Make sessions permanent by default
    app.config["SESSION_PERMANENT"] = True
    
    # Configure Flask-Login
    app.config["REMEMBER_COOKIE_DURATION"] = 86400  # 24 hours
    app.config["REMEMBER_COOKIE_SECURE"] = False  # Allow non-HTTPS for development
    app.config["REMEMBER_COOKIE_HTTPONLY"] = True
    app.config["REMEMBER_COOKIE_SAMESITE"] = "Lax"
    app.config["LOGIN_DISABLED"] = False
    app.config["SESSION_PROTECTION"] = "strong"

    # Configure JWT
    app.config["JWT_SECRET_KEY"] = os.environ.get("SESSION_SECRET", "dev_secret_key_for_testing_only")  # Using same secret for simplicity
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 3600  # 1 hour

    # Initialize extensions with app
    db.init_app(app)
    
    # Add database connection retry mechanism
    try:
        from db_retry import setup_db_retry_handlers
        setup_db_retry_handlers(app, db)
        logger.info("Database retry mechanism initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database retry mechanism: {str(e)}")
    
    # Disable CSRF protection completely for API testing
    app.config['WTF_CSRF_ENABLED'] = False
    
    # Initialize extensions
    csrf.init_app(app)
    jwt.init_app(app)
    login_manager.init_app(app)
    # login_view is already set in the global login_manager configuration
    
    # Direct root-level routes for registration
    @app.route('/signup')
    @app.route('/join')
    @app.route('/register')
    @app.route('/create-account')
    def direct_register():
        """Direct shortcut to the registration form"""
        return redirect('/main/register')
    
    # Add custom filters
    import json
    from utils import format_currency, format_transaction_type
    from markupsafe import Markup
    app.jinja_env.filters['format_currency'] = lambda amount, currency='USD': format_currency(amount, currency)
    
    # Add nl2br filter for newlines to <br> conversion
    @app.template_filter('nl2br')
    def nl2br_filter(text):
        """Convert newlines to <br> tags"""
        if text is None:
            return ""
        return Markup(text.replace('\n', '<br>'))
    
    # Register number formatting filter
    @app.template_filter('format_number')
    def format_number_filter(value):
        """Format a number with comma separators"""
        if value is None:
            return "0"
        try:
            return "{:,}".format(int(value))
        except (ValueError, TypeError):
            try:
                return "{:,.2f}".format(float(value))
            except (ValueError, TypeError):
                return str(value)
    
    # Register format_transaction_type as a template filter
    @app.template_filter('format_transaction_type')
    def format_transaction_type_filter(transaction_type):
        return format_transaction_type(transaction_type)
        
    # Add JSON parsing filter for transaction metadata
    @app.template_filter('from_json')
    def from_json_filter(value):
        """Convert JSON string to Python dictionary"""
        if not value:
            return {}
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return {}

    # Set debug mode to True
    app.config['DEBUG'] = True
    
    # Global error handlers
    @app.errorhandler(Exception)
    def handle_exception(e):
        """Global exception handler to log errors"""
        app.logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
        return render_template('error.html', error=str(e)), 500
        
    @app.errorhandler(404)
    def page_not_found(e):
        """Custom 404 error handler"""
        app.logger.error(f"404 error: {str(e)}")
        return render_template(
            'error.html', 
            error="The requested page could not be found.", 
            code=404, 
            title="Page Not Found"
        ), 404
    
    # Add direct routes to handle common paths
    @app.route('/')
    def root():
        """Root route - redirects to the index"""
        try:
            # Use the real index template
            return render_template('index.html')
        except Exception as e:
            logger.error(f"Error rendering index: {str(e)}")
            return f"Error: {str(e)}", 500
    
    # Add direct access to funds transfer guide
    @app.route('/funds-transfer-guide')
    def funds_transfer_guide_direct():
        """Direct access to funds transfer guide"""
        try:
            # Use redirect from the imported Flask functions
            return redirect('/documents/nvc_funds_transfer_guide')
        except Exception as e:
            logger.error(f"Error redirecting to funds transfer guide: {str(e)}")
            return f"Error: {str(e)}", 500
    
    @app.route('/main')
    def main_index():
        """Main index route"""
        try:
            return render_template('index.html')
        except Exception as e:
            logger.error(f"Error rendering main index: {str(e)}")
            return f"Error: {str(e)}", 500
            
    @app.route('/main/index')
    def main_explicit_index():
        """Explicit main index route"""
        try:
            return render_template('index.html')
        except Exception as e:
            logger.error(f"Error rendering explicit main index: {str(e)}")
            return f"Error: {str(e)}", 500

    @app.route('/routes')
    def list_routes():
        """List all registered routes for debugging"""
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append({
                'endpoint': rule.endpoint,
                'methods': ','.join([method for method in rule.methods if method not in ('HEAD', 'OPTIONS')]),
                'url': str(rule)
            })
        return {'routes': routes}

    with app.app_context():
        # Import models to ensure tables are created
        import models  # noqa: F401
        
        # Import account holder models
        try:
            import account_holder_models  # noqa: F401
            logger.info("Account holder models imported successfully")
        except Exception as e:
            logger.error(f"Error importing account holder models: {str(e)}")
            logger.warning("Application will run without account holder functionality")
            
        # Import trust portfolio models
        try:
            import trust_portfolio  # noqa: F401
            logger.info("Trust portfolio models imported successfully")
        except Exception as e:
            logger.error(f"Error importing trust portfolio models: {str(e)}")
            logger.warning("Application will run without trust portfolio functionality")
            
        # Import payment models
        try:
            import payment_models  # noqa: F401
            logger.info("Payment models imported successfully")
        except Exception as e:
            logger.error(f"Error importing payment models: {str(e)}")
            logger.warning("Application will run without payment settlement functionality")
            
        # Import self-liquidating loan models
        try:
            import self_liquidating_loan  # noqa: F401
            logger.info("Self-liquidating loan models imported successfully")
        except Exception as e:
            logger.error(f"Error importing self-liquidating loan models: {str(e)}")
            logger.warning("Application will run without self-liquidating loan functionality")
            
        # Import financial institution recapitalization models
        try:
            import models.financial_institution  # noqa: F401
            logger.info("Financial institution recapitalization models imported successfully")
        except Exception as e:
            logger.error(f"Error importing financial institution recapitalization models: {str(e)}")
            logger.warning("Application will run without financial institution recapitalization functionality")
        
        # Create database tables
        db.create_all()
        
        # Initialize blockchain connection (make it optional to allow app to start without blockchain)
        try:
            from blockchain import init_web3
            init_web3()
            logger.info("Blockchain initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing blockchain: {str(e)}")
            logger.warning("Application will run without blockchain functionality")
        
        # High-availability infrastructure has been removed as requested
        logger.info("High-availability infrastructure is disabled")
        
        # Initialize payment gateways
        try:
            from payment_gateways import init_payment_gateways
            if init_payment_gateways():
                logger.info("Payment gateways initialized successfully")
            else:
                logger.warning("Failed to initialize payment gateways")
        except Exception as e:
            logger.error(f"Error initializing payment gateways: {str(e)}")
            logger.warning("Application will run without payment gateway functionality")
        
        # Import routes module to register Flask route decorators
        import routes
        
        # Import and register blueprints
        from routes import api_blueprint, web_blueprint, api_access_bp
        app.register_blueprint(api_blueprint)
        app.register_blueprint(web_blueprint)
        app.register_blueprint(api_access_bp)
        
        # Add direct routes for recapitalization program
        @app.route('/recapitalization')
        def recapitalization():
            """Financial Institution Recapitalization Program information page"""
            return render_template('recapitalization.html')
            
        @app.route('/recapitalization/dashboard')
        def recapitalization_dashboard():
            """Financial Institution Recapitalization Dashboard"""
            return render_template('recapitalization_dashboard.html')
        
        # Register Documentation routes
        from routes.documentation_routes import documentation_bp
        app.register_blueprint(documentation_bp, url_prefix='/documentation')
        
        # Register Admin routes
        from routes.admin import admin
        app.register_blueprint(admin)
        
        # Register Transaction Admin routes
        try:
            from routes.admin_routes import admin_bp
            app.register_blueprint(admin_bp)
            
            # Register NVC Platform integration admin routes
            from routes.nvc_platform_admin_routes import nvc_platform_admin_bp
            app.register_blueprint(nvc_platform_admin_bp)
            logger.info("Transaction Admin routes registered successfully")
        except Exception as e:
            logger.error(f"Error registering Transaction Admin routes: {str(e)}")
            logger.warning("Application will run without Transaction Admin functionality")
            
        # Register Blockchain Admin routes
        try:
            from routes.blockchain_admin_routes import blockchain_admin_bp
            app.register_blueprint(blockchain_admin_bp)
            logger.info("Blockchain Admin routes registered successfully")
        except Exception as e:
            logger.error(f"Error registering Blockchain Admin routes: {str(e)}")
            logger.warning("Application will run without Blockchain Admin functionality")
        
        # Register EDI Integration routes
        from routes.edi_routes import edi
        app.register_blueprint(edi)
        
        # Register Treasury Management System routes
        from routes.treasury_routes import treasury_bp
        app.register_blueprint(treasury_bp)
        
        # Register Treasury Settlement routes
        try:
            from routes.treasury_settlement_routes import treasury_settlement_bp
            app.register_blueprint(treasury_settlement_bp)
            logger.info("Treasury Settlement routes registered successfully")
        except Exception as e:
            logger.error(f"Error registering Treasury Settlement routes: {str(e)}")
            logger.warning("Application will run without Treasury Settlement functionality")
        
        # Register Document routes
        from routes.document_routes import docs_bp
        app.register_blueprint(docs_bp)
        
        # Register Self-Liquidating Loan routes
        try:
            from routes.self_liquidating_loan_routes import self_liquidating_loan_bp
            app.register_blueprint(self_liquidating_loan_bp)
            logger.info("Self-Liquidating Loan routes registered successfully")
        except Exception as e:
            logger.error(f"Error registering Self-Liquidating Loan routes: {str(e)}")
            logger.warning("Application will run without Self-Liquidating Loan functionality")
        
        # Register SWIFT GPI routes
        try:
            from routes.swift_gpi_routes import swift_gpi_routes
            app.register_blueprint(swift_gpi_routes)
            logger.info("SWIFT GPI routes registered successfully")
        except Exception as e:
            logger.error(f"Error registering SWIFT GPI routes: {str(e)}")
            logger.warning("Application will run without SWIFT GPI functionality")
        
        # Register Server-to-Server routes
        try:
            from routes.server_to_server_routes import server_to_server_routes
            app.register_blueprint(server_to_server_routes)
            logger.info("Server-to-Server routes registered successfully")
        except Exception as e:
            logger.error(f"Error registering Server-to-Server routes: {str(e)}")
            logger.warning("Application will run without Server-to-Server functionality")
        
        # Register RTGS routes
        try:
            from routes.rtgs_routes import rtgs_routes
            app.register_blueprint(rtgs_routes)
            logger.info("RTGS routes registered successfully")
        except Exception as e:
            logger.error(f"Error registering RTGS routes: {str(e)}")
            logger.warning("Application will run without RTGS functionality")
        
        # Register API routes
        from routes.api import api_bp as main_api_bp
        app.register_blueprint(main_api_bp)
        
        # Register NVC Platform integration API routes
        try:
            from nvc_platform_integration import nvc_platform_bp
            app.register_blueprint(nvc_platform_bp, url_prefix='/api/nvc-platform')
            logger.info("NVC Platform integration API routes registered successfully")
        except Exception as e:
            logger.error(f"Error registering NVC Platform integration routes: {str(e)}")
        
        # Initialize EDI Service
        try:
            from edi_integration import init_app as init_edi
            init_edi(app)
            logger.info("EDI Integration module initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing EDI Integration: {str(e)}")
            logger.warning("Application will run without EDI functionality")
        
        # Admin API Keys routes are registered through the admin blueprint
        # No need to register them separately
        
        # Register Customer Support routes
        try:
            from routes.customer_support_routes import customer_support_bp
            app.register_blueprint(customer_support_bp)
            logger.info("Customer Support routes registered successfully")
        except Exception as e:
            logger.error(f"Error registering Customer Support routes: {str(e)}")
            logger.warning("Application will run without AI Customer Support functionality")
            
        # Register Admin Tools routes
        try:
            from routes.admin_tools_routes import admin_tools_bp
            app.register_blueprint(admin_tools_bp)
            logger.info("Admin Tools routes registered successfully")
        except Exception as e:
            logger.error(f"Error registering Admin Tools routes: {str(e)}")
            logger.warning("Application will run without Admin Tools functionality")
            
        # Register Payment Processor routes
        try:
            from routes.payment_processor_routes import register_payment_processor_routes
            register_payment_processor_routes(app)
            logger.info("Payment Processor routes registered successfully")
        except Exception as e:
            logger.error(f"Error registering Payment Processor routes: {str(e)}")
            logger.warning("Application will run without Payment Processor functionality")
            
        # Register PayPal routes
        try:
            from routes.paypal_routes import register_paypal_blueprint
            register_paypal_blueprint(app)
            logger.info("PayPal routes registered successfully")
            
            # Ensure PayPal gateway exists
            try:
                from models import PaymentGateway, PaymentGatewayType
                paypal_gateway = PaymentGateway.query.filter_by(
                    gateway_type=PaymentGatewayType.PAYPAL, 
                    is_active=True
                ).first()
                
                if not paypal_gateway:
                    # Create a new PayPal gateway if it doesn't exist
                    paypal_gateway = PaymentGateway(
                        name="PayPal",
                        gateway_type=PaymentGatewayType.PAYPAL,
                        api_endpoint="https://api.paypal.com",
                        is_active=True,
                        is_test_mode=False,  # Production mode
                        description="PayPal payment gateway (Live mode)"
                    )
                else:
                    # Update existing gateway to live mode
                    paypal_gateway.is_test_mode = False
                    paypal_gateway.description = "PayPal payment gateway (Live mode)"
                    logger.info("Updated PayPal gateway to live mode")
                    db.session.add(paypal_gateway)
                    db.session.commit()
                    logger.info("Created new PayPal payment gateway")
            except Exception as e:
                logger.warning(f"Error setting up PayPal gateway: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error registering PayPal routes: {str(e)}")
            logger.warning("Application will run without PayPal functionality")
            
        # Register KTT Telex routes
        try:
            from routes.telex_routes import register_telex_routes
            register_telex_routes(app)
            logger.info("KTT Telex routes registered successfully")
        except Exception as e:
            logger.error(f"Error registering KTT Telex routes: {str(e)}")
            logger.warning("Application will run without KTT Telex functionality")
            
        # Register PDF routes
        try:
            from routes.pdf_routes import register_pdf_routes
            register_pdf_routes(app)
            logger.info("PDF routes registered successfully")
        except Exception as e:
            logger.error(f"Error registering PDF routes: {str(e)}")
            logger.warning("Application will run without PDF generation functionality")
            
        # Register PDF Reports routes
        try:
            from routes.pdf_reports import register_pdf_reports_routes
            register_pdf_reports_routes(app)
            logger.info("PDF Reports routes registered successfully")
        except Exception as e:
            logger.error(f"Error registering PDF Reports routes: {str(e)}")
            logger.warning("Application will run without PDF Reports functionality")

        # Register Stablecoin routes for peer-to-peer closed-loop system
        try:
            from routes.stablecoin_routes import register_routes
            register_routes(app)
            logger.info("NVC Token Stablecoin routes registered successfully")
        except Exception as e:
            logger.error(f"Error registering NVC Token Stablecoin routes: {str(e)}")
            logger.warning("Application will run without Stablecoin functionality")
            
        # Register Saint Crown Integration routes
        try:
            from routes.saint_crown_routes import saint_crown_bp
            app.register_blueprint(saint_crown_bp)
            logger.info("Saint Crown Integration routes registered successfully")
        except Exception as e:
            logger.error(f"Error registering Saint Crown Integration routes: {str(e)}")
            logger.warning("Application will run without Saint Crown Integration functionality")
            
        # Register Account Holder routes
        try:
            from routes.account_holder_routes import register_account_holder_routes
            register_account_holder_routes(app)
            logger.info("Account Holder routes registered successfully")
        except Exception as e:
            logger.error(f"Error registering Account Holder routes: {str(e)}")
            logger.warning("Application will run without Account Holder functionality")
            
        # Register Currency Exchange routes
        try:
            from routes.currency_exchange_routes import register_currency_exchange_routes
            register_currency_exchange_routes(app)
            logger.info("Currency Exchange routes registered successfully")
            
            # Register POS Payment routes
            try:
                from routes.pos_routes import pos_bp, register_routes
                app.register_blueprint(pos_bp)
                register_routes(app)
                logger.info("POS Payment routes registered successfully")
                
                # Register Stripe routes since we have the POS routes
                try:
                    from routes.stripe_routes import register_stripe_routes
                    register_stripe_routes(app)
                    logger.info("Stripe payment routes registered successfully")
                except ImportError as e:
                    logger.warning(f"Could not register Stripe routes: {str(e)}")
                except Exception as e:
                    logger.error(f"Error registering Stripe routes: {str(e)}")
            except ImportError as e:
                logger.warning(f"Could not register POS routes: {str(e)}")
            except Exception as e:
                logger.error(f"Error registering POS routes: {str(e)}")
        except Exception as e:
            logger.error(f"Error registering Currency Exchange routes: {str(e)}")
            logger.warning("Application will run without Currency Exchange functionality")
            
        # Register Trust Portfolio routes
        try:
            from routes.trust_routes import trust_bp
            app.register_blueprint(trust_bp)
            logger.info("Trust Portfolio routes registered successfully")
        except Exception as e:
            logger.error(f"Error registering Trust Portfolio routes: {str(e)}")
            logger.warning("Application will run without Trust Portfolio functionality")
            
        # Register API Documentation routes
        try:
            from routes.api_documentation_routes import api_docs_bp
            app.register_blueprint(api_docs_bp)
            logger.info("API Documentation routes registered successfully")
        except Exception as e:
            logger.error(f"Error registering API Documentation routes: {str(e)}")
            logger.warning("Application will run without API Documentation functionality")
            
        # Register Correspondent Banking routes
        try:
            from routes.correspondent_banking_routes import correspondent_bp
            app.register_blueprint(correspondent_bp)
            logger.info("Correspondent Banking routes registered successfully")
        except Exception as e:
            logger.error(f"Error registering Correspondent Banking routes: {str(e)}")
            logger.warning("Application will run without Correspondent Banking functionality")
        
        # Register Wire Transfer routes
        try:
            from routes.wire_transfer_routes import wire_transfer_bp
            app.register_blueprint(wire_transfer_bp)
            logger.info("Wire Transfer routes registered successfully")
        except Exception as e:
            logger.error(f"Error registering Wire Transfer routes: {str(e)}")
            logger.warning("Application will run without Wire Transfer functionality")
        
        # Register Document Download Center routes
        try:
            from routes.document_download_routes import document_download_bp
            app.register_blueprint(document_download_bp)
            logger.info("Document Download Center routes registered successfully")
        except Exception as e:
            logger.error(f"Error registering Document Download Center routes: {str(e)}")
            logger.warning("Application will run without Document Download Center functionality")
            
        # Register Client Dashboard routes
        try:
            from routes.client_dashboard_routes import register_client_dashboard_routes
            register_client_dashboard_routes(app)
            logger.info("Client Dashboard routes registered successfully")
        except Exception as e:
            logger.error(f"Error registering Client Dashboard routes: {str(e)}")
            logger.warning("Application will run without Client Dashboard functionality")
            
        # Register Public Download routes
        try:
            from routes.public_downloads import public_downloads_bp
            app.register_blueprint(public_downloads_bp)
            logger.info("Public download routes registered successfully")
        except Exception as e:
            logger.error(f"Error registering Public Download routes: {str(e)}")
            logger.warning("Application will run without Public Download functionality")
            
        # Register Direct Static File routes
        try:
            from static_routes import register_static_routes
            register_static_routes(app)
            logger.info("Direct static file routes registered successfully")
        except Exception as e:
            logger.error(f"Error registering Direct Static File routes: {str(e)}")
            logger.warning("Application will run without Direct Static File functionality")
        
        # Register Institutional Agreements routes
        try:
            from routes.agreements_routes import agreements_bp
            app.register_blueprint(agreements_bp)
            logger.info("Institutional Agreements routes registered successfully")
        except Exception as e:
            logger.error(f"Error registering Institutional Agreements routes: {str(e)}")
            logger.warning("Application will run without Institutional Agreements functionality")
        
        # Create PHP test integration user
        try:
            from auth import create_php_test_user
            php_test_user = create_php_test_user()
            if php_test_user:
                logger.info(f"PHP test integration user ready with API key: php_test_api_key")
            else:
                logger.warning("Failed to create PHP test integration user")
        except Exception as e:
            logger.error(f"Error creating PHP test user: {str(e)}")
        
        # Register Healthcheck routes
        try:
            from routes.healthcheck_routes import register_healthcheck_routes
            register_healthcheck_routes(app)
            logger.info("Healthcheck routes registered successfully")
        except Exception as e:
            logger.error(f"Error registering Healthcheck routes: {str(e)}")
            
        # Register Static routes for special files (favicon, robots.txt)
        try:
            from routes.static_routes import register_static_routes
            register_static_routes(app)
            logger.info("Static routes registered successfully")
        except Exception as e:
            logger.error(f"Error registering Static routes: {str(e)}")
            
        # Add a simple root healthcheck
        @app.route('/ping', methods=['GET'])
        def ping():
            """Simple ping endpoint that always returns a 200 response"""
            return jsonify({
                'status': 'ok',
                'timestamp': datetime.utcnow().isoformat()
            }), 200
            
        # Add an error timeout handler
        @app.errorhandler(504)
        def gateway_timeout(error):
            """Handler for gateway timeout errors"""
            logger.error(f"Gateway timeout error: {str(error)}")
            return render_template('errors/504.html'), 504
            
        # Add performance monitoring
        @app.before_request
        def start_timer():
            """Record request start time for performance monitoring"""
            from flask import g, request
            g.start_time = time.time()
            logger.debug(f"Request started: {request.method} {request.path}")
            
        @app.after_request
        def log_request_time(response):
            """Log request processing time for performance monitoring"""
            from flask import g, request
            if hasattr(g, 'start_time'):
                elapsed = time.time() - g.start_time
                logger.debug(f"Request completed: {request.method} {request.path} ({elapsed:.4f}s)")
                # Add timing header for debugging
                response.headers['X-Response-Time'] = f"{elapsed:.4f}s"
                # Add a warning header if the request took too long
                if elapsed > 5.0:
                    logger.warning(f"Slow request detected: {request.method} {request.path} ({elapsed:.4f}s)")
            return response
            
        # Initialize currency exchange rates including AFD1 and SFN
        try:
            from currency_exchange_service import CurrencyExchangeService
            # Create an instance and update rates
            exchange_service = CurrencyExchangeService(db)
            updated_count = exchange_service.update_exchange_rates()
            logger.info(f"Currency exchange rates initialized successfully, updated {updated_count} rates")
            
            # Update AFD1 rates (gold-backed)
            try:
                from saint_crown_integration import SaintCrownIntegration
                
                # Get gold price and calculate AFD1 value
                sc_integration = SaintCrownIntegration()
                gold_price, _ = sc_integration.get_gold_price()
                afd1_unit_value = gold_price * 0.1  # AFD1 = 10% of gold price
                
                # Update AFD1/USD rate
                from account_holder_models import CurrencyType
                CurrencyExchangeService.update_exchange_rate(
                    CurrencyType.AFD1, 
                    CurrencyType.USD, 
                    afd1_unit_value, 
                    "system_gold_price"
                )
                
                # Update NVCT/AFD1 rate
                nvct_to_afd1_rate = 1.0 / afd1_unit_value
                CurrencyExchangeService.update_exchange_rate(
                    CurrencyType.NVCT, 
                    CurrencyType.AFD1, 
                    nvct_to_afd1_rate, 
                    "system_gold_price"
                )
                logger.info(f"AFD1 exchange rates updated (1 AFD1 = ${afd1_unit_value:.2f} USD)")
            except Exception as e:
                logger.error(f"Error updating AFD1 exchange rates: {str(e)}")
                
            # Update SFN rates (1:1 with NVCT)
            try:
                # Set SFN/NVCT rate to 1:1 as requested
                CurrencyExchangeService.update_exchange_rate(
                    CurrencyType.SFN, 
                    CurrencyType.NVCT, 
                    1.0,  # 1 SFN = 1 NVCT (as requested)
                    "system_fixed_rate"
                )
                
                # Set NVCT/SFN rate to 1:1 for consistency
                CurrencyExchangeService.update_exchange_rate(
                    CurrencyType.NVCT, 
                    CurrencyType.SFN, 
                    1.0,  # 1 NVCT = 1 SFN
                    "system_fixed_rate"
                )
                
                # Set SFN/USD rate to 1:1 (derived from SFN = NVCT = USD)
                CurrencyExchangeService.update_exchange_rate(
                    CurrencyType.SFN, 
                    CurrencyType.USD, 
                    1.0,
                    "system_fixed_rate"
                )
                logger.info("SFN exchange rates updated (1:1 with NVCT)")
            except Exception as e:
                logger.error(f"Error updating SFN exchange rates: {str(e)}")
                
            # Use reduced system load approach for currency exchange rates
            try:
                # Apply optimizations to reduce system load
                from reduce_system_load import reduce_system_load
                reduce_system_load()
                
                # Use the fast memory cache instead of the regular one
                from fast_memory_cache import cache_exchange_rate
                
                # Set up essential rates in memory without frequent updates
                essential_rates = {
                    # Core rates only
                    ('NVCT', 'USD'): 1.0,
                    ('USD', 'NVCT'): 1.0,
                    ('NVCT', 'AFD1'): 0.00294,
                    ('AFD1', 'NVCT'): 340.136,
                    ('NVCT', 'SFN'): 1.0,
                    ('SFN', 'NVCT'): 1.0,
                }
                
                # Cache these rates in memory
                for (from_curr, to_curr), rate in essential_rates.items():
                    cache_exchange_rate(from_curr, to_curr, rate)
                    
                # Add currency service module patching
                try:
                    # This approach is safer - use sys.modules to redirect imports
                    import sys
                    import fast_memory_cache
                    
                    # Replace any future imports of memory_cache
                    sys.modules['memory_cache'] = fast_memory_cache
                    
                    # Disable automatic updates in currency_exchange_service
                    if 'currency_exchange_service' in sys.modules:
                        # Get the module reference
                        currency_module = sys.modules['currency_exchange_service']
                        
                        # If the module has a CurrencyExchangeService class or object
                        if hasattr(currency_module, 'CurrencyExchangeService'):
                            service = currency_module.CurrencyExchangeService
                            
                            # Replace the update method with a no-op function if it exists
                            if hasattr(service, 'update_exchange_rate'):
                                original_update = service.update_exchange_rate
                                
                                # Create a lightweight version that does minimal work
                                def lightweight_update(*args, **kwargs):
                                    # Just cache the rate in memory without database operations
                                    if len(args) >= 3:
                                        from_curr = str(args[0])
                                        to_curr = str(args[1])
                                        rate = float(args[2])
                                        fast_memory_cache.cache_exchange_rate(from_curr, to_curr, rate)
                                    return None
                                
                                # Apply the patch
                                service.update_exchange_rate = lightweight_update
                                logger.info("Currency exchange rate updates optimized")
                except Exception as e:
                    logger.warning(f"Could not optimize currency service: {str(e)}")
                
                logger.info("Applied high-performance currency exchange configuration")
                
            except Exception as e:
                logger.error(f"Error applying system load optimizations: {str(e)}")
                logger.warning("Continuing with standard initialization")
                
                try:
                    # Process only key African currencies as fallback
                    african_currency_rates = {
                        # Only include currencies supported in enum
                        "NGN": 1500.00,     # Nigerian Naira
                        "KES": 132.05,      # Kenyan Shilling
                        "ZAR": 18.50,       # South African Rand
                        "EGP": 47.25,       # Egyptian Pound
                    }
                    
                    african_currencies_updated = 0
                    
                    # Process key African currencies
                    for currency_code, usd_rate in african_currency_rates.items():
                        try:
                            # Get the enum value for this currency
                            currency_enum = getattr(CurrencyType, currency_code)
                            
                            # Update USD to African currency rate
                            CurrencyExchangeService.update_exchange_rate(
                                CurrencyType.USD,
                                currency_enum,
                                usd_rate,
                                "system_african_rates"
                            )
                            
                            # Update NVCT to African currency rate (1:1 with USD)
                            CurrencyExchangeService.update_exchange_rate(
                                CurrencyType.NVCT,
                                currency_enum,
                                usd_rate,
                                "system_african_rates"
                            )
                            
                            african_currencies_updated += 1
                        except Exception as e:
                            logger.debug(f"Error updating rates for {currency_code}: {str(e)}")
                    
                    logger.info(f"African currency exchange rates initialized with {african_currencies_updated} currencies")
                    
                except Exception as e:
                    logger.error(f"Error initializing African currency exchange rates: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error initializing currency exchange rates: {str(e)}")
            logger.warning("Application will run with default currency exchange rates")

        # Register institutional routes
        try:
            from routes.institutional_routes import register_routes as register_institutional_routes
            register_institutional_routes(app)
            logger.info("Institutional routes registered successfully")
        except ImportError:
            logger.warning("Institutional routes module not found")
        except Exception as e:
            logger.error(f"Error registering institutional routes: {str(e)}")

        logger.info("Application initialized successfully")

    return app

# Initialize the app instance
app = create_app()
