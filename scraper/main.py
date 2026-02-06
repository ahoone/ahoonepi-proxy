from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import os

app = FastAPI(
    title="Scraper API",
    description="Web scraping service with Selenium",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
async def root():
    """Landing page"""
    return """
    <!DOCTYPE html>
    <html>
        <head>
            <title>Scraper API</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    max-width: 800px;
                    margin: 50px auto;
                    padding: 20px;
                    background: #f5f5f5;
                }
                .container {
                    background: white;
                    padding: 40px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                h1 { color: #333; margin-top: 0; }
                .endpoint {
                    background: #f8f9fa;
                    padding: 15px;
                    margin: 10px 0;
                    border-radius: 4px;
                    border-left: 4px solid #007bff;
                }
                code {
                    background: #e9ecef;
                    padding: 2px 6px;
                    border-radius: 3px;
                    font-family: monospace;
                }
                .status { color: #28a745; font-weight: bold; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 Scraper API</h1>
                <p class="status">✓ Service Running</p>
                
                <h2>Available Endpoints</h2>
                
                <div class="endpoint">
                    <strong>GET /health</strong>
                    <p>Check service health and Chrome status</p>
                </div>
                
                <div class="endpoint">
                    <strong>GET /docs</strong>
                    <p>Interactive API documentation (Swagger UI)</p>
                </div>
                
                <div class="endpoint">
                    <strong>GET /redoc</strong>
                    <p>Alternative API documentation</p>
                </div>
                
                <h2>Quick Start</h2>
                <p>Visit <a href="/docs">/docs</a> to explore the API interactively.</p>
            </div>
        </body>
    </html>
    """

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    # Check if Chrome/Chromium is available
    chrome_available = False
    chrome_path = None
    
    # Check common Chrome/Chromium paths
    paths = [
        "/usr/bin/google-chrome",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser"
    ]
    
    for path in paths:
        if os.path.exists(path):
            chrome_available = True
            chrome_path = path
            break
    
    return {
        "status": "healthy",
        "service": "scraper-api",
        "chrome_available": chrome_available,
        "chrome_path": chrome_path,
        "display": os.getenv("DISPLAY", "not set")
    }

@app.get("/test-scrape")
async def test_scrape():
    """Test endpoint - returns sample scraping configuration"""
    return {
        "message": "Scraper configured and ready",
        "capabilities": [
            "Headless Chrome/Chromium",
            "JavaScript rendering",
            "Cookie handling",
            "Screenshot capture"
        ],
        "note": "Add your scraping endpoints here"
    }
