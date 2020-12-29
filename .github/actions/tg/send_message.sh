#!/bin/bash

TOKEN=$1
CHAT_ID=$2
TEXT=$3

curl -X POST \
    -H 'Content-Type: application/json' \
    -d "{\"chat_id\": \"$CHAT_ID\", \"parse_mode\":\"markdown\", \"disable_web_page_preview\":true, \"text\": \"$TEXT\"}" \
    "https://api.telegram.org/bot$TOKEN/sendMessage"
