#!/bin/bash
# Usypia bezczynną rozmowę Remote Control „Rozwój panelu”: proces rozmowy (claude --print --sdk-url …, ~0,4 GB RAM)
# kończy się, gdy od 60 min nie zmienił się zapis żadnej rozmowy w kopii roboczej. Nasłuch (claude remote-control, ~0,14 GB)
# zostaje, więc kolejna wiadomość z aplikacji Claude uruchamia rozmowę ponownie. Uruchamia claude-zdalnie-uspij.timer.
set -u
CISZA_MIN=${CISZA_MIN:-60}
ZAPISY=/home/agent/.claude/projects/-home-agent-rozwoj-IntegrateSystems
swieze=$(find "$ZAPISY" -type f -name "*.jsonl" -mmin -"$CISZA_MIN" -print -quit 2>/dev/null)
[ -n "$swieze" ] && exit 0
for pid in $(pgrep -u agent -f -- '--sdk-url https://api.anthropic.com/v1/code/sessions/'); do
  wiek=$(ps -o etimes= -p "$pid" | tr -d ' ')
  [ -n "$wiek" ] && [ "$wiek" -gt $((CISZA_MIN * 60)) ] || continue
  kill -TERM "$pid" && logger -t claude-zdalnie "uśpiono bezczynną rozmowę (pid $pid)"
done
