"""Regression coverage for both public registration contracts and verified recovery."""
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.account_otp import AccountOTP
from app.models.audit_log import AuditLog
from app.models.resume import Resume
from app.models.user import User
from app.services import retention_service
from tests.test_recruitment_lifecycle_rules import _make_user, _make_job, _make_application


async def deactivated(db, email='recover@example.com', password='Secret123!'):
    user = await _make_user(db, email, password=password)
    user.is_deactivated = True
    user.deactivated_at = datetime.utcnow()
    await db.commit()
    return user


async def request_code(client, email, action='fresh-start'):
    with patch('app.services.auth_service.send_otp_email', new_callable=AsyncMock, return_value=True) as mail:
        response = await client.post(f'/auth/{action}/request-otp', json={'email': email})
    assert response.status_code == 200, response.text
    return mail.call_args.args[1]


@pytest.mark.asyncio
async def test_registration_contracts_and_password_gated_login(client, db_session):
    user = await deactivated(db_session, password='password')
    body = {'email': '  RECOVER@EXAMPLE.COM ', 'password': 'NewPassword123!', 'fullname': 'New Person'}
    for route in ['/candidate/register', '/auth/register']:
        result = await client.post(route, json=body)
        assert result.status_code == 409
        assert result.json()['detail']['allowed_actions'] == ['reactivate', 'fresh_start']
    await db_session.refresh(user)
    wrong = await client.post('/auth/login', json={'email': user.email, 'password': 'anything'})
    assert wrong.status_code == 401
    correct = await client.post('/auth/login', json={'email': user.email, 'password': 'password'})
    assert correct.status_code == 403
    assert correct.json()['detail']['code'] == 'ACCOUNT_DEACTIVATED'


@pytest.mark.asyncio
async def test_fresh_start_requires_verification_and_confirmation(client, db_session, tmp_path):
    user = await deactivated(db_session)
    user.phone = '09123456789'
    job = await _make_job(db_session, 'RECOVERY-1', 'Operator')
    file = tmp_path / 'resume.txt'
    file.write_text('Personal resume data')
    application = await _make_application(db_session, job, user, status='WITHDRAWN BY APPLICANT', resume_url=str(file))
    resume = Resume(candidate_id=user.id, filename='private.txt', file_url=str(file), parsed_data={'text': 'private'})
    audit = AuditLog(user_id=user.id, action='SIGN_IN', target=user.email, details=user.fullname, ip_address='127.0.0.1')
    db_session.add_all([resume, audit])
    await db_session.commit()
    body = {'email': user.email, 'password': 'NewPassword123!', 'fullname': 'Fresh Person'}
    for route in ['/auth/fresh-start', '/auth/register']:
        result = await client.post(route, json={**body, 'fresh_start': True, 'confirm_fresh_start': True})
        assert result.status_code == 400
    await db_session.refresh(user)
    assert not user.is_anonymized and file.exists()
    code = await request_code(client, user.email)
    verified = await client.post('/auth/fresh-start/verify', json={'email': user.email, 'otp_code': code})
    assert verified.status_code == 200, verified.text
    proof = verified.json()['verification_token']
    await db_session.refresh(user)
    assert not user.is_anonymized and file.exists()  # verification alone never purges
    denied = await client.post('/auth/fresh-start', json={**body, 'verification_token': proof})
    assert denied.status_code == 400
    result = await client.post('/auth/fresh-start', json={**body, 'verification_token': proof, 'confirm_fresh_start': True})
    assert result.status_code == 200, result.text
    for obj in [user, application, resume, audit]:
        await db_session.refresh(obj)
    assert user.is_anonymized and user.phone is None and user.email.endswith('@anonymized.local')
    assert not file.exists() and resume.parsed_data is None and resume.file_url is None
    assert audit.ip_address is None and 'Anonymized' in audit.details
    assert application.is_anonymized and application.status == 'WITHDRAWN BY APPLICANT'
    assert application.email_hash == retention_service.compute_email_hash(body['email'])
    new_user = (await db_session.execute(select(User).where(User.email == body['email']))).scalar_one()
    assert new_user.id != user.id and new_user.fullname == 'Fresh Person' and new_user.phone is None
    assert await retention_service.has_previous_anonymized_application(db_session, body['email'], new_user.id)
    login = await client.post('/auth/login', json={'email': body['email'], 'password': body['password']})
    assert login.status_code == 200
    apps = await client.get('/applications/my', headers={'Authorization': f"Bearer {login.json()['access_token']}"})
    assert apps.status_code == 200 and apps.json() == []
    replay = await client.post('/auth/fresh-start', json={**body, 'verification_token': proof, 'confirm_fresh_start': True})
    assert replay.status_code == 409


