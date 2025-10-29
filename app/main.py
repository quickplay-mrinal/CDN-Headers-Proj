"""Interactive FastAPI application for CDN Headers Project"""

import os
import json
import jwt
import boto3
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
import uvicorn

# Initialize FastAPI app
app = FastAPI(
    title="QP-IAC CDN Headers Application",
    description="Interactive application with JWT validation and CDN integration",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Pydantic models
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

class UserInfo(BaseModel):
    username: str
    authenticated: bool
    request_id: Optional[str] = None
    cdn_validated: Optional[bool] = False

# Global variables for caching
jwt_secret_cache = None
cache_timestamp = None
CACHE_TTL = 300  # 5 minutes

def get_jwt_secret():
    """Get JWT secret from AWS Secrets Manager with caching"""
    global jwt_secret_cache, cache_timestamp
    
    current_time = datetime.utcnow().timestamp()
    
    # Check if cache is valid
    if jwt_secret_cache and cache_timestamp and (current_time - cache_timestamp) < CACHE_TTL:
        return jwt_secret_cache
    
    try:
        secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
        secret_arn = os.environ.get('JWT_SECRET_ARN')
        
        if not secret_arn:
            raise Exception("JWT_SECRET_ARN environment variable not set")
        
        response = secrets_client.get_secret_value(SecretArn=secret_arn)
        secret_data = json.loads(response['SecretString'])
        
        jwt_secret_cache = secret_data['jwt_secret_key']
        cache_timestamp = current_time
        
        return jwt_secret_cache
        
    except Exception as e:
        # Fallback for local development
        return "fallback-secret-key-for-development"

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token"""
    try:
        token = credentials.credentials
        secret = get_jwt_secret()
        
        payload = jwt.decode(token, secret, algorithms=['HS256'])
        
        # Check expiration
        if payload.get('exp', 0) < datetime.utcnow().timestamp():
            raise HTTPException(status_code=401, detail="Token expired")
        
        return payload
        
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token validation error: {str(e)}")

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main application page"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>QP-IAC CDN Headers Application</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .header { text-align: center; color: #333; margin-bottom: 30px; }
            .form-group { margin-bottom: 20px; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
            button { background: #007bff; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; margin-right: 10px; }
            button:hover { background: #0056b3; }
            .result { margin-top: 20px; padding: 15px; border-radius: 5px; }
            .success { background: #d4edda; border: 1px solid #c3e6cb; color: #155724; }
            .error { background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; }
            .info { background: #d1ecf1; border: 1px solid #bee5eb; color: #0c5460; }
            .token-display { word-break: break-all; font-family: monospace; font-size: 12px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔐 QP-IAC CDN Headers Application</h1>
                <p>Interactive JWT Authentication & CDN Validation System</p>
            </div>
            
            <div class="form-group">
                <h3>🔑 Login & Get JWT Token</h3>
                <label for="username">Username:</label>
                <input type="text" id="username" value="admin" placeholder="Enter username">
                
                <label for="password">Password:</label>
                <input type="password" id="password" value="password123" placeholder="Enter password">
                
                <button onclick="login()">Login & Get Token</button>
            </div>
            
            <div class="form-group">
                <h3>🌐 Test Protected Endpoints</h3>
                <label for="token">JWT Token:</label>
                <input type="text" id="token" placeholder="Paste JWT token here">
                
                <button onclick="testUserInfo()">Get User Info</button>
                <button onclick="testProtected()">Test Protected Route</button>
                <button onclick="testHeaders()">Check Headers</button>
            </div>
            
            <div id="result"></div>
        </div>
        
        <script>
            async function login() {
                const username = document.getElementById('username').value;
                const password = document.getElementById('password').value;
                
                try {
                    const response = await fetch('/auth/login', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ username, password })
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok) {
                        document.getElementById('token').value = data.access_token;
                        showResult('success', `✅ Login successful!<br><strong>Token:</strong><br><div class="token-display">${data.access_token}</div><br><strong>Expires in:</strong> ${data.expires_in} seconds`);
                    } else {
                        showResult('error', `❌ Login failed: ${data.detail || data.error}`);
                    }
                } catch (error) {
                    showResult('error', `❌ Network error: ${error.message}`);
                }
            }
            
            async function testUserInfo() {
                const token = document.getElementById('token').value;
                
                if (!token) {
                    showResult('error', '❌ Please provide a JWT token');
                    return;
                }
                
                try {
                    const response = await fetch('/auth/me', {
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok) {
                        showResult('success', `✅ User Info Retrieved:<br><strong>Username:</strong> ${data.username}<br><strong>Authenticated:</strong> ${data.authenticated}<br><strong>Request ID:</strong> ${data.request_id}<br><strong>CDN Validated:</strong> ${data.cdn_validated}`);
                    } else {
                        showResult('error', `❌ Failed: ${data.detail}`);
                    }
                } catch (error) {
                    showResult('error', `❌ Network error: ${error.message}`);
                }
            }
            
            async function testProtected() {
                const token = document.getElementById('token').value;
                
                if (!token) {
                    showResult('error', '❌ Please provide a JWT token');
                    return;
                }
                
                try {
                    const response = await fetch('/api/protected', {
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok) {
                        showResult('success', `✅ Protected Route Access Granted:<br><strong>Message:</strong> ${data.message}<br><strong>Timestamp:</strong> ${data.timestamp}<br><strong>User:</strong> ${data.user}`);
                    } else {
                        showResult('error', `❌ Access Denied: ${data.detail}`);
                    }
                } catch (error) {
                    showResult('error', `❌ Network error: ${error.message}`);
                }
            }
            
            async function testHeaders() {
                try {
                    const response = await fetch('/debug/headers');
                    const data = await response.json();
                    
                    let headerInfo = '<strong>Request Headers:</strong><br>';
                    for (const [key, value] of Object.entries(data.headers)) {
                        headerInfo += `<strong>${key}:</strong> ${value}<br>`;
                    }
                    
                    showResult('info', `ℹ️ Header Information:<br>${headerInfo}<br><strong>CDN Validated:</strong> ${data.cdn_validated}<br><strong>Edge Processed:</strong> ${data.edge_processed}`);
                } catch (error) {
                    showResult('error', `❌ Network error: ${error.message}`);
                }
            }
            
            function showResult(type, message) {
                const resultDiv = document.getElementById('result');
                resultDiv.className = `result ${type}`;
                resultDiv.innerHTML = message;
            }
        </script>
    </body>
    </html>
    """

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "qp-iac-cdn-headers-app"
    }

