"""
CloudFront Module - Creates CloudFront distribution and function for JWT validation
CloudFront is a global service but configured from any region
"""
import pulumi_aws as aws

def create_jwt_function(config):
    """Create CloudFront Function for JWT validation"""
    
    project_name = config["project_name"]
    
    # Enhanced CloudFront Function code for JWT validation
    cloudfront_function_code = """
function handler(event) {
    var request = event.request;
    var headers = request.headers;
    
    // Check for Authorization header with JWT
    if (!headers.authorization) {
        return {
            statusCode: 401,
            statusDescription: 'Unauthorized',
            body: {
                encoding: 'text',
                data: JSON.stringify({
                    error: 'Missing Authorization header',
                    message: 'JWT token required for access',
                    timestamp: new Date().toISOString(),
                    region: 'Global CloudFront'
                })
            },
            headers: {
                'content-type': { value: 'application/json' },
                'cache-control': { value: 'no-cache' },
                'x-jwt-validation': { value: 'failed-missing-header' }
            }
        };
    }
    
    var authHeader = headers.authorization.value;
    
    // Validate Bearer token format
    if (!authHeader.startsWith('Bearer ')) {
        return {
            statusCode: 401,
            statusDescription: 'Unauthorized',
            body: {
                encoding: 'text',
                data: JSON.stringify({
                    error: 'Invalid Authorization format',
                    message: 'Bearer token required',
                    expected: 'Authorization: Bearer <jwt-token>',
                    timestamp: new Date().toISOString()
                })
            },
            headers: {
                'content-type': { value: 'application/json' },
                'cache-control': { value: 'no-cache' },
                'x-jwt-validation': { value: 'failed-invalid-format' }
            }
        };
    }
    
    var token = authHeader.substring(7); // Remove 'Bearer '
    
    // JWT structure validation (header.payload.signature)
    var parts = token.split('.');
    if (parts.length !== 3) {
        return {
            statusCode: 401,
            statusDescription: 'Unauthorized',
            body: {
                encoding: 'text',
                data: JSON.stringify({
                    error: 'Invalid JWT format',
                    message: 'JWT must have 3 parts (header.payload.signature)',
                    received_parts: parts.length,
                    timestamp: new Date().toISOString()
                })
            },
            headers: {
                'content-type': { value: 'application/json' },
                'cache-control': { value: 'no-cache' },
                'x-jwt-validation': { value: 'failed-invalid-structure' }
            }
        };
    }
    
    // Validate base64 encoding of JWT parts
    try {
        // Decode header and payload to validate structure
        var header = JSON.parse(atob(parts[0]));
        var payload = JSON.parse(atob(parts[1]));
        
        // Basic JWT validation
        if (!header.alg || !header.typ) {
            throw new Error('Invalid JWT header - missing alg or typ');
        }
        
        if (!payload.sub && !payload.user && !payload.username) {
            throw new Error('Invalid JWT payload - missing subject/user');
        }
        
        // Check expiration if present
        if (payload.exp && payload.exp < Math.floor(Date.now() / 1000)) {
            return {
                statusCode: 401,
                statusDescription: 'Unauthorized',
                body: {
                    encoding: 'text',
                    data: JSON.stringify({
                        error: 'Token expired',
                        message: 'JWT token has expired',
                        expired_at: new Date(payload.exp * 1000).toISOString(),
                        current_time: new Date().toISOString()
                    })
                },
                headers: {
                    'content-type': { value: 'application/json' },
                    'cache-control': { value: 'no-cache' },
                    'x-jwt-validation': { value: 'failed-expired' }
                }
            };
        }
        
        // Extract user information
        var userId = payload.sub || payload.user || payload.username || 'unknown';
        var userName = payload.name || payload.username || userId;
        
    } catch (e) {
        return {
            statusCode: 401,
            statusDescription: 'Unauthorized',
            body: {
                encoding: 'text',
                data: JSON.stringify({
                    error: 'Invalid JWT structure',
                    message: 'JWT parsing failed: ' + e.message,
                    timestamp: new Date().toISOString()
                })
            },
            headers: {
                'content-type': { value: 'application/json' },
                'cache-control': { value: 'no-cache' },
                'x-jwt-validation': { value: 'failed-parsing-error' }
            }
        };
    }
    
    // Add validated user info to request headers for ALB
    request.headers['x-validated-user'] = { value: userId };
    request.headers['x-validated-name'] = { value: userName };
    request.headers['x-auth-method'] = { value: 'jwt-cloudfront-function' };
    request.headers['x-jwt-validated'] = { value: 'true' };
    request.headers['x-jwt-validation-time'] = { value: new Date().toISOString() };
    request.headers['x-cloudfront-region'] = { value: 'global' };
    
    return request;
}

// Helper function for base64 decoding (CloudFront Functions compatible)
function atob(str) {
    var chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
    var result = '';
    var i = 0;
    
    // Remove any non-base64 characters
    str = str.replace(/[^A-Za-z0-9+/]/g, '');
    
    while (i < str.length) {
        var a = chars.indexOf(str.charAt(i++));
        var b = chars.indexOf(str.charAt(i++));
        var c = chars.indexOf(str.charAt(i++));
        var d = chars.indexOf(str.charAt(i++));
        
        if (a === -1 || b === -1) break;
        
        var bitmap = (a << 18) | (b << 12) | ((c === -1 ? 0 : c) << 6) | (d === -1 ? 0 : d);
        
        result += String.fromCharCode((bitmap >> 16) & 255);
        if (c !== -1 && c !== 64) result += String.fromCharCode((bitmap >> 8) & 255);
        if (d !== -1 && d !== 64) result += String.fromCharCode(bitmap & 255);
    }
    
    return result;
}
"""
    
    # CloudFront Function for JWT validation
    cloudfront_function = aws.cloudfront.Function("jwt-validator",
        name=f"{project_name}-jwt-validator",
        runtime="cloudfront-js-1.0",
        comment=f"JWT validation function for {project_name} - secure CDN-to-ALB communication",
        publish=True,
        code=cloudfront_function_code
    )
    
    return cloudfront_function