@pytest.mark.asyncio
async def test_otp_limits_purpose_expiry_replay_and_reactivation(client, db_session):
    user = await deactivated(db_session)
    user.bio = 'Keep my profile'
    await db_session.commit()
    code = await request_code(client, user.email, 'reactivate')
    cooldown = await client.post('/auth/reactivate/request-otp', json={'email': user.email})
    assert cooldown.status_code == 429 and int(cooldown.headers['retry-after']) > 0
    cross = await client.post('/auth/fresh-start/verify', json={'email': user.email, 'otp_code': code})
    assert cross.status_code == 400
    otp = (await db_session.execute(select(AccountOTP).where(AccountOTP.purpose == 'reactivate_account'))).scalar_one()
    wrong_code = '000000' if code != '000000' else '111111'
    for _ in range(5):
        wrong = await client.post('/auth/reactivate/verify', json={'email': user.email, 'otp_code': wrong_code})
        assert wrong.status_code == 400
    exhausted = await client.post('/auth/reactivate/verify', json={'email': user.email, 'otp_code': code})
    assert exhausted.status_code == 400
    otp.created_at = datetime.utcnow() - timedelta(minutes=2)
    await db_session.commit()
    code = await request_code(client, user.email, 'reactivate')
    otp = (await db_session.execute(select(AccountOTP).where(AccountOTP.used_at.is_(None)))).scalar_one()
    otp.expires_at = datetime.utcnow() - timedelta(seconds=1)
    await db_session.commit()
    expired = await client.post('/auth/reactivate/verify', json={'email': user.email, 'otp_code': code})
    assert expired.status_code == 400 and 'expired' in expired.text
    otp.created_at = datetime.utcnow() - timedelta(minutes=2)
    await db_session.commit()
    code = await request_code(client, user.email, 'reactivate')
    restored = await client.post('/auth/reactivate/verify', json={'email': user.email, 'otp_code': code})
    assert restored.status_code == 200, restored.text
    await db_session.refresh(user)
    assert user.bio == 'Keep my profile' and not user.is_deactivated
    assert restored.json()['user_id'] == user.id
    replay = await client.post('/auth/reactivate/verify', json={'email': user.email, 'otp_code': code})
    assert replay.status_code == 400


@pytest.mark.asyncio
async def test_nonexistent_otp_generic_and_rate_limited(client):
    with patch('app.services.auth_service.send_otp_email', new_callable=AsyncMock) as mail:
        for _ in range(5):
            result = await client.post('/auth/fresh-start/request-otp', json={'email': 'unknown@example.com'})
            assert result.status_code == 200
        assert not mail.called
        limited = await client.post('/auth/fresh-start/request-otp', json={'email': 'unknown@example.com'})
        assert limited.status_code == 429


