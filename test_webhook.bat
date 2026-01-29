@echo off
REM Script de testing en Windows

set API_URL=http://localhost:8000
set VERIFY_TOKEN=test_token_aqui

echo Testing del Chatbot ACA Lujan
echo ==============================
echo.

REM 1. Health Check
echo 1. Health Check...
curl -s "%API_URL%/api/health"
echo.
echo.

REM 2. Verificar webhook
echo 2. Verificar Webhook...
curl -s "%API_URL%/api/webhook?hub_mode=subscribe^&hub_challenge=test123^&hub_verify_token=%VERIFY_TOKEN%"
echo.
echo.

REM 3. Simular mensaje valido
echo 3. Simular mensaje: '1' (menu principal)...
curl -X POST "%API_URL%/api/webhook" ^
  -H "Content-Type: application/json" ^
  -d "{\"entry\":[{\"changes\":[{\"value\":{\"messages\":[{\"from\":\"5491234567890\",\"text\":{\"body\":\"1\"},\"timestamp\":1234567890}],\"contacts\":[{\"profile\":{\"name\":\"Test\"},\"wa_id\":\"5491234567890\"}]}}]}]}"
echo.
echo.

echo Test completado!
pause
