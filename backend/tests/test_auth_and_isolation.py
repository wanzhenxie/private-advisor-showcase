# Checked this after the memory routes were connected.
# User B should get 404 on A's memory, even with a valid token and the id.
def register(client, email):
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert response.status_code == 201, response.text
    return response.json()["access_token"]

def auth(token):
    return {"Authorization": f"Bearer {token}"}

def test_user_cannot_read_another_users_memory(client):
    # Important regression check: a valid login must not grant access to
    # another user's memories, even if the memory ID is known.
    token_a = register(client, "a@example.com")
    token_b = register(client, "b@example.com")

    created = client.post(
        "/api/memories",
        headers=auth(token_a),
        json={
            "category": "goal",
            "content": "A用户的私人目标",
            "status": "active",
            "keywords": ["目标"],
        },
    )
    assert created.status_code == 201
    memory_id = created.json()["id"]

    update = client.patch(
        f"/api/memories/{memory_id}",
        headers=auth(token_b),
        json={"content": "越权修改"},
    )
    assert update.status_code == 404

    delete = client.delete(
        f"/api/memories/{memory_id}",
        headers=auth(token_b),
    )
    assert delete.status_code == 404

    listed = client.get("/api/memories", headers=auth(token_b))
    assert listed.status_code == 200
    assert all(item["id"] != memory_id for item in listed.json())

def test_profile_is_user_scoped(client):
    # Updating account A's preferences should never modify account B's profile.
    token_a = register(client, "profile-a@example.com")
    token_b = register(client, "profile-b@example.com")

    response = client.put(
        "/api/profile",
        headers=auth(token_a),
        json={
            "display_name": "Alice",
            "locale": "zh-CN",
            "timezone": "America/New_York",
            "advisor_preferences": {"tone": "direct"},
        },
    )
    assert response.status_code == 200

    b_profile = client.get("/api/profile", headers=auth(token_b))
    assert b_profile.status_code == 200
    assert b_profile.json()["display_name"] is None
