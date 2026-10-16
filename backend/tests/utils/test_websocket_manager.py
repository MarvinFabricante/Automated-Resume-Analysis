import json
import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

import app.utils.websocket_manager as wm


@pytest.fixture(autouse=True)
def clean_ws_state():
    """Ensure clean connection state before and after each test."""
    wm.chat_connections.clear()
    wm.role_connections.clear()
    wm.email_connections.clear()
    yield
    wm.chat_connections.clear()
    wm.role_connections.clear()
    wm.email_connections.clear()


def test_normalize_uid():
    assert wm._normalize_uid("123") == 123
    assert wm._normalize_uid(456) == 456
    assert wm._normalize_uid("user_abc") == "user_abc"
    assert wm._normalize_uid(None) is None


@pytest.mark.asyncio
async def test_sync_or_async_none():
    helper = wm._SyncOrAsyncNone()
    # Can be awaited
    assert await helper is None


@pytest.mark.asyncio
async def test_chat_connect_and_disconnect():
    mock_ws1 = AsyncMock()
    mock_ws2 = AsyncMock()

    with patch("app.utils.websocket_manager.start_redis_listener", new_callable=AsyncMock), \
         patch("app.utils.websocket_manager.broadcast_status", new_callable=AsyncMock) as mock_broadcast:

        # 1. Connect first socket for user 10
        await wm.connect_chat(mock_ws1, 10)
        mock_ws1.accept.assert_awaited_once()
        assert 10 in wm.chat_connections
        assert mock_ws1 in wm.chat_connections[10]
        mock_broadcast.assert_awaited_with(10, True)

        # 2. Connect second socket for user 10 (e.g. second tab)
        await wm.connect_chat(mock_ws2, 10)
        assert len(wm.chat_connections[10]) == 2

        # 3. Disconnect one socket -> user should STILL be connected
        mock_broadcast.reset_mock()
        await wm.disconnect_chat(mock_ws1, 10)
        assert 10 in wm.chat_connections
        assert mock_ws2 in wm.chat_connections[10]
        # Should NOT broadcast offline yet
        mock_broadcast.assert_not_called()

        # 4. Disconnect second socket -> user is now offline
        await wm.disconnect_chat(mock_ws2, 10)
        assert 10 not in wm.chat_connections
        mock_broadcast.assert_awaited_with(10, False)


@pytest.mark.asyncio
async def test_send_local_chat_message_and_dead_cleanup():
    good_ws = AsyncMock()
    dead_ws = AsyncMock()
    dead_ws.send_json.side_effect = Exception("Connection closed")

    wm.chat_connections[5] = {good_ws, dead_ws}

    msg = {"text": "hello"}
    await wm.send_local_chat_message(msg, 5)

    good_ws.send_json.assert_awaited_once_with(msg)
    # dead_ws should have been removed
    assert dead_ws not in wm.chat_connections[5]
    assert good_ws in wm.chat_connections[5]

    # Now make good_ws fail too
    good_ws.send_json.side_effect = Exception("Closed")
    await wm.send_local_chat_message(msg, 5)
    # uid 5 should be deleted completely
    assert 5 not in wm.chat_connections


@pytest.mark.asyncio
async def test_send_personal_message():
    with patch("app.utils.websocket_manager.send_local_chat_message", new_callable=AsyncMock) as mock_local, \
         patch("app.utils.websocket_manager.publish_event", new_callable=AsyncMock) as mock_publish:

        msg = {"type": "chat", "text": "Hi"}
        await wm.send_personal_message(msg, "12")

        mock_local.assert_awaited_once_with(msg, 12)
        mock_publish.assert_awaited_once_with(
            "pubsub:ws_chat",
            {"origin_id": wm.INSTANCE_ID, "user_id": 12, "message": msg},
        )


@pytest.mark.asyncio
async def test_broadcast_status():
    ws_user1 = AsyncMock()
    wm.chat_connections[1] = {ws_user1}

    with patch("app.utils.websocket_manager.publish_event", new_callable=AsyncMock) as mock_publish:
        await wm.broadcast_status("2", True)

        expected_msg = {"type": "status", "user_id": 2, "is_online": True}
        ws_user1.send_json.assert_awaited_once_with(expected_msg)
        mock_publish.assert_awaited_once_with(
            "pubsub:ws_status",
            {"origin_id": wm.INSTANCE_ID, "user_id": 2, "is_online": True},
        )


@pytest.mark.asyncio
async def test_is_user_online():
    mock_redis = AsyncMock()
    # 1. Found in Redis
    mock_redis.sismember.return_value = True
    with patch("app.utils.websocket_manager.get_async_redis", return_value=mock_redis):
        assert await wm.is_user_online(10) is True

    # 2. Not in Redis, but in local chat_connections
    mock_redis.sismember.return_value = False
    wm.chat_connections[10] = {AsyncMock()}
    with patch("app.utils.websocket_manager.get_async_redis", return_value=mock_redis):
        assert await wm.is_user_online(10) is True

    # 3. Neither
    wm.chat_connections.clear()
    with patch("app.utils.websocket_manager.get_async_redis", return_value=mock_redis):
        assert await wm.is_user_online(10) is False


