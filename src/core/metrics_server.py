"""
Simple HTTP server for exposing Prometheus metrics in the AniVault desktop application.

This module provides a lightweight HTTP server that exposes metrics endpoints
for monitoring cache-DB synchronization operations.
"""

import threading
import time
from typing import Optional
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

from .metrics_exporter import metrics_exporter


class MetricsHTTPRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for metrics endpoints."""
    
    def do_GET(self) -> None:
        """Handle GET requests."""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/metrics':
            self._handle_metrics()
        elif parsed_path.path == '/health':
            self._handle_health()
        else:
            self._handle_not_found()
    
    def _handle_metrics(self) -> None:
        """Handle /metrics endpoint."""
        try:
            metrics_data = metrics_exporter.generate_metrics()
            
            self.send_response(200)
            self.send_header('Content-Type', metrics_exporter.get_content_type())
            self.send_header('Content-Length', str(len(metrics_data)))
            self.end_headers()
            
            self.wfile.write(metrics_data.encode('utf-8'))
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(f'Internal Server Error: {e}'.encode('utf-8'))
    
    def _handle_health(self) -> None:
        """Handle /health endpoint."""
        try:
            # Simple health check - could be enhanced with actual health checks
            health_data = '{"status": "healthy", "timestamp": "' + str(time.time()) + '"}'
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(health_data)))
            self.end_headers()
            
            self.wfile.write(health_data.encode('utf-8'))
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(f'Health check failed: {e}'.encode('utf-8'))
    
    def _handle_not_found(self) -> None:
        """Handle 404 errors."""
        self.send_response(404)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Not Found')
    
    def log_message(self, format: str, *args) -> None:
        """Override to reduce log noise."""
        # Only log errors, not normal requests
        if 'error' in format.lower():
            super().log_message(format, *args)


class MetricsServer:
    """
    Simple HTTP server for exposing Prometheus metrics.
    
    Runs in a separate thread to avoid blocking the main application.
    """
    
    def __init__(self, host: str = 'localhost', port: int = 8080):
        """Initialize the metrics server.
        
        Args:
            host: Host to bind to (default: localhost)
            port: Port to bind to (default: 8080)
        """
        self.host = host
        self.port = port
        self.server: Optional[HTTPServer] = None
        self.server_thread: Optional[threading.Thread] = None
        self.running = False
    
    def start(self) -> bool:
        """Start the metrics server.
        
        Returns:
            True if server started successfully, False otherwise
        """
        if self.running:
            return True
        
        try:
            self.server = HTTPServer((self.host, self.port), MetricsHTTPRequestHandler)
            self.server_thread = threading.Thread(
                target=self._run_server,
                daemon=True,
                name='MetricsServer'
            )
            self.server_thread.start()
            self.running = True
            
            print(f"Metrics server started on http://{self.host}:{self.port}")
            print(f"Metrics endpoint: http://{self.host}:{self.port}/metrics")
            print(f"Health endpoint: http://{self.host}:{self.port}/health")
            
            return True
            
        except Exception as e:
            print(f"Failed to start metrics server: {e}")
            return False
    
    def stop(self) -> None:
        """Stop the metrics server."""
        if not self.running or not self.server:
            return
        
        try:
            self.server.shutdown()
            self.server.server_close()
            
            if self.server_thread and self.server_thread.is_alive():
                self.server_thread.join(timeout=5.0)
            
            self.running = False
            print("Metrics server stopped")
            
        except Exception as e:
            print(f"Error stopping metrics server: {e}")
    
    def _run_server(self) -> None:
        """Run the HTTP server (called in separate thread)."""
        try:
            if self.server:
                self.server.serve_forever()
        except Exception as e:
            print(f"Metrics server error: {e}")
        finally:
            self.running = False
    
    def is_running(self) -> bool:
        """Check if the server is running.
        
        Returns:
            True if server is running, False otherwise
        """
        return self.running and self.server_thread and self.server_thread.is_alive()


# Global metrics server instance
metrics_server = MetricsServer()
