def notify(title: str, message: str):
    """Send a Windows desktop toast notification via plyer."""
    try:
        from plyer import notification
        notification.notify(
            title=title,
            message=message,
            app_name="Stock Tracker",
            timeout=8,
        )
    except Exception:
        pass  # Silently fail if notifications not available