def create_cloudfront_distribution(config, alb_dns_name, cloudfront_function_arn):
    """Create CloudFront distribution with JWT validation"""
    
    project_name = config["project_name"]
    common_tags = config["common_tags"]
    cloudfront_config = config["cloudfront_config"]
    
    # CloudFront Distribution with JWT Validation
    cloudfront_distribution = aws.cloudfront.Distribution("jwt-cloudfront",
        aliases=[],
        comment=f"Secure CDN with JWT validation at edge - {project_name}",
        default_cache_behavior=aws.cloudfront.DistributionDefaultCacheBehaviorArgs(
            allowed_methods=["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"],
            cached_methods=["GET", "HEAD"],
            target_origin_id="alb-origin",
            compress=True,
            viewer_protocol_policy="redirect-to-https",
            cache_policy_id=cloudfront_config["cache_policy_id"],  # CachingDisabled for demo
            function_associations=[
                aws.cloudfront.DistributionDefaultCacheBehaviorFunctionAssociationArgs(
                    event_type="viewer-request",
                    function_arn=cloudfront_function_arn
                )
            ]
        ),
        origins=[
            aws.cloudfront.DistributionOriginArgs(
                domain_name=alb_dns_name,
                origin_id="alb-origin",
                custom_origin_config=aws.cloudfront.DistributionOriginCustomOriginConfigArgs(
                    http_port=80,
                    https_port=443,
                    origin_protocol_policy="http-only",
                    origin_ssl_protocols=["TLSv1.2"],
                    origin_keepalive_timeout=5,
                    origin_read_timeout=30
                )
            )
        ],
        restrictions=aws.cloudfront.DistributionRestrictionsArgs(
            geo_restriction=aws.cloudfront.DistributionRestrictionsGeoRestrictionArgs(
                restriction_type="none"
            )
        ),
        viewer_certificate=aws.cloudfront.DistributionViewerCertificateArgs(
            cloudfront_default_certificate=True
        ),
        enabled=True,
        price_class=cloudfront_config["price_class"],  # Cost optimization
        tags={**common_tags, "Name": f"{project_name}-jwt-cloudfront"}
    )
    
    return cloudfront_distribution

def create_sample_jwt():
    """Create a sample JWT token for testing"""
    # Sample JWT with long expiration for demo purposes
    # In production, use proper JWT libraries with secure signing
    sample_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkZW1vLXVzZXIiLCJ1c2VybmFtZSI6ImRlbW8tdXNlciIsIm5hbWUiOiJKV1QgRGVtbyBVc2VyIiwiaWF0IjoxNTE2MjM5MDIyLCJleHAiOjk5OTk5OTk5OTl9.8VH1pNkNAjokT6Qa9-stQjs9TJ_5c-KJ6RM9-hjdgaY"
    
    return sample_jwt