def test_get_online_count_sync():
    mock_sync_redis = MagicMock()
    mock_sync_redis.scard.return_value = 7

    with patch("app.utils.redis_client.is_sync_redis_available", return_value=True), \
         patch("app.utils.redis_client.get_sync_redis", return_value=mock_sync_redis):
        assert wm.get_online_count() == 7

    # Fallback to local
    with patch("app.utils.redis_client.is_sync_redis_available", return_value=False):
        wm.chat_connections[1] = {MagicMock()}
        wm.chat_connections[2] = {MagicMock()}
        assert wm.get_online_count() == 2


@pytest.mark.asyncio
async def test_get_online_count_async():
    mock_redis = AsyncMock()
    mock_redis.scard.return_value = 5

    with patch("app.utils.websocket_manager.get_async_redis", return_value=mock_redis):
        assert await wm.get_online_count_async() == 5

    # Fallback when redis returns 0 / None
    mock_redis.scard.return_value = 0
    wm.chat_connections[1] = {AsyncMock()}
    with patch("app.utils.websocket_manager.get_async_redis", return_value=mock_redis):
        assert await wm.get_online_count_async() == 1


@pytest.mark.asyncio
async def test_notification_connect_and_disconnect():
    mock_ws = AsyncMock()

    with patch("app.utils.websocket_manager.start_redis_listener", new_callable=AsyncMock):
        await wm.connect_notification(mock_ws, role="hr", email="hr@company.com")
        assert "HR" in wm.role_connections
        assert mock_ws in wm.role_connections["HR"]
        assert "hr@company.com" in wm.email_connections
        assert mock_ws in wm.email_connections["hr@company.com"]

        wm.disconnect_notification(mock_ws, role="hr", email="hr@company.com")
        assert "HR" not in wm.role_connections
        assert "hr@company.com" not in wm.email_connections


@pytest.mark.asyncio
async def test_send_local_notification_by_email():
    ws_email = AsyncMock()
    wm.email_connections["cand@test.com"] = [ws_email]

    await wm.send_local_notification("Hello Candidate", target_email="cand@test.com")
    ws_email.send_text.assert_awaited_once_with("Hello Candidate")


@pytest.mark.asyncio
async def test_send_local_notification_by_role_hr_and_admin():
    ws_hr = AsyncMock()
    ws_admin = AsyncMock()
    wm.role_connections["HR"] = [ws_hr]
    wm.role_connections["ADMIN"] = [ws_admin]

    # Target HR should also send to ADMIN
    await wm.send_local_notification("New Interview", target_role="HR")
    ws_hr.send_text.assert_awaited_once_with("New Interview")
    ws_admin.send_text.assert_awaited_once_with("New Interview")


@pytest.mark.asyncio
async def test_send_local_notification_default():
    ws_hr = AsyncMock()
    ws_cand = AsyncMock()
    wm.role_connections["HR"] = [ws_hr]
    wm.role_connections["CANDIDATE"] = [ws_cand]

    # Default broadcasts only to ADMIN and HR, NEVER to CANDIDATE
    await wm.send_local_notification("System maintenance")
    ws_hr.send_text.assert_awaited_once_with("System maintenance")
    ws_cand.send_text.assert_not_called()


@pytest.mark.asyncio
async def test_send_local_notification_dead_cleanup():
    dead_ws = AsyncMock()
    dead_ws.send_text.side_effect = Exception("Dead socket")
    wm.role_connections["ADMIN"] = [dead_ws]

    await wm.send_local_notification("Msg", target_role="ADMIN")
    assert dead_ws not in wm.role_connections["ADMIN"]


@pytest.mark.asyncio
async def test_broadcast_notification():
    with patch("app.utils.websocket_manager.send_local_notification", new_callable=AsyncMock) as mock_local, \
         patch("app.utils.websocket_manager.publish_event", new_callable=AsyncMock) as mock_pub:

        await wm.broadcast_notification("Alert!", target_role="HR")
        mock_local.assert_awaited_once_with("Alert!", "HR", None)
        mock_pub.assert_awaited_once_with(
            "pubsub:ws_notifications",
            {
                "origin_id": wm.INSTANCE_ID,
                "message": "Alert!",
                "target_role": "HR",
                "target_email": None,
            },
        )


