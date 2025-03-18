"""
Integration tests for the main application
"""


from app.main import app


def test_app_includes_monitoring_router():
    """Test that app includes the monitoring router"""
    # Get all registered routes in the app
    routes = app.routes
    
    # Find routes with monitoring prefix
    monitoring_routes = []
    for route in routes:
        # FastAPI routes store path in different attributes depending on the route type
        # For APIRoute objects, it's route.path
        route_path = getattr(route, "path", None)
        if route_path and isinstance(route_path, str) and route_path.startswith("/monitoring"):
            monitoring_routes.append(route)
    
    # There should be at least one monitoring route
    assert len(monitoring_routes) > 0
    
    # Specifically, we should have the events/stats endpoint
    event_stats_route = []
    for route in monitoring_routes:
        route_path = getattr(route, "path", None)
        if route_path and route_path == "/monitoring/events/stats":
            event_stats_route.append(route)
    assert len(event_stats_route) == 1