# reCAPTCHA v3 Setup

This project uses Google reCAPTCHA v3 (score-based) to protect sensitive actions.

## Useful links

- Admin Console (create keys): [Google reCAPTCHA Admin](https://www.google.com/recaptcha/admin/create)
- Cloud Console product pages (optional):
  - [reCAPTCHA (standard)](https://console.cloud.google.com/marketplace/product/google-cloud-platform/recaptcha)
  - [reCAPTCHA Enterprise](https://console.cloud.google.com/marketplace/product/google/recaptchaenterprise.googleapis.com)

## Environment variables

### Frontend (.env)

```bash
VITE_RECAPTCHA_SITE_KEY=your_site_key
```

### Backend (.env)

```bash
RECAPTCHA_SECRET_KEY=your_secret_key
RECAPTCHA_MIN_SCORE=0.5  # Optional, defaults to 0.5
```

## Domain registration

Register the following domains in the reCAPTCHA Admin:

- app.brikli.com
- localhost (for development)
- Any Porter preview subdomains you use
