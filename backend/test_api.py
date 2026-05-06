"""
Integration tests — runs in-process via FastAPI TestClient.
Run: python test_api.py
"""
import sys
sys.path.insert(0, '.')

from fastapi.testclient import TestClient
import main

# Use context manager so startup events fire (creates tables, seeds demo data)
_client_ctx = TestClient(main.app)
_client_ctx.__enter__()
client = _client_ctx


def test_health():
    r = client.get('/health')
    assert r.status_code == 200
    data = r.json()
    assert data['status'] == 'ok'
    print(f"  Health OK — provider: {data['provider']}")


def test_auth():
    # Register
    r = client.post('/auth/register', json={
        'name': 'Test User', 'email': 'test_integration@example.com',
        'password': 'secret123', 'plan': 'starter',
    })
    assert r.status_code == 201, f"Register failed: {r.status_code} {r.text}"
    data  = r.json()
    token = data['access_token']
    user  = data['user']
    assert user['plan'] == 'starter'
    print(f"  Register OK: name={user['name']} plan={user['plan']}")

    # Duplicate email
    r2 = client.post('/auth/register', json={
        'name': 'Dupe', 'email': 'test_integration@example.com',
        'password': 'pass123', 'plan': 'starter',
    })
    assert r2.status_code == 400
    print("  Duplicate email correctly rejected")

    # Login
    r = client.post('/auth/login', json={
        'email': 'test_integration@example.com', 'password': 'secret123',
    })
    assert r.status_code == 200
    token = r.json()['access_token']
    print("  Login OK")

    # Wrong password
    r = client.post('/auth/login', json={
        'email': 'test_integration@example.com', 'password': 'wrongpass',
    })
    assert r.status_code == 401
    print("  Wrong password correctly rejected")

    # GET /auth/me
    r = client.get('/auth/me', headers={'Authorization': f'Bearer {token}'})
    assert r.status_code == 200
    me = r.json()
    assert me['email'] == 'test_integration@example.com'
    print(f"  GET /auth/me OK: {me['email']}")

    return token, me['id']


def test_campaigns(token, user_id):
    headers = {'Authorization': f'Bearer {token}'}

    # Unauthenticated request (401 or 403 depending on FastAPI/Starlette version)
    r = client.get('/api/campaigns')
    assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"
    print(f"  Unauthenticated request correctly rejected ({r.status_code})")

    # List campaigns — should see 5 demo campaigns
    r = client.get('/api/campaigns', headers=headers)
    assert r.status_code == 200
    campaigns = r.json()
    assert len(campaigns) == 5, f"Expected 5 demo campaigns, got {len(campaigns)}"
    for c in campaigns:
        assert c['user_id'] is None, f"Demo campaign should have user_id=None, got {c['user_id']}"
    print(f"  List campaigns OK: {len(campaigns)} demo campaigns visible")

    # Create valid campaign (Awareness, within Starter limits)
    r = client.post('/api/campaigns', headers=headers, json={
        'name': 'My First Campaign', 'campaign_type': 'Awareness',
        'status': 'active', 'objective': 'Registrations', 'target_number': 100,
        'start_date': '2026-06-01', 'end_date': '2026-06-30', 'budget': 10000,
    })
    assert r.status_code == 201, f"Create failed: {r.status_code} {r.text}"
    c1 = r.json()
    assert c1['user_id'] == user_id, f"user_id mismatch: {c1['user_id']} != {user_id}"
    print(f"  Create campaign OK: id={c1['id']} user_id={c1['user_id']}")

    # Create second campaign
    r = client.post('/api/campaigns', headers=headers, json={
        'name': 'My Second Campaign', 'campaign_type': 'Event Drive',
        'status': 'active', 'objective': 'Registrations', 'target_number': 50,
        'start_date': '2026-07-01', 'end_date': '2026-07-21', 'budget': 5000,
    })
    assert r.status_code == 201
    print("  Second campaign OK")

    # Third campaign should be blocked (Starter plan limit = 2)
    r = client.post('/api/campaigns', headers=headers, json={
        'name': 'Over Limit', 'campaign_type': 'Awareness',
        'status': 'active', 'objective': 'Registrations', 'target_number': 50,
        'start_date': '2026-08-01', 'end_date': '2026-08-30', 'budget': 5000,
    })
    assert r.status_code == 403, f"Expected 403 (plan limit), got {r.status_code}"
    print("  Third campaign correctly blocked by Starter plan limit")

    # Budget over cap
    r = client.post('/api/campaigns', headers=headers, json={
        'name': 'Budget Too High', 'campaign_type': 'Awareness',
        'status': 'draft', 'objective': 'Registrations', 'target_number': 50,
        'start_date': '2026-08-01', 'end_date': '2026-08-30', 'budget': 99999,
    })
    assert r.status_code == 403, f"Expected 403 (budget cap), got {r.status_code}"
    print("  Budget over cap correctly blocked")

    # Forbidden campaign type on Starter
    r = client.post('/api/campaigns', headers=headers, json={
        'name': 'Hiring Test', 'campaign_type': 'Hiring Drive',
        'status': 'draft', 'objective': 'Job Applications', 'target_number': 100,
        'start_date': '2026-08-01', 'end_date': '2026-08-30', 'budget': 5000,
    })
    assert r.status_code == 403, f"Expected 403 (campaign type), got {r.status_code}"
    print("  Hiring Drive on Starter plan correctly blocked")

    # Demo campaign cannot be modified
    demo_id = next(c['id'] for c in campaigns if c['user_id'] is None)
    r = client.patch(f'/api/campaigns/{demo_id}', headers=headers, json={'status': 'paused'})
    assert r.status_code == 403
    print(f"  Demo campaign modification correctly blocked")

    # Own campaign can be updated
    r = client.patch(f"/api/campaigns/{c1['id']}", headers=headers, json={'status': 'paused'})
    assert r.status_code == 200
    assert r.json()['status'] == 'paused'
    print("  Own campaign update OK")

    return c1['id']


