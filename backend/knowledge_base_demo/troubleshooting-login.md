---
category: troubleshooting
title: Login Issues and Authentication Troubleshooting
tags: [login, authentication, password-reset, 2fa, troubleshooting]
---

# Login Issues and Authentication Troubleshooting

This guide covers common login and authentication issues that CloudStream users may encounter.

## Password Reset

If you've forgotten your password or are unable to log in, follow these steps:

### Standard Password Reset Process

1. Navigate to the CloudStream login page
2. Click the "Forgot Password" link below the login form
3. Enter your registered email address
4. Check your email for the password reset link
5. Click the link and create a new password
6. Return to the login page and sign in with your new password

### Email Not Arriving

If you don't receive the password reset email within 5 minutes:

**Check Spam Folder:** Password reset emails sometimes get filtered as spam. Check your spam/junk folder for emails from noreply@cloudstream.com

**Verify Account Type:** If your account was created using Google Authentication (SSO), you won't receive a password reset email. Instead, click "Sign in with Google" on the login page.

**Check Email Address:** Ensure you're using the correct email address associated with your CloudStream account.

**Still Having Issues?** Contact support at support@cloudstream.com with your account email address.

## Two-Factor Authentication (2FA)

Two-Factor Authentication adds an extra layer of security to your CloudStream account.

### Lost 2FA Device

If you've lost access to your 2FA device (phone, authenticator app, etc.):

**Use Recovery Code:** During 2FA setup, you were provided with a recovery code. Enter this code on the 2FA verification screen to regain access.

**Recovery Code Format:** The recovery code is a 16-character alphanumeric string (e.g., ABCD-1234-EFGH-5678)

**Lost Recovery Code:** If you've lost both your 2FA device and recovery code, you'll need to contact human support for account recovery. This process requires identity verification and may take 24-48 hours.

### Escalation Required

If a user has lost both their 2FA device and recovery code, this issue must be escalated to human support. The AI agent cannot disable 2FA for security reasons.

**Escalation Process:**
1. Verify the user's identity (account email, last payment date, etc.)
2. Create a support ticket with priority: High
3. Tag the ticket with "2FA-Recovery" and "Identity-Verification-Required"
4. Inform the user that human support will contact them within 24 hours

## Google Authentication (SSO)

Users who signed up using "Sign in with Google" don't have a CloudStream password.

**To Log In:** Always use the "Sign in with Google" button on the login page.

**Switching to Password:** If you want to add a password to your account, go to Settings > Security > Add Password after logging in with Google.
