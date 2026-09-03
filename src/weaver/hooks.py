async def on_role_change(user_id: str, role: str, action: str):
    """Simple hook called when a user's role changes.

    This is a single async function so you can extend it to send emails,
    push to a pub/sub channel, or call external webhooks.
    """
    # For now: lightweight logging; replace with proper notifier as needed.
    print(f"hook: user={user_id} role={role} action={action}")