@app.post("/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Authenticate user and return JWT token"""
    
    # Simple authentication (in production, use proper auth service)
    if request.username != "admin" or request.password != "password123":
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    try:
        secret = get_jwt_secret()
        
        # Generate JWT token
        payload = {
            'sub': request.username,
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(hours=24),
            'iss': 'qp-iac-cdn-headers',
            'aud': 'cdn-alb-communication'
        }
        
        token = jwt.encode(payload, secret, algorithm='HS256')
        
        return TokenResponse(
            access_token=token,
            token_type="Bearer",
            expires_in=86400
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token generation failed: {str(e)}")

@app.get("/auth/me", response_model=UserInfo)
async def get_user_info(
    request: Request,
    payload: dict = Depends(verify_token),
    x_cdn_validated: Optional[str] = Header(None, alias="x-cdn-validated"),
    x_request_id: Optional[str] = Header(None, alias="x-request-id")
):
    """Get current user information"""
    
    return UserInfo(
        username=payload.get('sub', 'unknown'),
        authenticated=True,
        request_id=x_request_id,
        cdn_validated=x_cdn_validated == "true"
    )

@app.get("/api/protected")
async def protected_route(
    request: Request,
    payload: dict = Depends(verify_token),
    x_cdn_validated: Optional[str] = Header(None, alias="x-cdn-validated"),
    x_edge_processed: Optional[str] = Header(None, alias="x-edge-processed")
):
    """Protected API endpoint"""
    
    return {
        "message": "Access granted to protected resource",
        "user": payload.get('sub', 'unknown'),
        "timestamp": datetime.utcnow().isoformat(),
        "cdn_validated": x_cdn_validated == "true",
        "edge_processed": x_edge_processed == "true",
        "request_source": "CDN" if x_cdn_validated else "Direct"
    }

@app.get("/debug/headers")
async def debug_headers(request: Request):
    """Debug endpoint to show all headers"""
    
    headers = dict(request.headers)
    
    return {
        "headers": headers,
        "cdn_validated": headers.get("x-cdn-validated") == "true",
        "edge_processed": headers.get("x-edge-processed") == "true",
        "request_id": headers.get("x-request-id"),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/status")
async def api_status():
    """API status endpoint"""
    
    return {
        "api_status": "operational",
        "version": "1.0.0",
        "environment": os.environ.get("ENVIRONMENT", "development"),
        "timestamp": datetime.utcnow().isoformat(),
        "features": {
            "jwt_validation": True,
            "cdn_integration": True,
            "secrets_rotation": True,
            "header_validation": True
        }
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)