@pytest.mark.asyncio
async def test_active_duplicate_and_purged_registration_contract(client, db_session):
    user = await _make_user(db_session, 'active@example.com')
    body = {'email': ' ACTIVE@EXAMPLE.COM ', 'password': 'Password123!', 'fullname': 'New Person'}
    for route in ['/auth/register', '/candidate/register']:
        result = await client.post(route, json=body)
        assert result.status_code == 409 and 'already registered' in result.text
    await db_session.refresh(user)
    user.is_deactivated = True
    await retention_service.anonymize_user_and_records(db_session, user)
    await db_session.commit()
    result = await client.post('/candidate/register', json=body)
    assert result.status_code == 200, result.text
    assert result.json()['email'] == 'active@example.com' and result.json()['id'] != user.id


@pytest.mark.asyncio
async def test_normalized_active_email_index_and_reversible_migration(db_session, test_engine):
    from migrations.add_active_email_uniqueness import upgrade, downgrade
    await _make_user(db_session, 'unique@example.com')
    from app.models.candidate import Candidate
    db_session.add(Candidate(email=' UNIQUE@example.com ', password='hash', fullname='Duplicate', role='CANDIDATE'))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()
    async with test_engine.begin() as connection:
        await downgrade(connection)
        await upgrade(connection)
        await upgrade(connection)


@pytest.mark.asyncio
async def test_fresh_start_proof_cannot_cross_accounts_or_survive_expiry(client, db_session):
    user = await deactivated(db_session)
    other = await deactivated(db_session, 'other@example.com')
    code = await request_code(client, user.email)
    verified = await client.post('/auth/fresh-start/verify', json={'email': user.email, 'otp_code': code})
    proof = verified.json()['verification_token']
    body = {'password': 'Password123!', 'fullname': 'Fresh', 'verification_token': proof, 'confirm_fresh_start': True}
    cross = await client.post('/auth/fresh-start', json={**body, 'email': 'other@example.com'})
    assert cross.status_code == 400
    otp = (await db_session.execute(select(AccountOTP).where(AccountOTP.purpose == 'fresh_start_confirm'))).scalar_one()
    otp.expires_at = datetime.utcnow() - timedelta(seconds=1)
    await db_session.commit()
    expired = await client.post('/auth/fresh-start', json={**body, 'email': 'recover@example.com'})
    assert expired.status_code == 400
    for account in [user, other]:
        await db_session.refresh(account)
        assert not account.is_anonymized


@pytest.mark.asyncio
async def test_failed_file_purge_keeps_account_and_verification_for_retry(client, db_session, tmp_path):
    user = await deactivated(db_session)
    file = tmp_path / 'locked.txt'
    file.write_text('private')
    user.resume_url = str(file)
    await db_session.commit()
    code = await request_code(client, user.email)
    verified = await client.post('/auth/fresh-start/verify', json={'email': user.email, 'otp_code': code})
    body = {'email': user.email, 'password': 'Password123!', 'fullname': 'Fresh',
            'verification_token': verified.json()['verification_token'], 'confirm_fresh_start': True}
    with patch('app.services.retention_service.os.remove', side_effect=OSError('file locked')):
        failed = await client.post('/auth/fresh-start', json=body)
    assert failed.status_code == 400
    await db_session.refresh(user)
    assert not user.is_anonymized and file.exists()
    retry = await client.post('/auth/fresh-start', json=body)
    assert retry.status_code == 200, retry.text
    assert not file.exists()


@pytest.mark.asyncio
async def test_retention_skips_account_reactivated_since_selection(db_session):
    from sqlalchemy import update
    from sqlalchemy.ext.asyncio import AsyncSession
    user = await deactivated(db_session)
    # A retention worker already selected this object before recovery committed.
    async with AsyncSession(bind=db_session.bind) as recovery_session:
        await recovery_session.execute(update(User).where(User.id == user.id).values(is_deactivated=False))
        await recovery_session.commit()
    assert user.is_deactivated
    result = await retention_service.anonymize_user_and_records(db_session, user)
    assert result['skipped_active'] and not result['anonymized']
    assert user.email == 'recover@example.com' and not user.is_anonymized
