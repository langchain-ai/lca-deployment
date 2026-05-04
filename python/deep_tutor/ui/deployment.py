"""
deployment.py — Self-discovery of the deployment's public URL.

When the UI server runs as a custom route inside a LangGraph deployment, it needs
to know its own public URL to create a LangGraph SDK client. It can't know this
at deploy time (chicken-and-egg), so we derive it from the incoming HTTP request.

In cloud deployments, TLS is terminated at the load balancer, so we check
X-Forwarded-Proto and X-Forwarded-Host before falling back to the raw request URL.

This is isolated here so it's easy to swap out with alternate approaches.
"""

from fastapi import Request


def get_deployment_url(request: Request) -> str:
    """Derive the deployment's public URL from the incoming request headers."""
    host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    scheme = request.headers.get("x-forwarded-proto") or request.url.scheme
    return f"{scheme}://{host}"