def test_check_limits(token):
    headers = {'Authorization': f'Bearer {token}'}

    # Valid: Awareness, ₹20K on Starter
    r = client.post('/api/campaigns/check-limits', headers=headers, json={
        'campaign_type': 'Awareness', 'budget': 20000,
    })
    assert r.status_code == 200
    result = r.json()
    # Note: may have active_campaign violation if called after test_campaigns
    print(f"  check-limits (Awareness ₹20K): ok={result['ok']} violations={len(result['violations'])}")

    # Forbidden type
    r = client.post('/api/campaigns/check-limits', headers=headers, json={
        'campaign_type': 'Hiring Drive', 'budget': 20000,
    })
    result = r.json()
    assert not result['ok']
    assert any('Hiring Drive' in v['message'] for v in result['violations'])
    print("  check-limits (Hiring Drive on Starter): correctly blocked")

    # Budget over cap
    r = client.post('/api/campaigns/check-limits', headers=headers, json={
        'campaign_type': 'Awareness', 'budget': 50000,
    })
    result = r.json()
    assert not result['ok']
    assert any(v['field'] == 'budget' for v in result['violations'])
    print("  check-limits (budget ₹50K over ₹25K cap): correctly blocked")

    # Forbidden segment
    r = client.post('/api/campaigns/check-limits', headers=headers, json={
        'campaign_type': 'Awareness', 'audience_segments': ['Entrepreneurs'],
    })
    result = r.json()
    assert not result['ok']
    assert any('Entrepreneurs' in v['message'] for v in result['violations'])
    print("  check-limits (Entrepreneurs on Starter): correctly blocked")

    # Duration too long
    r = client.post('/api/campaigns/check-limits', headers=headers, json={
        'campaign_type': 'Awareness',
        'start_date': '2026-06-01', 'end_date': '2026-09-30',  # 121 days > 30
    })
    result = r.json()
    assert not result['ok']
    assert any(v['field'] == 'duration' for v in result['violations'])
    print("  check-limits (121 days on Starter max 30): correctly blocked")


if __name__ == '__main__':
    print("\n-- Health ------------------------------─")
    test_health()

    print("\n-- Auth --------------------------------─")
    token, user_id = test_auth()

    print("\n-- Campaigns ----------------------------")
    test_campaigns(token, user_id)

    print("\n-- Plan Limits --------------------------")
    test_check_limits(token)

    print("\nOK  ALL TESTS PASSED\n")
