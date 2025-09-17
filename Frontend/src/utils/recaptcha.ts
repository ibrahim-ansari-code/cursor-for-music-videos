// Lightweight helper to execute Google reCAPTCHA v3 without requiring React hooks

export async function executeRecaptchaAction(action: string): Promise<string | null> {
  const siteKey = import.meta.env.VITE_RECAPTCHA_SITE_KEY as string | undefined;
  if (!siteKey) return null;

  const grecaptcha: any = (window as any).grecaptcha;
  if (!grecaptcha || typeof grecaptcha.ready !== 'function') return null;

  return new Promise<string | null>((resolve) => {
    try {
      grecaptcha.ready(async () => {
        try {
          const token: string = await grecaptcha.execute(siteKey, { action });
          resolve(token);
        } catch (e) {
          resolve(null);
        }
      });
    } catch {
      resolve(null);
    }
  });
}