@pytest.mark.asyncio
async def test_unified_connect_and_disconnect():
    mock_ws = AsyncMock()

    with patch("app.utils.websocket_manager.connect_notification", new_callable=AsyncMock) as m_conn_notif, \
         patch("app.utils.websocket_manager.connect_chat", new_callable=AsyncMock) as m_conn_chat, \
         patch("app.utils.websocket_manager.disconnect_notification") as m_dis_notif, \
         patch("app.utils.websocket_manager.disconnect_chat", new_callable=AsyncMock) as m_dis_chat:

        # 1. Connect with email -> notification
        await wm.connect(mock_ws, "HR", email="test@mail.com")
        m_conn_notif.assert_awaited_once_with(mock_ws, role="HR", email="test@mail.com")

        # 2. Connect with int -> chat
        await wm.connect(mock_ws, 123)
        m_conn_chat.assert_awaited_once_with(mock_ws, user_id=123)

        # 3. Connect with numeric string -> chat
        await wm.connect(mock_ws, "456")
        m_conn_chat.assert_awaited_with(mock_ws, user_id=456)

        # 4. Connect with string role -> notification
        await wm.connect(mock_ws, "ADMIN")
        m_conn_notif.assert_awaited_with(mock_ws, role="ADMIN", email=None)

        # Disconnect notification (sync)
        res = wm.disconnect(mock_ws, "ADMIN")
        m_dis_notif.assert_called_once_with(mock_ws, role="ADMIN", email=None)
        await res  # _SyncOrAsyncNone is awaitable

        # Disconnect chat (coroutine returned)
        await wm.disconnect(mock_ws, 123)
        m_dis_chat.assert_awaited_once_with(mock_ws, user_id=123)


@pytest.mark.asyncio
async def test_broadcast_alias():
    with patch("app.utils.websocket_manager.broadcast_notification", new_callable=AsyncMock) as mock_bcast:
        await wm.broadcast("Hello", target_role="HR")
        mock_bcast.assert_awaited_once_with("Hello", target_role="HR", target_email=None)


@pytest.mark.asyncio
async def test_redis_listener_lifecycle_and_messages():
    # 1. Test start & stop listener
    mock_task = MagicMock()
    mock_task.done.return_value = False

    with patch("asyncio.create_task", return_value=mock_task) as mock_create, \
         patch("app.utils.websocket_manager._listen_redis_pubsub", new_callable=AsyncMock):
        wm._listener_task = None
        await wm.start_redis_listener()
        mock_create.assert_called_once()
        # Second call does nothing if task active
        await wm.start_redis_listener()
        assert mock_create.call_count == 1

    # Stop listener
    await wm.stop_redis_listener()
    assert wm._listener_task is None


@pytest.mark.asyncio
async def test_listen_redis_pubsub_message_processing():
    messages = [
        # 1. Self-echo message (should be ignored)
        {
            "type": "message",
            "channel": b"pubsub:ws_notifications",
            "data": json.dumps({"origin_id": wm.INSTANCE_ID, "message": "ignore me"}).encode("utf-8"),
        },
        # 2. Remote notification message
        {
            "type": "message",
            "channel": "pubsub:ws_notifications",
            "data": json.dumps({"origin_id": "remote_instance", "message": "Remote Alert", "target_role": "ADMIN"}),
        },
        # 3. Remote chat message
        {
            "type": "message",
            "channel": "pubsub:ws_chat",
            "data": json.dumps({"origin_id": "remote_instance", "user_id": 99, "message": {"text": "Remote chat"}}),
        },
        # 4. Remote status message
        {
            "type": "message",
            "channel": "pubsub:ws_status",
            "data": json.dumps({"origin_id": "remote_instance", "user_id": 99, "is_online": True}),
        },
    ]

    class MockPubSub:
        async def subscribe(self, *channels):
            pass

        async def listen(self):
            for m in messages:
                yield m

        async def unsubscribe(self, *channels):
            pass

        async def close(self):
            pass

    mock_redis = MagicMock()
    mock_redis.pubsub.return_value = MockPubSub()

    with patch("app.utils.websocket_manager.get_async_redis", return_value=mock_redis), \
         patch("app.utils.websocket_manager.send_local_notification", new_callable=AsyncMock) as m_local_notif, \
         patch("app.utils.websocket_manager.send_local_chat_message", new_callable=AsyncMock) as m_local_chat:

        wm.chat_connections[1] = {AsyncMock()}

        await wm._listen_redis_pubsub()

        # Remote notification was dispatched
        m_local_notif.assert_awaited_once_with("Remote Alert", "ADMIN", None)

        # Remote chat was dispatched
        m_local_chat.assert_any_await({"text": "Remote chat"}, 99)

        # Remote status was dispatched to local users
        m_local_chat.assert_any_await({"type": "status", "user_id": 99, "is_online": True}, 1)



def test_connection_manager_proxy():
    mgr = wm.ConnectionManager()
    assert mgr.active_connections is wm.chat_connections
    assert mgr.email_connections is wm.email_connections
    assert mgr.role_connections is wm.role_connections
    assert mgr.connect is wm.connect
    assert mgr.disconnect is wm.disconnect
    assert mgr.get_online_count is wm.get_online_count
