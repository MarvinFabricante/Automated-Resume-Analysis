import React, { useEffect, useRef, useState } from 'react';
import { useDispatch } from 'react-redux';
import api from '../../services/api';
import { apiSlice } from '../../redux/api/apiSlice';
import { setCredentials } from '../../redux/slices/authSlice';
import { broadcastAuthLogin } from '../../utils/token';
import { Role } from '../../types';

export const isDeactivatedAccount = (detail: any) =>
  ['ACCOUNT_DEACTIVATED', 'DEACTIVATED_ACCOUNT_EXISTS'].includes(detail?.code) ||
  (typeof detail === 'string' && /account.*deactivated/i.test(detail));

const freshWarning = 'A new account starts empty. Your old profile and history will not be restored, and the old data will be removed.';

interface Props {
  email: string;
  registration?: { fullname: string; password: string };
  onClose: () => void;
}

export default function AccountRecoveryDialog({ email: initialEmail, registration, onClose }: Props) {
  const [email, setEmail] = useState(initialEmail.trim().toLowerCase());
  const [action, setAction] = useState<'reactivate' | 'fresh-start'>('reactivate');
  const [step, setStep] = useState<'choose' | 'otp' | 'confirm' | 'success'>('choose');
  const [code, setCode] = useState<string[]>(Array(6).fill(''));
  const [proof, setProof] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [retryAt, setRetryAt] = useState(0);
  const [now, setNow] = useState(Date.now());
  const [session, setSession] = useState<any>(null);
  const inputs = useRef<(HTMLInputElement | null)[]>([]);
  const dialog = useRef<HTMLDivElement>(null);
  const dispatch = useDispatch();
  const remaining = Math.max(0, Math.ceil((retryAt - now) / 1000));
  const primary = 'min-h-[44px] w-full rounded-full bg-[#D60041] px-5 py-3 text-sm font-medium text-white hover:bg-[#b50037] disabled:opacity-50';
  const secondary = 'min-h-[44px] w-full rounded-full border border-gray-300 px-5 py-3 text-sm font-medium hover:bg-gray-50 disabled:opacity-50';

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    const previous = document.activeElement as HTMLElement | null;
    dialog.current?.focus();
    return () => { window.clearInterval(timer); previous?.focus(); };
  }, []);

  useEffect(() => { if (step === 'otp') inputs.current[0]?.focus(); }, [step]);

  const showError = (err: any) => {
    const detail = err?.response?.data?.detail;
    const message = typeof detail === 'string' ? detail : detail?.message;
    if (err?.response?.status === 429) {
      const wait = Number(detail?.retry_after_seconds || err.response.headers?.['retry-after'] || 60);
      setRetryAt(Date.now() + wait * 1000);
      setError('Please wait before trying again.');
    } else if (err?.response?.status === 400 && typeof message === 'string' &&
      /code|verification|verify your email|confirm|attempt/i.test(message)) {
      setError(message);
    } else {
      setError("We couldn't complete that step. Please try again in a moment.");
    }
  };

  const sendCode = async (nextAction = action) => {
    setBusy(true); setError(''); setAction(nextAction);
    try {
      const { data } = await api.post(`/auth/${nextAction}/request-otp`, { email });
      setRetryAt(Date.now() + (data.resend_after_seconds || 60) * 1000);
      setCode(Array(6).fill('')); setStep('otp');
    } catch (err) { showError(err); } finally { setBusy(false); }
  };

  const verify = async () => {
    setBusy(true); setError('');
    try {
      const { data } = await api.post(`/auth/${action}/verify`, { email, otp_code: code.join('') });
      if (action === 'fresh-start') { setProof(data.verification_token); setStep('confirm'); }
      else { saveSession(data); setSession(data); setStep('success'); }
    } catch (err) { showError(err); } finally { setBusy(false); }
  };

  const startFresh = async () => {
    setBusy(true); setError('');
    try {
      await api.post('/auth/fresh-start', { email, ...registration, verification_token: proof, confirm_fresh_start: true });
      setStep('success');
    } catch (err) { showError(err); } finally { setBusy(false); }
  };

  const saveSession = (session: any) => {
    dispatch(apiSlice.util.resetApiState());
    dispatch(setCredentials({ user: email, role: session.role as Role, userId: session.user_id, profileImageUrl: session.profile_image_url }));
    localStorage.setItem('token', session.access_token);
    localStorage.setItem('role', session.role);
    localStorage.setItem('fullname', session.fullname || '');
    localStorage.setItem('user_id', String(session.user_id));
    localStorage.setItem('saved_email', email);
    if (session.profile_image_url) localStorage.setItem('profile_image_url', session.profile_image_url);
    else localStorage.removeItem('profile_image_url');
    broadcastAuthLogin(session.user_id, email, session.role);
  };

  const continueAfterSuccess = () => {
    if (!session) { window.location.assign('/login'); return; }
    window.location.assign(`/${['HR', 'ADMIN'].includes(session.role) ? session.role.toLowerCase() : 'candidate'}/dashboard`);
  };

  const putDigits = (value: string, index: number) => {
    const digits = value.replace(/\D/g, '').slice(0, 6 - index).split('');
    setCode(previous => { const next = [...previous]; if (!digits.length) next[index] = ''; digits.forEach((digit, offset) => { next[index + offset] = digit; }); return next; });
    inputs.current[Math.min(5, index + digits.length)]?.focus();
  };

  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/50 p-4 backdrop-blur-sm">
    <div ref={dialog} tabIndex={-1} role="dialog" aria-modal="true" aria-labelledby="recovery-title"
      className="max-h-[90dvh] w-full max-w-md space-y-4 overflow-y-auto rounded-3xl bg-white p-6 shadow-2xl outline-none sm:p-8"
      onKeyDown={event => {
        if (event.key === 'Escape' && !busy && step !== 'success') onClose();
        if (event.key === 'Tab') {
          const controls = dialog.current?.querySelectorAll<HTMLElement>('button:not(:disabled), input:not(:disabled), a[href]');
          if (!controls?.length) return;
          const first = controls[0], last = controls[controls.length - 1];
          if (event.shiftKey && (document.activeElement === first || document.activeElement === dialog.current)) { event.preventDefault(); last.focus(); }
          else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
        }
      }}>
      <h2 id="recovery-title" className="text-xl font-medium text-gray-900">{step === 'choose' ? 'Choose how to continue' : step === 'otp' ? 'Check your email' : step === 'confirm' ? 'Ready to start fresh?' : session ? 'Your account is reactivated' : 'Your new account is ready'}</h2>
      {step === 'choose' && <>
        <p className="text-sm leading-relaxed text-gray-600">This account has been deactivated. Please reactivate it with email OTP or register with a fresh start.</p>
        {!initialEmail && <label className="block text-sm text-gray-700">Email address<input autoComplete="email" type="email" value={email} onChange={e => setEmail(e.target.value.trim().toLowerCase())} className="mt-2 w-full rounded-lg border border-gray-300 p-3" /></label>}
        <button className={primary} disabled={busy || remaining > 0 || !email.includes('@')} onClick={() => sendCode('reactivate')}>{busy ? 'Sending code…' : 'Reactivate my account'}</button>
        <p className="text-sm text-gray-600">Restore your profile and history. Withdrawn applications stay withdrawn.</p>
        <button className={secondary} disabled={busy || remaining > 0 || !email.includes('@')} onClick={() => {
          if (registration) sendCode('fresh-start');
          else { sessionStorage.setItem('recovery_email', email); window.location.assign('/register?fresh_start=1'); }
        }}>Start fresh with a new account</button>
        <p className="text-sm leading-relaxed text-gray-600">{freshWarning}</p>
        {remaining > 0 && <p className="text-sm text-gray-500">Try again in {remaining}s.</p>}
      </>}
      {step === 'otp' && <form onSubmit={event => { event.preventDefault(); verify(); }} className="space-y-4">
        <p className="text-sm text-gray-600">If this account is eligible, we’ll send a 6-digit code to {email}. It expires in 10 minutes.</p>
        <div className="flex justify-center gap-2" onPaste={event => { event.preventDefault(); putDigits(event.clipboardData.getData('text'), 0); }}>
          {code.map((digit, index) => <input key={index} ref={element => { inputs.current[index] = element; }} value={digit}
            type="text" inputMode="numeric" autoComplete={index === 0 ? 'one-time-code' : 'off'} aria-label={`Code digit ${index + 1}`} disabled={busy}
            className="h-12 w-9 min-w-0 rounded-lg border border-gray-300 text-center text-xl focus:border-[#D60041] focus:outline-none focus:ring-1 focus:ring-[#D60041] sm:w-11"
            onChange={event => putDigits(event.target.value, index)} onFocus={event => event.target.select()}
            onKeyDown={event => {
              if (event.key === 'Backspace' && !digit && index > 0) inputs.current[index - 1]?.focus();
              if (event.key === 'ArrowLeft' && index > 0) inputs.current[index - 1]?.focus();
              if (event.key === 'ArrowRight' && index < 5) inputs.current[index + 1]?.focus();
            }} />)}
        </div>
        <button className={primary} disabled={busy || code.join('').length !== 6}>{busy ? 'Verifying…' : action === 'reactivate' ? 'Verify and reactivate' : 'Verify email'}</button>
        <button type="button" className={secondary} disabled={busy || remaining > 0} onClick={() => sendCode()}>{remaining > 0 ? `Resend code in ${remaining}s` : 'Resend code'}</button>
      </form>}
      {step === 'confirm' && <>
        <p className="text-sm text-gray-600">Email verified. {freshWarning} Withdrawn applications stay withdrawn. This cannot be undone.</p>
        <button className={primary} disabled={busy} onClick={startFresh}>{busy ? 'Creating your new account…' : 'Yes, start fresh'}</button>
      </>}
      {step === 'success' && <>
        <p className="text-sm text-gray-600">{session ? 'Your profile and history are restored. Withdrawn applications stay withdrawn.' : 'Your old personal data has been removed. Sign in to your new, empty account.'}</p>
        <button className={primary} onClick={continueAfterSuccess}>{session ? 'Continue to my account' : 'Sign in'}</button>
      </>}
      {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
      {step !== 'choose' && step !== 'success' && <button className={secondary} disabled={busy} onClick={() => { setStep('choose'); setError(''); setProof(''); }}>Back to choices</button>}
      {step !== 'success' && <button className="min-h-[44px] w-full text-sm font-medium text-gray-600" disabled={busy} onClick={onClose}>Cancel</button>}
    </div>
  </div>;
}
