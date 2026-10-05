from django.urls import reverse


def navigation(request):
    from .registry import MODULES

    current = (
        request.resolver_match.kwargs.get("module", "")
        if request.resolver_match
        else ""
    )
    items = [
        {
            "key": key,
            "title": config["title"],
            "icon": config["icon"],
            "url": reverse("record-list", kwargs={"module": key}),
        }
        for key, config in MODULES.items()
        if key != "accounts" or request.user.is_superuser
    ]
    return {"nav_items": items, "active_module": current}
