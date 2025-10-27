# TMDB API Key Guide

This guide provides step-by-step instructions for obtaining and using a TMDB (The Movie Database) API key for the AniVault project.

## Table of Contents

1. [Overview](#overview)
2. [Getting Your TMDB API Key](#getting-your-tmdb-api-key)
3. [Setting Up Your API Key](#setting-up-your-api-key)
4. [Validating Your API Key](#validating-your-api-key)
5. [Troubleshooting](#troubleshooting)
6. [Best Practices](#best-practices)
7. [Rate Limits and Usage Guidelines](#rate-limits-and-usage-guidelines)

## Overview

The Movie Database (TMDB) API provides access to comprehensive movie and TV show information, including metadata, images, ratings, and more. AniVault uses this API to enhance anime collection management with rich metadata.

### What You'll Need

- A valid email address
- Internet connection
- Basic understanding of API concepts (helpful but not required)

### API Key Types

TMDB offers two types of API keys:
- **API Key (v3)**: Most common, used for read operations
- **Bearer Token**: Used for write operations (not needed for AniVault)

For AniVault, you only need the **API Key (v3)**.

## Getting Your TMDB API Key

### Step 1: Create a TMDB Account

1. Visit [The Movie Database](https://www.themoviedb.org/)
2. Click **"Join TMDb"** in the top-right corner
3. Fill out the registration form:
   - Username (choose a unique username)
   - Email address
   - Password
   - Confirm password
4. Click **"Sign Up"**
5. Check your email and click the verification link

### Step 2: Request an API Key

1. Log in to your TMDB account
2. Go to your account settings by clicking your profile picture/username
3. Navigate to **Settings** → **API**
4. You'll see the API section with options:
   - **Developer API**: For personal projects
   - **Commercial API**: For commercial applications
5. For AniVault, select **"Developer API"**
6. Fill out the application form:

   **Application Details:**
   - **Application Name**: `AniVault`
   - **Application Summary**: `Personal anime collection management tool`
   - **Application URL**: Leave blank or add your GitHub repo URL

   **Contact Information:**
   - **Name**: Your full name
   - **Email**: Your email address
   - **Phone**: Optional

7. Read and accept the Terms of Use
8. Click **"Submit"**

### Step 3: Get Your API Key

1. After submitting your application, you'll be redirected to your API settings
2. Your API Key (v3) will be displayed
3. **Important**: Copy and save this key securely - you won't be able to see it again!

The API key will look something like this:
```
c479f9ce20ccbcc06dbcce991a238120
```

## Setting Up Your API Key

### Method 1: Environment File (.env) - Recommended

1. Create a `.env` file in your AniVault project root directory
2. Add your API key:

```env
# TMDB API Configuration
TMDB_API_KEY=your_api_key_here
```

3. Make sure `.env` is in your `.gitignore` file to keep your key secure

### Method 2: Configuration File

1. Open `tmdb_config.py` in your project
2. Replace the placeholder with your actual API key:

```python
TMDB_API_KEY = "your_actual_api_key_here"  # pragma: allowlist secret
```

### Method 3: Environment Variable

Set the environment variable in your system:

**Windows (Command Prompt):**
```cmd
set TMDB_API_KEY=your_api_key_here
```

**Windows (PowerShell):**
```powershell
$env:TMDB_API_KEY="your_api_key_here"  # pragma: allowlist secret
```

**Linux/macOS:**
```bash
export TMDB_API_KEY=your_api_key_here
```

## Validating Your API Key

Use the provided validation script to test your API key:

```bash
# Test API key from .env file
python check_api_key.py --file .env

# Test API key directly
python check_api_key.py your_api_key_here

# Test with verbose output
python check_api_key.py --file .env --verbose
```

### Expected Output

If your API key is valid, you should see:
```
✅ API Key Status: VALID
📊 HTTP Status: 200
🎉 Your API key is working correctly!
```

## Troubleshooting

### Common Issues and Solutions

#### 1. "Unauthorized - Invalid API key" (HTTP 401)

**Causes:**
- Incorrect API key
- API key not copied correctly
- Using Bearer token instead of API key

**Solutions:**
- Double-check your API key for typos
- Make sure you're using the API Key (v3), not the Bearer token
- Try copying the key again from TMDB settings

#### 2. "Forbidden" (HTTP 403)

**Causes:**
- API key doesn't have required permissions
- Application not approved yet

**Solutions:**
- Wait for TMDB to approve your application (usually instant for developer keys)
- Check if you selected the correct API type (Developer vs Commercial)

#### 3. "Rate limit exceeded" (HTTP 429)

**Causes:**
- Too many API requests in a short time
- Exceeded daily/hourly limits

**Solutions:**
- Wait before making more requests
- Implement rate limiting in your application
- Consider caching API responses

#### 4. Connection Errors

**Causes:**
- Internet connection issues
- TMDB API server problems

**Solutions:**
- Check your internet connection
- Visit [TMDB Status Page](https://status.themoviedb.org/) for server status
- Try again later

#### 5. API Key Not Found in File

**Causes:**
- File doesn't exist
- Wrong file format
- API key not in expected location

**Solutions:**
- Ensure the file exists and is readable
- Check file format (should be plain text)
- Verify the API key is on a line starting with `TMDB_API_KEY=` or `API_KEY=`

### Validation Script Troubleshooting

If the validation script fails:

1. **Check Python Dependencies:**
   ```bash
   pip install requests
   ```

2. **Verify File Permissions:**
   - Make sure you have read access to the `.env` file
   - Check that the script has execute permissions

3. **Test with Direct API Key:**
   ```bash
   python check_api_key.py your_api_key_here
   ```

## Best Practices

### Security

1. **Never commit API keys to version control**
   - Add `.env` to `.gitignore`
   - Use environment variables in production
   - Consider using secret management tools for production

2. **Keep your API key private**
   - Don't share it in public forums or code
   - Don't include it in screenshots or documentation
   - Regenerate if accidentally exposed

3. **Use different keys for different environments**
   - Development key for testing
   - Production key for live applications

### Performance

1. **Implement caching**
   - Cache API responses to reduce requests
   - Use appropriate cache expiration times
   - Consider local database for frequently accessed data

2. **Respect rate limits**
   - Implement request throttling
   - Use exponential backoff for retries
   - Monitor your usage in TMDB dashboard

3. **Optimize requests**
   - Only request needed data
   - Use appropriate language settings
   - Batch requests when possible

### Error Handling

1. **Implement proper error handling**
   - Handle network timeouts
   - Retry failed requests with backoff
   - Log errors for debugging

2. **Graceful degradation**
   - Continue working without API data if needed
   - Provide fallback options
   - Inform users of API issues

## Rate Limits and Usage Guidelines

### TMDB API Limits

- **Rate Limit**: 40 requests per 10 seconds per IP
- **Daily Limit**: Varies by account type (usually generous for personal use)
- **Burst Limit**: 20 requests per second

### Monitoring Usage

1. **Check your usage in TMDB dashboard**
2. **Monitor response headers for rate limit info**
3. **Implement usage tracking in your application**

### Optimization Tips

1. **Use the configuration endpoint to check available image sizes**
2. **Request only the data you need**
3. **Use appropriate language codes for your audience**
4. **Cache results locally to minimize API calls**

## Additional Resources

- [TMDB API Documentation](https://developers.themoviedb.org/3/getting-started/introduction)
- [TMDB API Reference](https://developers.themoviedb.org/3)
- [TMDB Community Forums](https://www.themoviedb.org/talk)
- [AniVault Project Repository](https://github.com/yourusername/anivault)

## Support

If you encounter issues not covered in this guide:

1. Check the [TMDB API documentation](https://developers.themoviedb.org/3)
2. Search the [TMDB community forums](https://www.themoviedb.org/talk)
3. Create an issue in the AniVault repository
4. Contact the AniVault development team

---

**Last Updated**: January 2025
**Version**: 1.0
**Compatible with**: TMDB API v3, AniVault v0.1.0+
