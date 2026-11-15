@echo off
cd /d "%~dp0"
echo =========================================================================
echo  Starting COA Markov Page Prefetching Presentation UI on Port 8000...
echo =========================================================================
echo.
echo Opening http://localhost:8000 in your default browser...
start "" http://localhost:8000
echo.
echo Press Ctrl+C in this terminal window to stop the server when finished.
echo.
REM Server sends no-store so edits show up on a normal refresh
python -c "import http.server as h; h.SimpleHTTPRequestHandler.end_headers=lambda s:(s.send_header('Cache-Control','no-store'),h.BaseHTTPRequestHandler.end_headers(s)); h.test(HandlerClass=h.SimpleHTTPRequestHandler,port=8000,bind='127.0.0.1')"

