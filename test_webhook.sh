#!/bin/bash
# Script de testing del webhook con curl

set -e

API_URL="http://localhost:8000"
VERIFY_TOKEN="test_token_aqui"

echo "🧪 Testing del Chatbot ACA Luján"
echo "=================================="
echo ""

# 1. Health Check
echo "1️⃣  Health Check..."
curl -s "${API_URL}/api/health" | jq .
echo ""

# 2. Verificar webhook
echo "2️⃣  Verificar Webhook..."
curl -s "${API_URL}/api/webhook?hub_mode=subscribe&hub_challenge=test123&hub_verify_token=${VERIFY_TOKEN}" | jq .
echo ""

# 3. Simular mensaje válido (menú principal)
echo "3️⃣  Simular mensaje: '1' (menú principal)..."
curl -s -X POST "${API_URL}/api/webhook" \
  -H "Content-Type: application/json" \
  -d '{
    "object": "whatsapp_business_account",
    "entry": [{
      "id": "123456789",
      "changes": [{
        "value": {
          "messaging_product": "whatsapp",
          "messages": [{
            "from": "5491234567890",
            "text": {"body": "1"},
            "timestamp": '$(date +%s)'
          }],
          "contacts": [{
            "profile": {"name": "Usuario Test"},
            "wa_id": "5491234567890"
          }]
        }
      }]
    }]
  }' | jq .
echo ""

# 4. Simular mensaje inválido
echo "4️⃣  Simular mensaje inválido: '99'..."
curl -s -X POST "${API_URL}/api/webhook" \
  -H "Content-Type: application/json" \
  -d '{
    "object": "whatsapp_business_account",
    "entry": [{
      "changes": [{
        "value": {
          "messages": [{
            "from": "5491234567890",
            "text": {"body": "99"},
            "timestamp": '$(date +%s)'
          }],
          "contacts": [{
            "profile": {"name": "Usuario Test"},
            "wa_id": "5491234567890"
          }]
        }
      }]
    }]
  }' | jq .
echo ""

# 5. Simular comando volver
echo "5️⃣  Simular comando volver: '#'..."
curl -s -X POST "${API_URL}/api/webhook" \
  -H "Content-Type: application/json" \
  -d '{
    "object": "whatsapp_business_account",
    "entry": [{
      "changes": [{
        "value": {
          "messages": [{
            "from": "5491234567890",
            "text": {"body": "#"},
            "timestamp": '$(date +%s)'
          }],
          "contacts": [{
            "profile": {"name": "Usuario Test"},
            "wa_id": "5491234567890"
          }]
        }
      }]
    }]
  }' | jq .
echo ""

# 6. Obtener sesión
echo "6️⃣  Obtener sesión del usuario..."
curl -s "${API_URL}/api/sesion/+5491234567890" | jq .
echo ""

echo "✅ Testing completado!"
echo ""
echo "💡 Tip: Usa http://localhost:8000/docs para documentación interactiva"
